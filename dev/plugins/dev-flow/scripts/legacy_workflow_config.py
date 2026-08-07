from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
REPORT_KIND = "devflow-legacy-workflow-config-inspection"
CANONICAL_TARGET_CONFIGURATION = {
    "projectContract": 2,
    "workflow": {"mode": "full-openspec"},
}
LEGACY_WORKFLOW_FIELD_ALIASES = {
    "methodology_profile": ("methodology_profile", "methodologyProfile"),
    "roadmap_provider": ("roadmap_provider", "roadmapProvider"),
    "provider_selectors": ("provider_selectors", "providerSelectors"),
    "roadmap_bindings": ("roadmap_bindings", "roadmapBindings"),
}
SUPERPOWERS_SKILLS = (
    "brainstorming",
    "executing-plans",
    "finishing-a-development-branch",
    "receiving-code-review",
    "requesting-code-review",
    "subagent-driven-development",
    "systematic-debugging",
    "test-driven-development",
    "using-git-worktrees",
    "using-superpowers",
    "verification-before-completion",
    "writing-plans",
)
GSD_SKILLS = (
    "gsd-discuss-phase",
    "gsd-execute-phase",
    "gsd-new-project",
    "gsd-plan-phase",
    "gsd-progress",
    "gsd-verify-work",
)
GSD_AGENT_NAMES = (
    "gsd-code-fixer",
    "gsd-code-reviewer",
    "gsd-executor",
    "gsd-phase-researcher",
    "gsd-plan-checker",
    "gsd-planner",
)
GSD_AGENTS = tuple(
    f"{name}.{suffix}"
    for name in GSD_AGENT_NAMES
    for suffix in ("toml", "md")
)
HISTORY_PATHS = (
    ".codex/gsd-migration-journal",
    ".planning/STATE.md",
    ".planning/ROADMAP.md",
    ".planning/PROJECT.md",
    ".planning/REQUIREMENTS.md",
    ".planning/config.json",
    ".planning/phases",
    ".planning/codebase",
    ".planning/milestones",
    ".planning/todos",
    "docs/superpowers/specs",
    "docs/superpowers/plans",
)


def inspect_legacy_workflow_config(repo: Path) -> dict[str, Any]:
    """Inspect obsolete DevFlow configuration without mutating the project."""
    repo = Path(repo).expanduser().resolve()
    recognized_inputs: list[dict[str, Any]] = []
    conflicts: list[dict[str, str]] = []
    artifacts: list[dict[str, Any]] = []
    current_config = _read_config(repo, conflicts)
    workflow = current_config.get("workflow")
    workflow = workflow if isinstance(workflow, dict) else {}

    for canonical, aliases in LEGACY_WORKFLOW_FIELD_ALIASES.items():
        found_values: list[Any] = []
        for prefix, container in (("workflow.", workflow), ("", current_config)):
            for field in aliases:
                if field not in container:
                    continue
                value = _json_value(container[field])
                found_values.append(value)
                recognized_inputs.append(
                    {
                        "field": f"{prefix}{field}",
                        "path": ".dev-flow.json",
                        "present": True,
                        "valueType": _value_type(value),
                    }
                )
        if len({_canonical_json(value) for value in found_values}) > 1:
            conflicts.append(
                {
                    "path": ".dev-flow.json",
                    "reason": f"conflicting_legacy_{canonical}",
                }
            )

    _inspect_provider_lock(repo, recognized_inputs, artifacts, conflicts)
    _inspect_known_artifacts(repo, artifacts, conflicts)
    recognized_inputs.sort(key=lambda item: (item["path"], item["field"]))
    artifacts.sort(key=lambda item: item["path"])
    conflicts.sort(key=lambda item: (item["path"], item["reason"]))
    preserved_paths = sorted(
        item["path"]
        for item in artifacts
        if item["classification"] != "generated_candidate"
    )
    status = "manual_review_required" if conflicts else (
        "legacy_detected" if recognized_inputs or artifacts else "current"
    )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "kind": REPORT_KIND,
        "ok": not conflicts,
        "status": status,
        "readOnly": True,
        "valuesRedacted": True,
        "repo": str(repo),
        "recognizedInputs": recognized_inputs,
        "artifacts": artifacts,
        "conflicts": conflicts,
        "preservedPaths": preserved_paths,
        "targetConfiguration": _json_value(CANONICAL_TARGET_CONFIGURATION),
        "manualActions": _manual_actions(bool(recognized_inputs or artifacts), bool(conflicts)),
    }


def _inspect_provider_lock(
    repo: Path,
    recognized: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
    conflicts: list[dict[str, str]],
) -> None:
    relative = ".planning/devflow/providers.lock.json"
    path = _inspection_path(repo, relative, "provider_lock", artifacts, conflicts)
    if path is None:
        return
    if not _lexists(path):
        return
    if path.is_symlink() or not path.is_file():
        _add_conflict_artifact(
            artifacts,
            conflicts,
            relative,
            "provider_lock_not_regular_file",
            "provider_lock",
        )
        return
    try:
        value = json.loads(path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        _add_conflict_artifact(
            artifacts,
            conflicts,
            relative,
            f"provider_lock_unreadable:{type(error).__name__}",
            "provider_lock",
        )
        return
    if not isinstance(value, dict) or not isinstance(value.get("providers"), dict):
        _add_conflict_artifact(
            artifacts,
            conflicts,
            relative,
            "provider_lock_invalid_schema",
            "provider_lock",
        )
        return
    artifacts.append(
        {
            "path": relative,
            "kind": "provider_lock",
            "classification": "generated_candidate",
            "reason": "recognized_generated_provider_lock",
        }
    )
    for index, (_, provider_value) in enumerate(sorted(value["providers"].items())):
        recognized.append(
            {
                "field": f"providerLock.providers[{index}]",
                "path": relative,
                "present": True,
                "valueType": _value_type(provider_value),
            }
        )


def _inspect_known_artifacts(
    repo: Path,
    artifacts: list[dict[str, Any]],
    conflicts: list[dict[str, str]],
) -> None:
    for root in (".agents/skills", ".codex/skills"):
        for skill in (*SUPERPOWERS_SKILLS, *GSD_SKILLS):
            _inspect_legacy_path(
                repo,
                f"{root}/{skill}",
                "legacy_skill",
                artifacts,
                conflicts,
            )
    for root in (".codex/agents", ".agents/agents"):
        for agent in GSD_AGENTS:
            _inspect_legacy_path(
                repo,
                f"{root}/{agent}",
                "legacy_agent",
                artifacts,
                conflicts,
            )

    _inspect_legacy_agent_config(repo, artifacts, conflicts)
    _inspect_legacy_hook_config(repo, artifacts, conflicts)
    _inspect_legacy_hook_files(repo, artifacts, conflicts)

    for relative, kind in (
        (".codex/.gsd-profile", "gsd_profile"),
        (".codex/gsd-core", "gsd_runtime"),
        (".codex/gsd-file-manifest.json", "gsd_manifest"),
        (".codex/gsd-install-state.json", "gsd_install_state"),
    ):
        _inspect_generated_marker(repo, relative, kind, artifacts, conflicts)

    for relative in HISTORY_PATHS:
        path = _inspection_path(repo, relative, "historical_data", artifacts, conflicts)
        if path is None:
            continue
        if not _lexists(path):
            continue
        if path.is_symlink():
            _add_conflict_artifact(
                artifacts,
                conflicts,
                relative,
                "historical_path_is_symlink",
                "historical_data",
            )
        else:
            artifacts.append(
                {
                    "path": relative,
                    "kind": "historical_data",
                    "classification": "user_history_data",
                    "reason": "historical_or_user_authored_content_is_preserved",
                }
            )


def _inspect_legacy_agent_config(
    repo: Path,
    artifacts: list[dict[str, Any]],
    conflicts: list[dict[str, str]],
) -> None:
    relative = ".codex/config.toml"
    path = _inspection_path(repo, relative, "legacy_agent_config", artifacts, conflicts)
    if path is None:
        return
    if not _lexists(path):
        return
    if path.is_symlink() or not path.is_file():
        _add_conflict_artifact(
            artifacts,
            conflicts,
            relative,
            "legacy_agent_config_not_regular_file",
            "legacy_agent_config",
        )
        return
    try:
        payload = path.read_text()
    except (OSError, UnicodeError) as error:
        _add_conflict_artifact(
            artifacts,
            conflicts,
            relative,
            f"legacy_agent_config_unreadable:{type(error).__name__}",
            "legacy_agent_config",
        )
        return
    if _contains_legacy_marker(payload):
        artifacts.append(
            {
                "path": relative,
                "kind": "legacy_agent_config",
                "classification": "preserved_unknown",
                "reason": "legacy_agent_registration_present_but_mixed_or_user_ownership_is_unproven",
            }
        )


def _inspect_legacy_hook_config(
    repo: Path,
    artifacts: list[dict[str, Any]],
    conflicts: list[dict[str, str]],
) -> None:
    relative = ".codex/hooks.json"
    path = _inspection_path(repo, relative, "legacy_hook_config", artifacts, conflicts)
    if path is None:
        return
    if not _lexists(path):
        return
    if path.is_symlink() or not path.is_file():
        _add_conflict_artifact(
            artifacts,
            conflicts,
            relative,
            "legacy_hook_config_not_regular_file",
            "legacy_hook_config",
        )
        return
    try:
        payload = json.loads(path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        _add_conflict_artifact(
            artifacts,
            conflicts,
            relative,
            f"legacy_hook_config_unreadable:{type(error).__name__}",
            "legacy_hook_config",
        )
        return
    if _contains_legacy_marker(payload):
        artifacts.append(
            {
                "path": relative,
                "kind": "legacy_hook_config",
                "classification": "preserved_unknown",
                "reason": "legacy_hook_marker_present_but_mixed_or_user_ownership_is_unproven",
            }
        )


def _inspect_legacy_hook_files(
    repo: Path,
    artifacts: list[dict[str, Any]],
    conflicts: list[dict[str, str]],
) -> None:
    root = _inspection_path(repo, ".codex/hooks", "legacy_hook_root", artifacts, conflicts)
    if root is None:
        return
    if not _lexists(root):
        return
    if root.is_symlink() or not root.is_dir():
        _add_conflict_artifact(
            artifacts,
            conflicts,
            ".codex/hooks",
            "legacy_hook_root_not_regular_directory",
            "legacy_hook_root",
        )
        return
    candidates = {
        path
        for pattern in ("gsd-*", "superpowers-*")
        for path in root.glob(pattern)
    }
    for path in sorted(candidates):
        relative = path.relative_to(repo).as_posix()
        if path.is_symlink() or not path.is_file():
            _add_conflict_artifact(
                artifacts,
                conflicts,
                relative,
                "legacy_hook_file_not_regular_file",
                "legacy_hook",
            )
            continue
        artifacts.append(
            {
                "path": relative,
                "kind": "legacy_hook",
                "classification": "preserved_unknown",
                "reason": "legacy_hook_filename_is_recognized_but_generation_is_not_attested",
            }
        )


def _contains_legacy_marker(value: Any) -> bool:
    if isinstance(value, str):
        lowered = value.lower()
        return "gsd" in lowered or "superpowers" in lowered
    if isinstance(value, list):
        return any(_contains_legacy_marker(item) for item in value)
    if isinstance(value, dict):
        return any(
            _contains_legacy_marker(key) or _contains_legacy_marker(item)
            for key, item in value.items()
        )
    return False


def _inspect_legacy_path(
    repo: Path,
    relative: str,
    kind: str,
    artifacts: list[dict[str, Any]],
    conflicts: list[dict[str, str]],
) -> None:
    path = _inspection_path(repo, relative, kind, artifacts, conflicts)
    if path is None:
        return
    if not _lexists(path):
        return
    if path.is_symlink():
        if not path.exists():
            _add_conflict_artifact(
                artifacts,
                conflicts,
                relative,
                "broken_legacy_symlink",
                kind,
            )
            return
        artifacts.append(
            {
                "path": relative,
                "kind": kind,
                "classification": "generated_candidate",
                "reason": "recognized_legacy_generated_link",
                "linkTargetKind": "absolute" if path.readlink().is_absolute() else "relative",
            }
        )
        return
    artifacts.append(
        {
            "path": relative,
            "kind": kind,
            "classification": "preserved_unknown",
            "reason": "ownership_or_local_edits_not_proven",
        }
    )


def _inspect_generated_marker(
    repo: Path,
    relative: str,
    kind: str,
    artifacts: list[dict[str, Any]],
    conflicts: list[dict[str, str]],
) -> None:
    path = _inspection_path(repo, relative, kind, artifacts, conflicts)
    if path is None:
        return
    if not _lexists(path):
        return
    if path.is_symlink():
        if not path.exists():
            reason = "broken_legacy_symlink"
        else:
            reason = "generated_marker_is_symlink"
        _add_conflict_artifact(artifacts, conflicts, relative, reason, kind)
        return
    if kind == "gsd_runtime" and not path.is_dir():
        _add_conflict_artifact(
            artifacts,
            conflicts,
            relative,
            "gsd_runtime_not_directory",
            kind,
        )
        return
    if kind == "gsd_profile" and not path.is_file():
        _add_conflict_artifact(
            artifacts,
            conflicts,
            relative,
            "gsd_profile_not_regular_file",
            kind,
        )
        return
    if kind in {"gsd_manifest", "gsd_install_state"}:
        try:
            payload = json.loads(path.read_text())
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            _add_conflict_artifact(
                artifacts,
                conflicts,
                relative,
                f"{kind}_unreadable:{type(error).__name__}",
                kind,
            )
            return
        if not isinstance(payload, dict):
            _add_conflict_artifact(
                artifacts,
                conflicts,
                relative,
                f"{kind}_invalid_schema",
                kind,
            )
            return
    artifacts.append(
        {
            "path": relative,
            "kind": kind,
            "classification": "generated_candidate",
            "reason": "recognized_generated_runtime_marker",
        }
    )


def _add_conflict_artifact(
    artifacts: list[dict[str, Any]],
    conflicts: list[dict[str, str]],
    path: str,
    reason: str,
    kind: str,
) -> None:
    artifacts.append(
        {
            "path": path,
            "kind": kind,
            "classification": "conflict",
            "reason": reason,
        }
    )
    conflicts.append({"path": path, "reason": reason})


def _lexists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _inspection_path(
    repo: Path,
    relative: str,
    kind: str,
    artifacts: list[dict[str, Any]],
    conflicts: list[dict[str, str]],
) -> Path | None:
    requested = Path(relative)
    if requested.is_absolute() or not requested.parts or ".." in requested.parts:
        _add_conflict_artifact(
            artifacts,
            conflicts,
            relative,
            "legacy_path_invalid",
            kind,
        )
        return None
    cursor = repo
    for segment in requested.parts[:-1]:
        cursor = cursor / segment
        if cursor.is_symlink() or (cursor.exists() and not cursor.is_dir()):
            offending = cursor.relative_to(repo).as_posix()
            conflict = {"path": offending, "reason": "legacy_path_parent_untrusted"}
            if conflict not in conflicts:
                _add_conflict_artifact(
                    artifacts,
                    conflicts,
                    offending,
                    "legacy_path_parent_untrusted",
                    kind,
                )
            return None
    return repo.joinpath(*requested.parts)


def _read_config(repo: Path, conflicts: list[dict[str, str]]) -> dict[str, Any]:
    path = repo / ".dev-flow.json"
    if not _lexists(path):
        return {}
    if path.is_symlink() or not path.is_file():
        conflicts.append(
            {
                "path": ".dev-flow.json",
                "reason": "config_not_regular_file",
            }
        )
        return {}
    try:
        value = json.loads(path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        conflicts.append(
            {
                "path": ".dev-flow.json",
                "reason": f"config_unreadable:{type(error).__name__}",
            }
        )
        return {}
    if not isinstance(value, dict):
        conflicts.append(
            {
                "path": ".dev-flow.json",
                "reason": "config_not_object",
            }
        )
        return {}
    return value


def _manual_actions(legacy_detected: bool, conflicted: bool) -> list[str]:
    actions: list[str] = []
    if conflicted:
        actions.append("Review each conflict and preserve the original path until ownership is known.")
    if legacy_detected:
        actions.append(
            "Review the canonical target configuration and preserve unreported current settings "
            "before any separately authorized migration."
        )
    actions.append("Keep historical and ambiguous paths unless a separate cleanup is explicitly approved.")
    return actions


def _json_value(value: Any) -> Any:
    """Return a detached, deterministic JSON value."""
    return json.loads(json.dumps(value, sort_keys=True))


def _value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, (int, float)):
        return "number"
    return "unknown"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


inspect = inspect_legacy_workflow_config
