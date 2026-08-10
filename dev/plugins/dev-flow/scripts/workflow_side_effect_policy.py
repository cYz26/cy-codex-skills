from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from workflow_authority_delta import (
    AUTO_CLEAN,
    CONTINUE,
    CONTINUE_WITH_MINIMAL_GUARD,
    resolve_authority_delta,
)


SIDE_EFFECT_IDS = {
    "workspace.read",
    "draft.write",
    "canonical.write",
    "code_test.modify",
    "git.branch_worktree",
    "git.commit",
    "git.push",
    "git.push_pr",
    "github.control_plane_write",
    "tracker.read",
    "tracker.write",
    "dependency.install_update",
    "model.invoke",
    "destructive.cleanup",
    "release.promote_local",
    "release.publish",
    "devflow.source.fast_forward_named",
    "plugin.cache.refresh_named",
    "devflow.project.refresh_named",
    "openspec.archive",
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
    *,
    request: dict[str, Any] | None = None,
    authority_envelope: dict[str, Any] | None = None,
    evidence: dict[str, Any] | None = None,
    standing_contract: dict[str, Any] | None = None,
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
    if effect == "model.invoke" and not any(
        item is not None
        for item in (request, authority_envelope, evidence, standing_contract)
    ):
        return {
            "effect": effect,
            "authorized": False,
            "requiredAuthorization": required,
            "denial": str(policy["denial"]),
            "reason": "authority_context_required",
        }
    if any(
        item is not None
        for item in (request, authority_envelope, evidence, standing_contract)
    ):
        if request is None or authority_envelope is None or evidence is None:
            return {
                "effect": effect,
                "authorized": False,
                "requiredAuthorization": required,
                "denial": "block",
                "reason": "authority_context_incomplete",
                "authorityResolution": None,
            }
        request_data = dict(request)
        request_data.setdefault("effect", effect)
        request_data["policyEffect"] = effect
        resolution = resolve_authority_delta(
            request=request_data,
            authority_envelope=authority_envelope,
            evidence=evidence,
            standing_contract=standing_contract,
        )
        authorized = resolution["decision"] in {
            CONTINUE,
            CONTINUE_WITH_MINIMAL_GUARD,
            AUTO_CLEAN,
        }
        return {
            "effect": effect,
            "authorized": authorized,
            "requiredAuthorization": required,
            "denial": None if authorized else str(policy["denial"]),
            "reason": (
                "authority_delta_resolved"
                if authorized
                else "authority_delta_not_resolved"
            ),
            "authorityResolution": resolution,
        }
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
