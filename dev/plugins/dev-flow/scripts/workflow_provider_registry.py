from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


CAPABILITY_IDS = {
    "decision-resolution",
    "implementation-planning",
    "test-first-execution",
    "root-cause-diagnosis",
    "change-review",
    "completion-proof",
    "execution-orchestration",
    "architecture-guidance",
    "goal-definition",
    "roadmap-lifecycle",
}

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


def load_provider_registry(plugin_root: Path) -> dict[str, Any]:
    plugin_root = Path(plugin_root).resolve()
    profiles_path = plugin_root / "docs" / "provider_profiles.json"
    effects_path = plugin_root / "docs" / "provider_side_effect_policy.json"
    profiles = json.loads(profiles_path.read_text())
    effects = json.loads(effects_path.read_text())
    validate_provider_registry(profiles, effects)
    profiles["sideEffects"] = effects["effects"]
    profiles["defaultDeny"] = effects["defaultDeny"]
    profiles["sourcePaths"] = {
        "profiles": str(profiles_path),
        "sideEffects": str(effects_path),
    }
    return profiles


def validate_provider_registry(profiles: dict[str, Any], effects: dict[str, Any]) -> None:
    methodology_profiles = set(profiles.get("methodologyProfiles", {}))
    if methodology_profiles != {"core", "lean-matt", "strict-superpowers"}:
        raise ValueError(f"invalid methodology profiles: {sorted(methodology_profiles)}")
    roadmap_providers = set(profiles.get("roadmapProviders", {}))
    if roadmap_providers != {"none", "gsd"}:
        raise ValueError(f"invalid roadmap providers: {sorted(roadmap_providers)}")
    capabilities = set(profiles.get("capabilities", {}))
    if capabilities != CAPABILITY_IDS:
        raise ValueError(f"invalid capability ids: {sorted(capabilities)}")
    side_effects = set(effects.get("effects", {}))
    if side_effects != SIDE_EFFECT_IDS:
        raise ValueError(f"invalid side-effect ids: {sorted(side_effects)}")
    if effects.get("defaultDeny") is not True:
        raise ValueError("provider side effects must be default-deny")


def side_effect_decision(
    plugin_root: Path,
    effect: str,
    authorizations: set[str] | None = None,
) -> dict[str, Any]:
    registry = load_provider_registry(plugin_root)
    policy = registry["sideEffects"].get(effect)
    if not isinstance(policy, dict):
        return {
            "effect": effect,
            "authorized": False,
            "requiredAuthorization": None,
            "denial": "block",
            "reason": "unknown_effect_default_denied",
        }
    required = str(policy["authorization"])
    granted = set(authorizations or set())
    authorized = required in granted
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
    return {**action, **side_effect_decision(plugin_root, str(action.get("effect", "")), authorizations)}
