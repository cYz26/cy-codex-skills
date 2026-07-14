from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


SIDE_EFFECT_IDS = {
    "workspace.read",
    "draft.write",
    "canonical.write",
    "code_test.modify",
    "git.branch_worktree",
    "git.commit",
    "git.push_pr",
    "tracker.read",
    "tracker.write",
    "dependency.install_update",
    "destructive.cleanup",
    "archive_release",
    "goal.state",
}


def default_plugin_root() -> Path:
    configured = os.environ.get("DEVFLOW_PLUGIN_ROOT") or os.environ.get("PLUGIN_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[1]


def load_side_effect_policy(plugin_root: Path | None = None) -> dict[str, Any]:
    root = Path(plugin_root or default_plugin_root()).resolve()
    source = root / "docs" / "side_effect_policy.json"
    policy = json.loads(source.read_text())
    effects = policy.get("effects", {})
    if set(effects) != SIDE_EFFECT_IDS:
        raise ValueError(f"invalid side-effect ids: {sorted(effects)}")
    if policy.get("defaultDeny") is not True:
        raise ValueError("DevFlow side effects must be default-deny")
    return {**policy, "sourcePath": str(source)}


def side_effect_decision(
    plugin_root: Path,
    effect: str,
    authorizations: set[str] | None = None,
) -> dict[str, Any]:
    policy = load_side_effect_policy(plugin_root)["effects"].get(effect)
    if not isinstance(policy, dict):
        return {
            "effect": effect,
            "authorized": False,
            "requiredAuthorization": None,
            "denial": "block",
            "reason": "unknown_effect_default_denied",
        }
    required = str(policy["authorization"])
    authorized = required in set(authorizations or set())
    return {
        "effect": effect,
        "authorized": authorized,
        "requiredAuthorization": required,
        "denial": None if authorized else str(policy["denial"]),
        "reason": "authorized" if authorized else "authorization_missing",
    }


def authorize_action(
    plugin_root: Path,
    action: dict[str, Any],
    authorizations: set[str] | None = None,
) -> dict[str, Any]:
    return {
        **action,
        **side_effect_decision(plugin_root, str(action.get("effect", "")), authorizations),
    }
