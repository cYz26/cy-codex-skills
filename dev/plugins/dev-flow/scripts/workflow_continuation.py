from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

from workflow_paths import rel, repo_path
from workflow_implementation_readiness import repository_mutation_gate
from workflow_state import parse_state


CONTINUE_NEXT_ITEM = "CONTINUE_NEXT_ITEM"
CHECKPOINT_AND_CONTINUE = "CHECKPOINT_AND_CONTINUE"
VERIFY_ACTIVE_CHANGE = "VERIFY_ACTIVE_CHANGE"
AWAIT_HUMAN = "AWAIT_HUMAN"
READY_FOR_EXTERNAL_EFFECT = "READY_FOR_EXTERNAL_EFFECT"
COMPLETE = "COMPLETE"

AUTOMATIC_CONTINUATION_ACTIONS = frozenset(
    {CONTINUE_NEXT_ITEM, CHECKPOINT_AND_CONTINUE, VERIFY_ACTIVE_CHANGE}
)
VALID_STOP_ACTIONS = frozenset({AWAIT_HUMAN, READY_FOR_EXTERNAL_EFFECT, COMPLETE})
HUMAN_GATE_STATE = "awaiting_human"
EXTERNAL_EFFECT_STATUSES = frozenset({"pending", "authorization_required"})

INCOMPLETE_LEDGER_STATUSES = frozenset(
    {"todo", "in_progress", "planned", "executing", "review", "blocked"}
)
COMPLETE_LEDGER_STATUSES = frozenset({"done", "skipped_with_reason"})
MALFORMED_LEDGER_STATUS = "__malformed__"
MARKDOWN_TABLE_SEPARATOR = re.compile(r"^:?-{3,}:?$")
SAFE_CHANGE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
VALID_TASK_CHECKBOX = re.compile(r"^\s*[-+*]\s+\[([ xX])\]\s+\S.*$")
POSSIBLE_TASK_CHECKBOX = re.compile(r"^\s*[-+*]\s+\[[^]]*\]")
FENCE_START = re.compile(r"^\s*(`{3,}|~{3,})")


def decide_continuation(
    *,
    source_valid: bool,
    work_remaining: bool,
    checkpoint_recommended: bool,
    verification_passed: bool,
    human_gate: bool,
    external_effect_ready: bool,
) -> dict[str, Any]:
    """Return one deterministic continuation outcome from explicit signals."""
    if human_gate:
        return decision(
            AWAIT_HUMAN,
            "an explicit Human Gate is recorded",
            "Present the one concrete question and wait for the human decision.",
        )
    if not source_valid:
        return decision(
            AWAIT_HUMAN,
            "the canonical execution source is invalid or ambiguous",
            "Report the source issue and obtain or record a canonical repair decision.",
        )
    if work_remaining and checkpoint_recommended:
        return decision(
            CHECKPOINT_AND_CONTINUE,
            "approved work remains and a durable checkpoint is recommended",
            "Write and validate the checkpoint, then continue with the next approved item.",
        )
    if work_remaining:
        return decision(
            CONTINUE_NEXT_ITEM,
            "approved executable work remains",
            "Return to project-orchestrator and execute the next dependency-ready item.",
        )
    if not verification_passed:
        return decision(
            VERIFY_ACTIVE_CHANGE,
            "the active execution source is closed but current verification is missing",
            "Run current-change review and verification before any completion claim.",
        )
    if external_effect_ready:
        return decision(
            READY_FOR_EXTERNAL_EFFECT,
            "verified work reached a separately authorized external-effect boundary",
            "Present the exact external effect and request its existing explicit authorization.",
        )
    return decision(
        COMPLETE,
        "the active execution source is closed and required verification is current",
        "Prepare the overall completion claim with fresh evidence and residual risks.",
    )


def decision(action: str, reason: str, next_action: str) -> dict[str, Any]:
    return {
        "action": action,
        "reason": reason,
        "nextAction": next_action,
        "continuationRequired": action in AUTOMATIC_CONTINUATION_ACTIONS,
        "stopAllowed": action in VALID_STOP_ACTIONS,
    }


def generated_artifact_orchestration(
    repo: Path,
    contract: dict[str, Any],
    manifest: dict[str, Any],
    proposed_plan: dict[str, Any] | None,
) -> dict[str, Any]:
    from workflow_generated_artifacts import (
        AUTO_CLEAN,
        HUMAN_GATE,
        RETAIN,
        WAIT_OWNER,
        plan_cleanup,
    )

    fresh_plan = plan_cleanup(repo, contract, manifest)
    if proposed_plan is not None and proposed_plan != fresh_plan:
        return {
            "decision": HUMAN_GATE,
            "action": AWAIT_HUMAN,
            "applyAllowed": False,
            "requiresExplicitApply": True,
            "receiptRequired": False,
            "reasons": ["stale_or_self_authored_plan"],
            "plan": fresh_plan,
        }

    artifact_decision = fresh_plan["decision"]
    routes = {
        AUTO_CLEAN: ("APPLY_GENERATED_ARTIFACT_CLEANUP", True, True),
        WAIT_OWNER: ("WAIT_OWNER", False, False),
        RETAIN: ("RECORD_RETENTION", False, False),
        HUMAN_GATE: (AWAIT_HUMAN, False, False),
    }
    action, apply_allowed, receipt_required = routes[artifact_decision]
    return {
        "decision": artifact_decision,
        "action": action,
        "applyAllowed": apply_allowed,
        "requiresExplicitApply": True,
        "receiptRequired": receipt_required,
        "reasons": list(fresh_plan["reasons"]),
        "plan": fresh_plan,
    }


def continuation_decision(
    repo: Path,
    *,
    state: Optional[dict[str, Any]] = None,
    release_status: Optional[str] = None,
) -> dict[str, Any]:
    repo = repo_path(repo)
    current_state = state if state is not None else parse_state(repo)
    source = execution_source(repo, state=current_state)
    has_source = source["kind"] != "none"
    recorded_verification = bool(current_state.get("gates", {}).get("verification_passed"))
    effective_verification = recorded_verification if has_source else True
    context = current_state.get("context_management", {})
    checkpoint_recommended = bool(context.get("compact_recommended")) or context.get(
        "compact_status"
    ) == "pending"
    external_effect_ready = recorded_verification and str(release_status or "") in EXTERNAL_EFFECT_STATUSES
    result = decide_continuation(
        source_valid=bool(source["valid"]),
        work_remaining=bool(source["incomplete"]),
        checkpoint_recommended=checkpoint_recommended,
        verification_passed=effective_verification,
        human_gate=is_explicit_human_gate(current_state),
        external_effect_ready=external_effect_ready,
    )
    readiness = repository_mutation_gate(repo, ordinary_authority=True)
    if (
        result["action"] in AUTOMATIC_CONTINUATION_ACTIONS
        and readiness["applicable"]
        and not readiness["allowed"]
    ):
        result = decision(
            CHECKPOINT_AND_CONTINUE,
            "implementation readiness blocks governed execution but its Human Gate is not yet durably recorded",
            (
                "Record the exact readiness issue and next action, set both current_stage and "
                "current_change.status to awaiting_human, then re-run continuation before stopping. "
                f"Required remediation: {readiness['nextAction']}"
            ),
        )
    return {
        **result,
        "executionSource": source,
        "implementationReadiness": readiness,
    }


def is_explicit_human_gate(state: dict[str, Any]) -> bool:
    change = state.get("current_change", {})
    status = change.get("status") if isinstance(change, dict) else None
    return (
        normalize_token(state.get("current_stage")) == HUMAN_GATE_STATE
        and normalize_token(status) == HUMAN_GATE_STATE
    )


def normalize_token(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def execution_source(repo: Path, state: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    repo = repo_path(repo)
    current_state = state if state is not None else parse_state(repo)
    change = current_state.get("current_change", {})
    change_id = str(change.get("id") or "none") if isinstance(change, dict) else "none"
    if change_id not in {"", "none"}:
        if not SAFE_CHANGE_ID.fullmatch(change_id):
            return source_report(
                "openspec",
                f"openspec/changes/{change_id}/tasks.md",
                valid=False,
                issues=["active OpenSpec change id is unsafe or malformed"],
            )
        tasks = repo / "openspec" / "changes" / change_id / "tasks.md"
        if not trusted_regular_file(repo, tasks):
            return source_report(
                "openspec",
                rel(repo, tasks),
                valid=False,
                issues=["active OpenSpec tasks file is missing or untrusted"],
            )
        try:
            return openspec_execution_source(repo, tasks, tasks.read_text())
        except (OSError, UnicodeError):
            return source_report(
                "openspec",
                rel(repo, tasks),
                valid=False,
                issues=["active OpenSpec tasks file is unreadable"],
            )

    ledger = repo / "TASK_LEDGER.md"
    if not ledger.exists():
        return source_report("none", "none", valid=True)
    if not trusted_regular_file(repo, ledger):
        return source_report(
            "task_ledger",
            "TASK_LEDGER.md",
            valid=False,
            issues=["fallback task ledger is untrusted"],
        )
    try:
        return ledger_execution_source(repo, ledger, ledger.read_text())
    except (OSError, UnicodeError):
        return source_report(
            "task_ledger",
            "TASK_LEDGER.md",
            valid=False,
            issues=["fallback task ledger is unreadable"],
        )


def trusted_regular_file(repo: Path, path: Path) -> bool:
    try:
        relative = path.absolute().relative_to(repo.resolve())
    except ValueError:
        return False
    current = repo.resolve()
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return False
    return current.is_file()


def openspec_execution_source(repo: Path, path: Path, text: str) -> dict[str, Any]:
    total = 0
    incomplete = 0
    issues: list[str] = []
    fence: Optional[str] = None
    for line_number, line in enumerate(text.splitlines(), start=1):
        marker = FENCE_START.match(line)
        if marker:
            token = marker.group(1)
            kind = token[0]
            if fence is None:
                fence = kind
            elif fence == kind:
                fence = None
            continue
        if fence is not None:
            continue
        checkbox = VALID_TASK_CHECKBOX.match(line)
        if checkbox:
            total += 1
            if checkbox.group(1) == " ":
                incomplete += 1
            continue
        if POSSIBLE_TASK_CHECKBOX.match(line):
            issues.append(f"malformed task checkbox at line {line_number}")
    if fence is not None:
        issues.append("unterminated fenced block in active OpenSpec tasks")
    if total == 0:
        issues.append("active OpenSpec tasks contain no valid task checkboxes")
    return source_report(
        "openspec",
        rel(repo, path),
        valid=not issues,
        total=total,
        incomplete=incomplete,
        issues=issues,
    )


def ledger_execution_source(repo: Path, path: Path, text: str) -> dict[str, Any]:
    statuses = markdown_table_column_values(text, "status")
    unknown = sorted(
        {
            status
            for status in statuses
            if status not in INCOMPLETE_LEDGER_STATUSES and status not in COMPLETE_LEDGER_STATUSES
        }
    )
    issues: list[str] = []
    if not statuses:
        issues.append("fallback task ledger contains no task statuses")
    if unknown:
        issues.append(f"fallback task ledger has invalid task statuses: {', '.join(unknown)}")
    incomplete = sum(status in INCOMPLETE_LEDGER_STATUSES for status in statuses)
    return source_report(
        "task_ledger",
        rel(repo, path),
        valid=not issues,
        total=len(statuses),
        incomplete=incomplete,
        issues=issues,
        invalid_statuses=unknown,
    )


def source_report(
    kind: str,
    path: str,
    *,
    valid: bool,
    total: int = 0,
    incomplete: int = 0,
    issues: Optional[list[str]] = None,
    invalid_statuses: Optional[list[str]] = None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "path": path,
        "valid": valid,
        "total": total,
        "incomplete": incomplete,
        "complete": total - incomplete,
        "issues": list(issues or []),
        "invalidStatuses": list(invalid_statuses or []),
    }


def markdown_table_column_values(text: str, column_name: str) -> list[str]:
    """Return normalized values from a named column in Markdown tables only."""
    lines = text.splitlines()
    values: list[str] = []
    index = 0
    wanted = column_name.strip().lower()
    while index + 1 < len(lines):
        header = markdown_table_cells(lines[index])
        separator = markdown_table_cells(lines[index + 1])
        if (
            wanted not in header
            or len(separator) != len(header)
            or not all(MARKDOWN_TABLE_SEPARATOR.fullmatch(cell) for cell in separator)
        ):
            index += 1
            continue

        column_index = header.index(wanted)
        index += 2
        while index < len(lines):
            row = markdown_table_cells(lines[index])
            if not row:
                break
            if len(row) != len(header):
                values.append(MALFORMED_LEDGER_STATUS)
                break
            values.append(row[column_index])
            index += 1
    return values


def markdown_table_cells(line: str) -> list[str]:
    stripped = line.strip()
    if "|" not in stripped:
        return []
    cells: list[str] = []
    current: list[str] = []
    index = 0
    while index < len(stripped):
        character = stripped[index]
        if character == "\\" and index + 1 < len(stripped) and stripped[index + 1] == "|":
            current.append("|")
            index += 2
            continue
        if character == "|":
            cells.append("".join(current))
            current = []
        else:
            current.append(character)
        index += 1
    cells.append("".join(current))
    if stripped.startswith("|"):
        cells = cells[1:]
    if stripped.endswith("|"):
        cells = cells[:-1]
    return [cell.strip().lower() for cell in cells]
