#!/usr/bin/env python3
"""Generate deterministic fixture art, rig metadata, motions, and negative cases."""

from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "fixtures" / "godot_demo_project"
CASES = PROJECT / "fixtures" / "cases"
NEGATIVE = PROJECT / "fixtures" / "negative_cases"


RGBA = tuple[int, int, int, int]


def chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def write_png(path: Path, width: int, height: int, pixels: list[RGBA]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width):
            raw.extend(pixels[y * width + x])
    data = b"\x89PNG\r\n\x1a\n"
    data += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    data += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    data += chunk(b"IEND", b"")
    path.write_bytes(data)


def blank(width: int, height: int, color: RGBA = (0, 0, 0, 0)) -> list[RGBA]:
    return [color for _ in range(width * height)]


def rect(pixels: list[RGBA], width: int, height: int, x: int, y: int, w: int, h: int, color: RGBA) -> None:
    for yy in range(max(0, y), min(height, y + h)):
        for xx in range(max(0, x), min(width, x + w)):
            pixels[yy * width + xx] = color


def border(pixels: list[RGBA], width: int, height: int, color: RGBA = (24, 28, 38, 255)) -> None:
    rect(pixels, width, height, 0, 0, width, 2, color)
    rect(pixels, width, height, 0, height - 2, width, 2, color)
    rect(pixels, width, height, 0, 0, 2, height, color)
    rect(pixels, width, height, width - 2, 0, 2, height, color)


def make_part(path: Path, size: tuple[int, int], color: RGBA) -> None:
    width, height = size
    pixels = blank(width, height)
    rect(pixels, width, height, 2, 2, width - 4, height - 4, color)
    border(pixels, width, height)
    write_png(path, width, height, pixels)


def make_reference(path: Path, title_color: RGBA, placements: Iterable[tuple[int, int, int, int, RGBA]]) -> None:
    width, height = 420, 300
    pixels = blank(width, height, (236, 240, 244, 255))
    rect(pixels, width, height, 0, 0, width, 10, title_color)
    for x, y, w, h, color in placements:
        rect(pixels, width, height, x, y, w, h, color)
        rect(pixels, width, height, x, y, w, 2, (24, 28, 38, 255))
        rect(pixels, width, height, x, y + h - 2, w, 2, (24, 28, 38, 255))
        rect(pixels, width, height, x, y, 2, h, (24, 28, 38, 255))
        rect(pixels, width, height, x + w - 2, y, 2, h, (24, 28, 38, 255))
    write_png(path, width, height, pixels)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def bone(name: str, parent: str | None, position: list[float], rotation: float = 0) -> dict:
    return {"name": name, "parent": parent, "position": position, "rotation_degrees": rotation}


def part(part_id: str, bone_name: str, size: tuple[int, int], color: RGBA, z: int, offset: list[float] | None = None) -> dict:
    return {
        "id": part_id,
        "file": f"parts/{part_id}.png",
        "bone": bone_name,
        "pivot": [size[0] / 2, size[1] / 2],
        "offset": offset or [0, 0],
        "z_index": z,
        "_size": size,
        "_color": color,
    }


def write_case(case_id: str, object_type: str, bones: list[dict], parts: list[dict], sockets: list[dict], hitboxes: list[dict], motions: list[dict], brief: str, reference: list[tuple[int, int, int, int, RGBA]], title_color: RGBA) -> None:
    case_dir = CASES / case_id
    parts_dir = case_dir / "parts"
    for item in parts:
        make_part(parts_dir / f"{item['id']}.png", tuple(item.pop("_size")), tuple(item.pop("_color")))
    make_reference(case_dir / "reference.png", title_color, reference)
    (case_dir / "design_brief.md").write_text(brief.strip() + "\n", encoding="utf-8")
    write_json(case_dir / "rig_meta.json", {
        "schema_version": "1.0",
        "case_id": case_id,
        "object_type": object_type,
        "skeleton": {"bones": bones},
        "parts": parts,
        "sockets": sockets,
        "hitboxes": hitboxes,
    })
    for motion in motions:
        write_json(case_dir / "motions" / f"{motion['category']}.json", motion)


def motion(case_id: str, name: str, category: str, length: float, loop: bool, tracks: list[dict], events: list[dict] | None = None) -> dict:
    return {
        "schema_version": "1.0",
        "case_id": case_id,
        "animation": name,
        "category": category,
        "length": length,
        "loop": loop,
        "tracks": tracks,
        "events": events or [],
    }


def rot(name: str, keys: list[tuple[float, float]]) -> dict:
    return {"target": "bone", "name": name, "property": "rotation_degrees", "keys": [{"time": t, "value": v} for t, v in keys]}


def pos(name: str, keys: list[tuple[float, list[float]]]) -> dict:
    return {"target": "bone", "name": name, "property": "position", "keys": [{"time": t, "value": v} for t, v in keys]}


def make_humanoid() -> None:
    case_id = "case_01_humanoid_adventurer"
    bones = [
        bone("root", None, [210, 230]), bone("pelvis", "root", [0, 0]), bone("spine", "pelvis", [0, -44]),
        bone("chest", "spine", [0, -34]), bone("neck", "chest", [0, -20]), bone("head", "neck", [0, -24]),
        bone("upper_arm_L", "chest", [-28, -4]), bone("lower_arm_L", "upper_arm_L", [-34, 28]), bone("hand_L", "lower_arm_L", [-16, 25]),
        bone("upper_arm_R", "chest", [28, -4]), bone("lower_arm_R", "upper_arm_R", [34, 28]), bone("hand_R", "lower_arm_R", [16, 25]),
        bone("upper_leg_L", "pelvis", [-14, 16]), bone("lower_leg_L", "upper_leg_L", [-8, 48]), bone("foot_L", "lower_leg_L", [-4, 44]),
        bone("upper_leg_R", "pelvis", [14, 16]), bone("lower_leg_R", "upper_leg_R", [8, 48]), bone("foot_R", "lower_leg_R", [4, 44]),
    ]
    parts = [
        part("head", "head", (42, 46), (236, 182, 124, 255), 50), part("torso", "chest", (52, 72), (61, 132, 184, 255), 20),
        part("pelvis", "pelvis", (46, 34), (84, 88, 104, 255), 18), part("upper_arm_L", "upper_arm_L", (24, 54), (227, 156, 94, 255), 22),
        part("lower_arm_L", "lower_arm_L", (22, 48), (230, 176, 112, 255), 23), part("hand_L", "hand_L", (20, 20), (236, 182, 124, 255), 24),
        part("upper_arm_R", "upper_arm_R", (24, 54), (227, 156, 94, 255), 22), part("lower_arm_R", "lower_arm_R", (22, 48), (230, 176, 112, 255), 23),
        part("hand_R", "hand_R", (20, 20), (236, 182, 124, 255), 24), part("upper_leg_L", "upper_leg_L", (26, 58), (77, 99, 138, 255), 10),
        part("lower_leg_L", "lower_leg_L", (24, 54), (60, 74, 110, 255), 11), part("foot_L", "foot_L", (34, 18), (48, 44, 40, 255), 12),
        part("upper_leg_R", "upper_leg_R", (26, 58), (77, 99, 138, 255), 10), part("lower_leg_R", "lower_leg_R", (24, 54), (60, 74, 110, 255), 11),
        part("foot_R", "foot_R", (34, 18), (48, 44, 40, 255), 12),
    ]
    motions = [
        motion(case_id, "idle", "idle", 1.0, True, [pos("pelvis", [(0, [0, 0]), (0.5, [0, -3]), (1.0, [0, 0])]), rot("chest", [(0, 0), (0.5, 2), (1.0, 0)])]),
        motion(case_id, "run", "move", 0.8, True, [rot("upper_leg_L", [(0, -18), (0.4, 22), (0.8, -18)]), rot("upper_leg_R", [(0, 22), (0.4, -18), (0.8, 22)]), rot("upper_arm_L", [(0, 18), (0.4, -18), (0.8, 18)]), rot("upper_arm_R", [(0, -18), (0.4, 18), (0.8, -18)])]),
        motion(case_id, "basic_attack", "action", 0.55, False, [rot("chest", [(0, -4), (0.15, -9), (0.24, 8), (0.55, 0)]), rot("upper_arm_R", [(0, -20), (0.15, -55), (0.24, 60), (0.55, 5)])], [{"time": 0.16, "name": "hitbox_on", "target": "body_hitbox"}, {"time": 0.28, "name": "hitbox_off", "target": "body_hitbox"}]),
    ]
    write_case(case_id, "humanoid", bones, parts, [], [{"name": "body_hitbox", "anchor": "chest", "size": [52, 80], "offset": [0, 10]}], motions, "Standard humanoid adventurer fixture for base skeleton, pivots, idle, run, and basic attack validation.", [(192, 40, 38, 42, (236, 182, 124, 255)), (184, 90, 54, 76, (61, 132, 184, 255)), (145, 96, 28, 88, (227, 156, 94, 255)), (255, 96, 28, 88, (227, 156, 94, 255)), (170, 168, 28, 82, (77, 99, 138, 255)), (222, 168, 28, 82, (77, 99, 138, 255))], (61, 132, 184, 255))


def make_swordsman() -> None:
    case_id = "case_02_weapon_swordsman"
    bones = [
        bone("root", None, [210, 230]), bone("pelvis", "root", [0, 0]), bone("spine", "pelvis", [0, -44]), bone("chest", "spine", [0, -34]), bone("neck", "chest", [0, -20]), bone("head", "neck", [0, -24]),
        bone("upper_arm_L", "chest", [-28, 0]), bone("lower_arm_L", "upper_arm_L", [-34, 28]), bone("hand_L", "lower_arm_L", [-16, 25]),
        bone("upper_arm_R", "chest", [30, 0]), bone("lower_arm_R", "upper_arm_R", [38, 24]), bone("hand_R", "lower_arm_R", [22, 22]), bone("weapon", "hand_R", [45, 0]),
        bone("upper_leg_L", "pelvis", [-14, 16]), bone("lower_leg_L", "upper_leg_L", [-8, 48]), bone("foot_L", "lower_leg_L", [-4, 44]),
        bone("upper_leg_R", "pelvis", [14, 16]), bone("lower_leg_R", "upper_leg_R", [8, 48]), bone("foot_R", "lower_leg_R", [4, 44]),
    ]
    parts = [
        part("head", "head", (42, 46), (230, 178, 118, 255), 50), part("torso_armor", "chest", (58, 76), (94, 103, 119, 255), 20),
        part("pelvis_armor", "pelvis", (48, 36), (72, 76, 88, 255), 18), part("upper_arm_L", "upper_arm_L", (24, 52), (92, 116, 160, 255), 22),
        part("lower_arm_L", "lower_arm_L", (22, 46), (92, 116, 160, 255), 23), part("hand_L", "hand_L", (20, 20), (230, 178, 118, 255), 24),
        part("upper_arm_R", "upper_arm_R", (24, 52), (92, 116, 160, 255), 22), part("lower_arm_R", "lower_arm_R", (22, 46), (92, 116, 160, 255), 23),
        part("hand_R", "hand_R", (20, 20), (230, 178, 118, 255), 24), part("sword", "weapon", (92, 14), (198, 210, 224, 255), 60),
        part("upper_leg_L", "upper_leg_L", (26, 58), (54, 74, 112, 255), 10), part("lower_leg_L", "lower_leg_L", (24, 54), (48, 60, 86, 255), 11), part("foot_L", "foot_L", (34, 18), (38, 36, 34, 255), 12),
        part("upper_leg_R", "upper_leg_R", (26, 58), (54, 74, 112, 255), 10), part("lower_leg_R", "lower_leg_R", (24, 54), (48, 60, 86, 255), 11), part("foot_R", "foot_R", (34, 18), (38, 36, 34, 255), 12),
    ]
    sockets = [{"name": "weapon_socket_R", "bone": "hand_R", "local_position": [18, 0], "local_rotation_degrees": 0}, {"name": "slash_fx_socket_R", "bone": "weapon", "local_position": [80, 0], "local_rotation_degrees": 0}]
    motions = [
        motion(case_id, "idle", "idle", 1.0, True, [pos("pelvis", [(0, [0, 0]), (0.5, [0, -2]), (1.0, [0, 0])]), rot("weapon", [(0, -5), (0.5, -2), (1, -5)])]),
        motion(case_id, "combat_run", "move", 0.8, True, [rot("upper_leg_L", [(0, -16), (0.4, 18), (0.8, -16)]), rot("upper_leg_R", [(0, 18), (0.4, -16), (0.8, 18)]), rot("weapon", [(0, -8), (0.4, 8), (0.8, -8)])]),
        motion(case_id, "slash_attack", "action", 0.6, False, [rot("upper_arm_R", [(0, -50), (0.16, -80), (0.24, 68), (0.6, 8)]), rot("weapon", [(0, -70), (0.16, -110), (0.24, 70), (0.6, 5)])], [{"time": 0.17, "name": "slash_fx", "target": "slash_fx_socket_R"}, {"time": 0.18, "name": "hitbox_on", "target": "sword_hitbox"}, {"time": 0.29, "name": "hitbox_off", "target": "sword_hitbox"}]),
    ]
    write_case(case_id, "weapon_humanoid", bones, parts, sockets, [{"name": "sword_hitbox", "anchor": "slash_fx_socket_R", "size": [90, 28], "offset": [0, 0]}], motions, "Weapon humanoid fixture for sockets, slash event timing, and weapon attachment validation.", [(190, 40, 42, 46, (230, 178, 118, 255)), (181, 90, 60, 78, (94, 103, 119, 255)), (250, 105, 112, 16, (198, 210, 224, 255)), (150, 168, 28, 82, (54, 74, 112, 255)), (220, 168, 28, 82, (54, 74, 112, 255))], (94, 103, 119, 255))


def make_beast() -> None:
    case_id = "case_03_quadruped_beast"
    bones = [
        bone("root", None, [205, 210]), bone("pelvis", "root", [-50, 0]), bone("spine_01", "pelvis", [45, -8]), bone("spine_02", "spine_01", [50, 2]), bone("chest", "spine_02", [45, -8]), bone("neck", "chest", [34, -20]), bone("head", "neck", [38, -10]), bone("jaw", "head", [18, 18]),
        bone("tail_01", "pelvis", [-42, -4]), bone("tail_02", "tail_01", [-36, -2]), bone("tail_03", "tail_02", [-30, 0]),
        bone("front_upper_leg_L", "chest", [10, 34]), bone("front_lower_leg_L", "front_upper_leg_L", [6, 36]), bone("front_paw_L", "front_lower_leg_L", [10, 32]),
        bone("front_upper_leg_R", "chest", [34, 34]), bone("front_lower_leg_R", "front_upper_leg_R", [6, 36]), bone("front_paw_R", "front_lower_leg_R", [10, 32]),
        bone("rear_upper_leg_L", "pelvis", [-14, 34]), bone("rear_lower_leg_L", "rear_upper_leg_L", [6, 38]), bone("rear_paw_L", "rear_lower_leg_L", [10, 32]),
        bone("rear_upper_leg_R", "pelvis", [12, 34]), bone("rear_lower_leg_R", "rear_upper_leg_R", [6, 38]), bone("rear_paw_R", "rear_lower_leg_R", [10, 32]),
    ]
    parts = [
        part("body", "spine_01", (120, 58), (99, 126, 80, 255), 20), part("chest", "chest", (58, 54), (118, 145, 91, 255), 21),
        part("neck", "neck", (52, 28), (118, 145, 91, 255), 22), part("head", "head", (58, 42), (128, 156, 96, 255), 30), part("jaw", "jaw", (34, 18), (100, 118, 82, 255), 31),
        part("tail_base", "tail_01", (50, 20), (90, 112, 72, 255), 10), part("tail_mid", "tail_02", (44, 18), (90, 112, 72, 255), 10), part("tail_tip", "tail_03", (34, 16), (90, 112, 72, 255), 10),
        part("front_upper_leg_L", "front_upper_leg_L", (22, 46), (78, 94, 66, 255), 12), part("front_lower_leg_L", "front_lower_leg_L", (20, 40), (78, 94, 66, 255), 13), part("front_paw_L", "front_paw_L", (34, 16), (54, 58, 48, 255), 14),
        part("front_upper_leg_R", "front_upper_leg_R", (22, 46), (78, 94, 66, 255), 12), part("front_lower_leg_R", "front_lower_leg_R", (20, 40), (78, 94, 66, 255), 13), part("front_paw_R", "front_paw_R", (34, 16), (54, 58, 48, 255), 14),
        part("rear_upper_leg_L", "rear_upper_leg_L", (24, 50), (78, 94, 66, 255), 12), part("rear_lower_leg_L", "rear_lower_leg_L", (20, 42), (78, 94, 66, 255), 13), part("rear_paw_L", "rear_paw_L", (34, 16), (54, 58, 48, 255), 14),
        part("rear_upper_leg_R", "rear_upper_leg_R", (24, 50), (78, 94, 66, 255), 12), part("rear_lower_leg_R", "rear_lower_leg_R", (20, 42), (78, 94, 66, 255), 13), part("rear_paw_R", "rear_paw_R", (34, 16), (54, 58, 48, 255), 14),
    ]
    sockets = [{"name": "bite_hitbox_anchor", "bone": "jaw", "local_position": [18, 0], "local_rotation_degrees": 0}]
    motions = [
        motion(case_id, "idle", "idle", 1.0, True, [pos("root", [(0, [205, 210]), (0.5, [205, 207]), (1.0, [205, 210])]), rot("tail_02", [(0, 0), (0.5, 8), (1, 0)])]),
        motion(case_id, "walk", "move", 1.0, True, [rot("front_upper_leg_L", [(0, -15), (0.5, 16), (1, -15)]), rot("front_upper_leg_R", [(0, 16), (0.5, -15), (1, 16)]), rot("rear_upper_leg_L", [(0, 16), (0.5, -15), (1, 16)]), rot("rear_upper_leg_R", [(0, -15), (0.5, 16), (1, -15)])]),
        motion(case_id, "bite_attack", "action", 0.65, False, [rot("neck", [(0, -4), (0.18, -16), (0.28, 14), (0.65, 0)]), rot("jaw", [(0, 0), (0.18, 22), (0.28, -8), (0.65, 0)])], [{"time": 0.24, "name": "hitbox_on", "target": "bite_hitbox"}, {"time": 0.36, "name": "hitbox_off", "target": "bite_hitbox"}]),
    ]
    write_case(case_id, "quadruped", bones, parts, sockets, [{"name": "bite_hitbox", "anchor": "bite_hitbox_anchor", "size": [44, 30], "offset": [10, 0]}], motions, "Quadruped beast fixture for non-humanoid bones, walk loop, bite hitbox, and tail motion.", [(120, 126, 140, 58, (99, 126, 80, 255)), (260, 100, 58, 42, (128, 156, 96, 255)), (70, 142, 80, 20, (90, 112, 72, 255)), (150, 182, 22, 72, (78, 94, 66, 255)), (230, 182, 22, 72, (78, 94, 66, 255)), (285, 182, 22, 72, (78, 94, 66, 255))], (99, 126, 80, 255))


def make_trap() -> None:
    case_id = "case_04_mechanical_trap"
    bones = [
        bone("root", None, [210, 230]), bone("base", "root", [0, 0]), bone("hinge", "base", [0, -72]), bone("swing_arm", "hinge", [0, 0]), bone("blade", "swing_arm", [0, 78]), bone("gear_main", "base", [-46, -38]), bone("pressure_plate", "base", [82, 12]),
    ]
    parts = [
        part("stone_base", "base", (120, 38), (108, 104, 98, 255), 1), part("hinge_cap", "hinge", (38, 38), (102, 114, 124, 255), 30),
        part("swing_arm", "swing_arm", (18, 110), (116, 88, 54, 255), 20, [0, 50]), part("axe_blade", "blade", (76, 50), (188, 196, 204, 255), 35),
        part("gear_main", "gear_main", (48, 48), (130, 124, 112, 255), 10), part("pressure_plate", "pressure_plate", (72, 18), (96, 94, 88, 255), 5),
    ]
    sockets = [{"name": "hazard_hitbox_anchor", "bone": "blade", "local_position": [0, 0], "local_rotation_degrees": 0}, {"name": "trigger_area_anchor", "bone": "pressure_plate", "local_position": [0, 0], "local_rotation_degrees": 0}]
    motions = [
        motion(case_id, "idle", "idle", 1.0, True, [rot("swing_arm", [(0, -20), (0.5, -18), (1, -20)])]),
        motion(case_id, "armed", "move", 0.8, True, [rot("gear_main", [(0, 0), (0.4, 90), (0.8, 0)]), pos("pressure_plate", [(0, [82, 12]), (0.4, [82, 16]), (0.8, [82, 12])])]),
        motion(case_id, "trigger", "action", 0.75, False, [rot("swing_arm", [(0, -35), (0.16, -55), (0.32, 58), (0.75, -20)]), rot("gear_main", [(0, 0), (0.32, 180), (0.75, 360)])], [{"time": 0.26, "name": "hazard_on", "target": "axe_hazard"}, {"time": 0.46, "name": "hazard_off", "target": "axe_hazard"}]),
    ]
    write_case(case_id, "mechanical", bones, parts, sockets, [{"name": "axe_hazard", "anchor": "hazard_hitbox_anchor", "size": [84, 56], "offset": [0, 0]}], motions, "Mechanical trap fixture for hinge pivot, trigger events, and hazard hitbox timing.", [(142, 225, 136, 38, (108, 104, 98, 255)), (194, 110, 38, 38, (102, 114, 124, 255)), (204, 132, 18, 110, (116, 88, 54, 255)), (171, 70, 76, 50, (188, 196, 204, 255)), (120, 165, 48, 48, (130, 124, 112, 255)), (280, 240, 72, 18, (96, 94, 88, 255))], (116, 88, 54, 255))


def make_negative_cases() -> None:
    base_part = NEGATIVE / "_shared" / "parts" / "part.png"
    make_part(base_part, (32, 32), (220, 80, 80, 255))
    root_bone = bone("root", None, [0, 0])
    valid_part = {"id": "part", "file": "../_shared/parts/part.png", "bone": "root", "pivot": [16, 16], "offset": [0, 0], "z_index": 1}

    write_json(NEGATIVE / "missing_part" / "rig_meta.json", {"schema_version": "1.0", "case_id": "missing_part", "object_type": "custom", "skeleton": {"bones": [root_bone]}, "parts": [{**valid_part, "file": "parts/not_here.png"}]})
    write_json(NEGATIVE / "bone_cycle" / "rig_meta.json", {"schema_version": "1.0", "case_id": "bone_cycle", "object_type": "custom", "skeleton": {"bones": [bone("a", "b", [0, 0]), bone("b", "a", [0, 0])]}, "parts": [{**valid_part, "bone": "a"}]})
    write_json(NEGATIVE / "pivot_out_of_bounds" / "rig_meta.json", {"schema_version": "1.0", "case_id": "pivot_out_of_bounds", "object_type": "custom", "skeleton": {"bones": [root_bone]}, "parts": [{**valid_part, "pivot": [80, 80]}]})
    write_json(NEGATIVE / "missing_bone_motion" / "rig_meta.json", {"schema_version": "1.0", "case_id": "missing_bone_motion", "object_type": "custom", "skeleton": {"bones": [root_bone]}, "parts": [valid_part]})
    write_json(NEGATIVE / "missing_bone_motion" / "motions" / "action.json", motion("missing_bone_motion", "bad_action", "action", 0.4, False, [rot("not_a_bone", [(0, 0), (0.2, 10)])], [{"time": 0.1, "name": "hitbox_on"}, {"time": 0.2, "name": "hitbox_off"}]))
    write_json(NEGATIVE / "action_missing_event" / "rig_meta.json", {"schema_version": "1.0", "case_id": "action_missing_event", "object_type": "custom", "skeleton": {"bones": [root_bone]}, "parts": [valid_part]})
    write_json(NEGATIVE / "action_missing_event" / "motions" / "action.json", motion("action_missing_event", "bad_action", "action", 0.4, False, [rot("root", [(0, 0), (0.2, 10)])], [{"time": 0.1, "name": "hitbox_on"}]))


def main() -> int:
    make_humanoid()
    make_swordsman()
    make_beast()
    make_trap()
    make_negative_cases()
    print(f"Generated fixtures under {PROJECT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
