from __future__ import annotations

import json
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any

from workflow_mode_routing import read_workflow_mode_config
from workflow_roadmap_provider import validate_roadmap_bindings
from workflow_state import parse_state


ARCHIVE_POLICIES = {"confirm-on-risk", "manual", "auto-after-explicit-request"}
DEFAULT_ARCHIVE_POLICY = "confirm-on-risk"
STATE_GATE_KEYS = (
    "spec_approved",
    "plan_written",
    "implementation_done",
    "verification_passed",
    "state_updated",
)


def read_archive_policy(repo: Path) -> dict[str, Any]:
    config_path = repo / ".dev-flow.json"
    configured = None
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text())
        except json.JSONDecodeError:
            data = {}
        archive = data.get("archive") if isinstance(data.get("archive"), dict) else {}
        configured = archive.get("policy")
    if configured in ARCHIVE_POLICIES:
        return {"policy": configured, "source": str(config_path)}
    report = {"policy": DEFAULT_ARCHIVE_POLICY, "source": "default"}
    if configured:
        report["ignoredPolicy"] = configured
        report["source"] = str(config_path)
    return report


def archive_status(
    repo: Path,
    change: str | None = None,
    *,
    explicit_request: bool = False,
    allow_risk: bool = False,
) -> dict[str, Any]:
    repo = repo.resolve()
    state = parse_state(repo)
    change_id = change or str(state.get("current_change", {}).get("id") or "")
    policy = read_archive_policy(repo)
    risks: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    workflow_config = read_workflow_mode_config(repo)
    if not workflow_config.get("valid", True):
        blockers.append(
            risk(
                "invalid_workflow_config",
                "Archive is blocked because .dev-flow.json is malformed.",
                errors=workflow_config.get("config_errors", []),
            )
        )

    if not change_id or change_id == "none":
        blockers.append(risk("missing_change", "No OpenSpec change id was provided."))
    else:
        blockers.extend(change_artifact_risks(repo, change_id))

    failed_gates = failed_state_gates(state)
    if failed_gates:
        blockers.append(
            risk(
                "failed_state_gates",
                "State gates are not ready for archive.",
                gates=failed_gates,
            )
        )

    if change_id and change_id != "none":
        blockers.extend(roadmap_binding_archive_risks(repo, change_id, state))

    if change_id and change_id != "none":
        risks.extend(task_risks(repo, change_id))
        risks.extend(dirty_worktree_risks(repo, change_id))

    all_risks = [*blockers, *risks]
    ready = not blockers
    effective_allow_risk = allow_risk or bool(state.get("gates", {}).get("archive_allowed"))
    approval_required = archive_approval_required(
        policy["policy"],
        explicit_request=explicit_request,
        has_risks=bool(risks),
        has_blockers=bool(blockers),
        allow_risk=effective_allow_risk,
    )
    can_archive = ready and not approval_required
    return {
        "ok": ready,
        "ready": ready,
        "canArchive": can_archive,
        "approvalRequired": approval_required,
        "policy": policy["policy"],
        "policySource": policy["source"],
        "ignoredPolicy": policy.get("ignoredPolicy"),
        "change": change_id or None,
        "risks": all_risks,
        "stateGates": state.get("gates", {}),
        "explicitRequest": bool(explicit_request),
        "allowRisk": bool(effective_allow_risk),
        "nextAction": archive_next_action(ready, approval_required, risks, blockers),
    }


def failed_state_gates(state: dict[str, Any]) -> list[str]:
    gates = state.get("gates", {}) if isinstance(state.get("gates"), dict) else {}
    return [key for key in STATE_GATE_KEYS if not bool(gates.get(key))]


def change_artifact_risks(repo: Path, change: str) -> list[dict[str, Any]]:
    change_root = repo / "openspec" / "changes" / change
    if not change_root.exists():
        return [risk("missing_change", f"OpenSpec change `{change}` does not exist.")]
    missing = []
    for name in ("proposal.md", "design.md", "tasks.md"):
        if not (change_root / name).exists():
            missing.append(name)
    if not any((change_root / "specs").rglob("spec.md")):
        missing.append("specs/**/*.md")
    if not missing:
        return []
    return [risk("incomplete_artifacts", "OpenSpec artifacts are incomplete.", missing=missing)]


def task_risks(repo: Path, change: str) -> list[dict[str, Any]]:
    tasks = repo / "openspec" / "changes" / change / "tasks.md"
    if not tasks.exists():
        return []
    incomplete = sum(1 for line in tasks.read_text().splitlines() if line.strip().startswith("- [ ]"))
    if incomplete == 0:
        return []
    return [risk("incomplete_tasks", "OpenSpec tasks are incomplete.", count=incomplete)]


def roadmap_binding_archive_risks(
    repo: Path,
    change: str,
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    config = read_workflow_mode_config(repo)
    if not config.get("valid", True):
        return [
            risk(
                "invalid_workflow_config",
                "Roadmap binding checks cannot run against malformed .dev-flow.json.",
                errors=config.get("config_errors", []),
            )
        ]
    bindings = config.get("roadmap_bindings", {})
    binding = bindings.get(change) if isinstance(bindings, dict) else None
    if config.get("roadmap_provider") != "gsd" or not isinstance(binding, dict):
        return []
    if binding.get("status") != "active":
        return []

    results: list[dict[str, Any]] = []
    binding_report = validate_roadmap_bindings(repo, {change: binding}, "gsd")
    if not binding_report["ready"]:
        results.append(
            risk(
                "roadmap_binding_invalid",
                "The active GSD roadmap binding requires manual review.",
                reasons=binding_report["blockingReasons"],
            )
        )
    gates = state.get("gates", {}) if isinstance(state.get("gates"), dict) else {}
    verification_matches = (
        gates.get("gsd_verification_passed") is True
        and str(gates.get("gsd_verification_change")) == change
        and str(gates.get("gsd_verification_phase")) == str(binding.get("phase_id"))
    )
    if not verification_matches:
        results.append(
            risk(
                "gsd_verification_required",
                "The bound GSD phase must have recorded verification before archive.",
                phase=binding.get("phase_id"),
            )
        )
    return results


def dirty_worktree_risks(repo: Path, change: str) -> list[dict[str, Any]]:
    paths = dirty_worktree_paths(repo)
    unrelated = [path for path in paths if not archive_related_dirty_path(path, change)]
    if not unrelated:
        return []
    return [
        risk(
            "dirty_unrelated_worktree",
            "Dirty working-tree paths outside the archive scope require confirmation.",
            paths=unrelated[:20],
            count=len(unrelated),
        )
    ]


def dirty_worktree_paths(repo: Path) -> list[str]:
    if not (repo / ".git").exists():
        return []
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    paths = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:] if len(line) > 3 else line.strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path.strip())
    return paths


def archive_related_dirty_path(path: str, change: str) -> bool:
    allowed_prefixes = (
        f"openspec/changes/{change}/",
        ".planning/devflow/",
        "dev/plugins/dev-flow/",
        "plugins/dev-flow/",
    )
    allowed_exact = {
        "AGENTS.md",
        ".gitignore",
        "dev/scripts/package_devflow_release_runtime.py",
    }
    return path in allowed_exact or any(path.startswith(prefix) for prefix in allowed_prefixes)


def archive_approval_required(
    policy: str,
    *,
    explicit_request: bool,
    has_risks: bool,
    has_blockers: bool,
    allow_risk: bool,
) -> bool:
    if has_blockers:
        return True
    if policy == "manual":
        return not allow_risk
    if not explicit_request:
        return True
    if has_risks and not allow_risk:
        return True
    return False


def archive_next_action(
    ready: bool,
    approval_required: bool,
    risks: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
) -> str:
    if blockers:
        return "resolve_blockers"
    if risks and approval_required:
        return "confirm_risks"
    if approval_required:
        return "request_archive_confirmation"
    if ready:
        return "run_archive"
    return "inspect_archive_status"


def risk(code: str, message: str, **extra: Any) -> dict[str, Any]:
    payload = {"code": code, "message": message}
    payload.update(extra)
    return payload


def mutating_archive_command(command: str) -> bool:
    tokens = shell_tokens(command)
    if not tokens:
        return False
    normalized = [token.lower() for token in tokens]
    if normalized[:2] == ["openspec", "archive"]:
        return True
    if normalized[0] in {"openspec-archive-change", "openspec-archive"}:
        return True
    if normalized[:2] == ["git", "mv"]:
        return moves_change_to_archive(tokens[2:])
    if normalized[0] == "mv":
        return moves_change_to_archive(tokens[1:])
    if normalized[:2] == ["git", "rm"]:
        return removes_change_path(tokens[2:])
    if normalized[0] in {"rm", "rmdir"}:
        return removes_change_path(tokens[1:])
    return False


def archive_change_from_command(command: str) -> str | None:
    tokens = shell_tokens(command)
    if not tokens:
        return None
    normalized = [token.lower() for token in tokens]
    if normalized[:2] == ["openspec", "archive"] and len(tokens) > 2:
        return tokens[2]
    if normalized[0] in {"openspec-archive-change", "openspec-archive"} and len(tokens) > 1:
        return tokens[1]
    for token in tokens:
        change = change_from_path_token(token)
        if change:
            return change
    return None


def shell_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def moves_change_to_archive(tokens: list[str]) -> bool:
    source = next((token for token in tokens if change_from_path_token(token)), "")
    destination = next((token for token in tokens if "openspec/changes/archive/" in token), "")
    return bool(source and destination)


def removes_change_path(tokens: list[str]) -> bool:
    return any(change_from_path_token(token) for token in tokens if not token.startswith("-"))


def change_from_path_token(token: str) -> str | None:
    normalized = token.strip("'\"")
    match = re.search(r"(?:^|/)openspec/changes/([^/\s]+)", normalized)
    if not match:
        return None
    change = match.group(1)
    if change == "archive":
        return None
    return change
