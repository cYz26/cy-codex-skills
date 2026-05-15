#!/usr/bin/env python3
"""Validate Godot AI 2D rig metadata and transparent part PNGs."""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from pathlib import Path
from typing import Any


def issue(severity: str, message: str, path: str | None = None) -> dict[str, str]:
    item = {"severity": severity, "message": message}
    if path:
        item["path"] = path
    return item


def summarize(checks: list[dict[str, str]]) -> dict[str, int]:
    return {
        "critical": sum(1 for c in checks if c["severity"] == "critical"),
        "warning": sum(1 for c in checks if c["severity"] == "warning"),
        "info": sum(1 for c in checks if c["severity"] == "info"),
    }


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def is_vector2(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 2 and all(is_number(v) for v in value)


def read_png_info(path: Path) -> tuple[int, int, int]:
    with path.open("rb") as handle:
        signature = handle.read(8)
        if signature != b"\x89PNG\r\n\x1a\n":
            raise ValueError("not a PNG file")
        length = struct.unpack(">I", handle.read(4))[0]
        chunk_type = handle.read(4)
        if chunk_type != b"IHDR" or length < 13:
            raise ValueError("missing IHDR chunk")
        data = handle.read(length)
        width, height, _bit_depth, color_type = struct.unpack(">IIBB", data[:10])
        return width, height, color_type


def load_json(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except Exception as exc:  # noqa: BLE001 - report exact parser failure
        return None, [issue("critical", f"invalid JSON: {exc}", str(path))]


def validate_bones(data: dict[str, Any]) -> tuple[set[str], list[dict[str, str]]]:
    checks: list[dict[str, str]] = []
    bones = data.get("skeleton", {}).get("bones")
    if not isinstance(bones, list) or not bones:
        return set(), [issue("critical", "skeleton.bones must be a non-empty array", "skeleton.bones")]

    names: set[str] = set()
    parents: dict[str, str | None] = {}
    for index, bone in enumerate(bones):
        path = f"skeleton.bones[{index}]"
        if not isinstance(bone, dict):
            checks.append(issue("critical", "bone entry must be an object", path))
            continue
        name = bone.get("name")
        parent = bone.get("parent")
        if not isinstance(name, str) or not name:
            checks.append(issue("critical", "bone.name is required", f"{path}.name"))
            continue
        if name in names:
            checks.append(issue("critical", f"duplicate bone name '{name}'", f"{path}.name"))
        names.add(name)
        if parent is not None and not isinstance(parent, str):
            checks.append(issue("critical", "bone.parent must be a string or null", f"{path}.parent"))
        parents[name] = parent
        if not is_vector2(bone.get("position")):
            checks.append(issue("critical", "bone.position must be [x, y]", f"{path}.position"))
        if "rotation_degrees" in bone and not is_number(bone["rotation_degrees"]):
            checks.append(issue("critical", "bone.rotation_degrees must be numeric", f"{path}.rotation_degrees"))

    roots = [name for name, parent in parents.items() if parent is None]
    if len(roots) != 1:
        checks.append(issue("critical", f"expected exactly one root bone, found {len(roots)}", "skeleton.bones"))

    for name, parent in parents.items():
        if parent is not None and parent not in names:
            checks.append(issue("critical", f"bone '{name}' references missing parent '{parent}'", "skeleton.bones"))

    for name in names:
        seen: set[str] = set()
        current: str | None = name
        while current is not None:
            if current in seen:
                checks.append(issue("critical", f"bone parent cycle detected at '{current}'", "skeleton.bones"))
                break
            seen.add(current)
            current = parents.get(current)

    return names, checks


def validate_sockets(
    data: dict[str, Any],
    bone_names: set[str],
    checks: list[dict[str, str]],
) -> set[str]:
    socket_names: set[str] = set()
    for index, socket in enumerate(data.get("sockets", []) or []):
        path_label = f"sockets[{index}]"
        if not isinstance(socket, dict):
            checks.append(issue("critical", "socket entry must be an object", path_label))
            continue
        name = socket.get("name")
        bone = socket.get("bone")
        if not isinstance(name, str) or not name:
            checks.append(issue("critical", "socket.name is required", f"{path_label}.name"))
        elif name in socket_names:
            checks.append(issue("critical", f"duplicate socket '{name}'", f"{path_label}.name"))
        else:
            socket_names.add(name)
        if bone not in bone_names:
            checks.append(issue("critical", f"socket references missing bone '{bone}'", f"{path_label}.bone"))
        if not is_vector2(socket.get("local_position")):
            checks.append(issue("critical", "socket.local_position must be [x, y]", f"{path_label}.local_position"))
    return socket_names


def validate_part_file(
    rig_path: Path,
    part: dict[str, Any],
    path_label: str,
    checks: list[dict[str, str]],
) -> tuple[int, int] | None:
    file_value = part.get("file")
    if not isinstance(file_value, str) or not file_value:
        checks.append(issue("critical", "part.file is required", f"{path_label}.file"))
        return None

    part_path = rig_path.parent / file_value
    if not part_path.exists():
        checks.append(issue("critical", f"missing part file '{file_value}'", str(part_path)))
        return None

    try:
        width, height, color_type = read_png_info(part_path)
    except Exception as exc:  # noqa: BLE001
        checks.append(issue("critical", f"invalid PNG '{file_value}': {exc}", str(part_path)))
        return None

    if color_type not in {4, 6}:
        checks.append(issue("warning", f"part PNG '{file_value}' may not contain alpha", str(part_path)))
    return width, height


def validate_parts(
    rig_path: Path,
    data: dict[str, Any],
    bone_names: set[str],
    checks: list[dict[str, str]],
) -> None:
    parts = data.get("parts")
    if not isinstance(parts, list) or not parts:
        checks.append(issue("critical", "parts must be a non-empty array", "parts"))
        return

    part_ids: set[str] = set()
    for index, part in enumerate(parts):
        path_label = f"parts[{index}]"
        if not isinstance(part, dict):
            checks.append(issue("critical", "part entry must be an object", path_label))
            continue
        part_id = part.get("id")
        if not isinstance(part_id, str) or not part_id:
            checks.append(issue("critical", "part.id is required", f"{path_label}.id"))
        elif part_id in part_ids:
            checks.append(issue("critical", f"duplicate part id '{part_id}'", f"{path_label}.id"))
        else:
            part_ids.add(part_id)
        if part.get("bone") not in bone_names:
            missing_bone = part.get("bone")
            checks.append(issue("critical", f"part references missing bone '{missing_bone}'", f"{path_label}.bone"))
        if not is_vector2(part.get("pivot")):
            checks.append(issue("critical", "part.pivot must be [x, y]", f"{path_label}.pivot"))
        if not is_vector2(part.get("offset")):
            checks.append(issue("critical", "part.offset must be [x, y]", f"{path_label}.offset"))
        if not isinstance(part.get("z_index"), int):
            checks.append(issue("critical", "part.z_index must be an integer", f"{path_label}.z_index"))

        dimensions = validate_part_file(rig_path, part, path_label, checks)
        pivot = part.get("pivot")
        if dimensions and is_vector2(pivot):
            width, height = dimensions
            if not (0 <= pivot[0] <= width and 0 <= pivot[1] <= height):
                message = f"pivot {pivot} outside image bounds {width}x{height}"
                checks.append(issue("critical", message, f"{path_label}.pivot"))


def validate_hitboxes(
    data: dict[str, Any],
    valid_anchors: set[str],
    checks: list[dict[str, str]],
) -> None:
    for index, hitbox in enumerate(data.get("hitboxes", []) or []):
        path_label = f"hitboxes[{index}]"
        if not isinstance(hitbox, dict):
            checks.append(issue("critical", "hitbox entry must be an object", path_label))
            continue
        anchor = hitbox.get("anchor")
        if anchor not in valid_anchors:
            checks.append(issue("critical", f"hitbox references missing anchor '{anchor}'", f"{path_label}.anchor"))
        if not is_vector2(hitbox.get("size")):
            checks.append(issue("critical", "hitbox.size must be [x, y]", f"{path_label}.size"))
        if "offset" in hitbox and not is_vector2(hitbox.get("offset")):
            checks.append(issue("critical", "hitbox.offset must be [x, y]", f"{path_label}.offset"))


def print_report(report: dict[str, Any]) -> None:
    print(f"{report['path']}: {report['summary']}")
    for check in report["checks"]:
        suffix = f" ({check.get('path')})" if check.get("path") else ""
        print(f"  [{check['severity']}] {check['message']}{suffix}")


def validate_rig(path: Path) -> dict[str, Any]:
    data, checks = load_json(path)
    if data is None:
        return {"schema_version": "1.0", "path": str(path), "summary": summarize(checks), "checks": checks}

    if data.get("schema_version") != "1.0":
        checks.append(issue("critical", "schema_version must be '1.0'", "schema_version"))
    if not isinstance(data.get("case_id"), str) or not data.get("case_id"):
        checks.append(issue("critical", "case_id is required", "case_id"))
    if data.get("object_type") not in {"humanoid", "weapon_humanoid", "quadruped", "mechanical", "custom"}:
        checks.append(issue("critical", "object_type is invalid", "object_type"))

    bone_names, bone_checks = validate_bones(data)
    checks.extend(bone_checks)

    socket_names = validate_sockets(data, bone_names, checks)
    validate_parts(path, data, bone_names, checks)
    valid_anchors = bone_names | socket_names
    validate_hitboxes(data, valid_anchors, checks)

    if not any(c["severity"] == "critical" for c in checks):
        checks.append(issue("info", "rig metadata validation passed", str(path)))

    return {"schema_version": "1.0", "path": str(path), "summary": summarize(checks), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("rig_meta", nargs="+", help="Path(s) to rig_meta.json")
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    args = parser.parse_args()

    reports = [validate_rig(Path(item)) for item in args.rig_meta]
    if args.json:
        print(json.dumps(reports[0] if len(reports) == 1 else reports, indent=2))
    else:
        for report in reports:
            print_report(report)
    return 1 if any(report["summary"]["critical"] for report in reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
