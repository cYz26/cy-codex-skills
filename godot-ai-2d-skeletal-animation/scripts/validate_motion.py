#!/usr/bin/env python3
"""Validate Godot AI 2D motion JSON files against a rig."""

from __future__ import annotations

import argparse
import json
import math
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


def value_distance(a: Any, b: Any) -> float:
    if is_number(a) and is_number(b):
        return abs(float(a) - float(b))
    if is_vector2(a) and is_vector2(b):
        return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))
    return float("inf")


def load_json(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except Exception as exc:  # noqa: BLE001
        return None, [issue("critical", f"invalid JSON: {exc}", str(path))]


def infer_rig_path(motion_path: Path) -> Path | None:
    candidate = motion_path.parent.parent / "rig_meta.json"
    return candidate if candidate.exists() else None


def load_targets(rig_path: Path | None) -> tuple[set[str], set[str], list[dict[str, str]]]:
    if rig_path is None:
        return set(), set(), [issue("warning", "no rig_meta.json found; target existence checks skipped")]
    rig, checks = load_json(rig_path)
    if rig is None:
        return set(), set(), checks
    bones = {bone.get("name") for bone in rig.get("skeleton", {}).get("bones", []) if isinstance(bone, dict)}
    sockets = {socket.get("name") for socket in rig.get("sockets", []) if isinstance(socket, dict)}
    return {b for b in bones if isinstance(b, str)}, {s for s in sockets if isinstance(s, str)}, []


def validate_motion_header(data: dict[str, Any], checks: list[dict[str, str]]) -> None:
    if data.get("schema_version") != "1.0":
        checks.append(issue("critical", "schema_version must be '1.0'", "schema_version"))
    if not isinstance(data.get("case_id"), str) or not data.get("case_id"):
        checks.append(issue("critical", "case_id is required", "case_id"))
    if not isinstance(data.get("animation"), str) or not data.get("animation"):
        checks.append(issue("critical", "animation is required", "animation"))
    if data.get("category") not in {"idle", "move", "action"}:
        checks.append(issue("critical", "category must be idle, move, or action", "category"))
    if not is_number(data.get("length")) or data.get("length", 0) <= 0:
        checks.append(issue("critical", "length must be a positive number", "length"))
    if not isinstance(data.get("loop"), bool):
        checks.append(issue("critical", "loop must be boolean", "loop"))


def validate_track_target(
    track: dict[str, Any],
    track_path: str,
    bones: set[str],
    sockets: set[str],
    checks: list[dict[str, str]],
) -> None:
    target = track.get("target")
    name = track.get("name")
    if target not in {"bone", "socket"}:
        checks.append(issue("critical", "track.target must be bone or socket", f"{track_path}.target"))
    elif target == "bone" and bones and name not in bones:
        checks.append(issue("critical", f"track references missing bone '{name}'", f"{track_path}.name"))
    elif target == "socket" and sockets and name not in sockets:
        checks.append(issue("critical", f"track references missing socket '{name}'", f"{track_path}.name"))


def validate_key_value(
    prop: Any,
    value: Any,
    key_path: str,
    checks: list[dict[str, str]],
) -> None:
    if prop == "rotation_degrees" and not is_number(value):
        checks.append(issue("critical", "rotation value must be numeric", f"{key_path}.value"))
    if prop in {"position", "scale"} and not is_vector2(value):
        checks.append(issue("critical", f"{prop} value must be [x, y]", f"{key_path}.value"))


def validate_track_keys(
    track: dict[str, Any],
    track_path: str,
    length: float,
    loop_tolerance: float,
    loop: bool,
    checks: list[dict[str, str]],
) -> None:
    prop = track.get("property")
    keys = track.get("keys")
    if not isinstance(keys, list) or not keys:
        checks.append(issue("critical", "track.keys must be non-empty", f"{track_path}.keys"))
        return

    previous_time = -1.0
    for key_index, key in enumerate(keys):
        key_path = f"{track_path}.keys[{key_index}]"
        if not isinstance(key, dict):
            checks.append(issue("critical", "key entry must be an object", key_path))
            continue
        time = key.get("time")
        value = key.get("value")
        if not is_number(time):
            checks.append(issue("critical", "key.time must be numeric", f"{key_path}.time"))
            continue
        time_value = float(time)
        if time_value < previous_time:
            checks.append(issue("critical", "key times must be sorted ascending", f"{track_path}.keys"))
        previous_time = time_value
        if time_value > length:
            checks.append(issue("critical", "key.time exceeds animation length", f"{key_path}.time"))
        validate_key_value(prop, value, key_path, checks)

    if loop and len(keys) >= 2:
        delta = value_distance(keys[0].get("value"), keys[-1].get("value"))
        if delta > loop_tolerance:
            checks.append(issue("warning", f"loop first/last key differ by {delta:.3f}", track_path))


def validate_tracks(
    data: dict[str, Any],
    bones: set[str],
    sockets: set[str],
    length: float,
    loop_tolerance: float,
    checks: list[dict[str, str]],
) -> None:
    tracks = data.get("tracks")
    if not isinstance(tracks, list) or not tracks:
        checks.append(issue("critical", "tracks must be a non-empty array", "tracks"))
        return

    for track_index, track in enumerate(tracks):
        track_path = f"tracks[{track_index}]"
        if not isinstance(track, dict):
            checks.append(issue("critical", "track entry must be an object", track_path))
            continue
        validate_track_target(track, track_path, bones, sockets, checks)
        prop = track.get("property")
        if prop not in {"rotation_degrees", "position", "scale"}:
            checks.append(issue("critical", "track.property is invalid", f"{track_path}.property"))
        validate_track_keys(
            track,
            track_path,
            length,
            loop_tolerance,
            bool(data.get("loop")),
            checks,
        )


def validate_events(data: dict[str, Any], length: float, checks: list[dict[str, str]]) -> set[str]:
    events = data.get("events", []) or []
    if not isinstance(events, list):
        checks.append(issue("critical", "events must be an array", "events"))
        return set()

    event_names: set[str] = set()
    for index, event in enumerate(events):
        event_path = f"events[{index}]"
        if not isinstance(event, dict):
            checks.append(issue("critical", "event entry must be an object", event_path))
            continue
        time = event.get("time")
        name = event.get("name")
        if not is_number(time):
            checks.append(issue("critical", "event.time must be numeric", f"{event_path}.time"))
        elif float(time) > length:
            checks.append(issue("critical", "event.time exceeds animation length", f"{event_path}.time"))
        if not isinstance(name, str) or not name:
            checks.append(issue("critical", "event.name is required", f"{event_path}.name"))
        else:
            event_names.add(name)
    return event_names


def print_report(report: dict[str, Any]) -> None:
    print(f"{report['path']}: {report['summary']}")
    for check in report["checks"]:
        suffix = f" ({check.get('path')})" if check.get("path") else ""
        print(f"  [{check['severity']}] {check['message']}{suffix}")


def validate_motion(path: Path, rig_path: Path | None, loop_tolerance: float) -> dict[str, Any]:
    data, checks = load_json(path)
    if data is None:
        return {"schema_version": "1.0", "path": str(path), "summary": summarize(checks), "checks": checks}

    bones, sockets, target_checks = load_targets(rig_path or infer_rig_path(path))
    checks.extend(target_checks)

    validate_motion_header(data, checks)
    length = float(data.get("length", 0) or 0)
    validate_tracks(data, bones, sockets, length, loop_tolerance, checks)
    event_names = validate_events(data, length, checks)
    if data.get("category") == "action":
        has_on = bool(event_names & {"hitbox_on", "hazard_on"})
        has_off = bool(event_names & {"hitbox_off", "hazard_off"})
        if not has_on or not has_off:
            checks.append(issue("critical", "action animation requires hitbox/hazard on and off events", "events"))

    if not any(c["severity"] == "critical" for c in checks):
        checks.append(issue("info", "motion validation passed", str(path)))

    return {"schema_version": "1.0", "path": str(path), "summary": summarize(checks), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("motions", nargs="+", help="Path(s) to motion JSON files")
    parser.add_argument("--rig", help="Optional rig_meta.json path")
    parser.add_argument("--loop-tolerance", type=float, default=0.01)
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    args = parser.parse_args()

    rig_path = Path(args.rig) if args.rig else None
    reports = [validate_motion(Path(item), rig_path, args.loop_tolerance) for item in args.motions]
    if args.json:
        print(json.dumps(reports[0] if len(reports) == 1 else reports, indent=2))
    else:
        for report in reports:
            print_report(report)
    return 1 if any(report["summary"]["critical"] for report in reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
