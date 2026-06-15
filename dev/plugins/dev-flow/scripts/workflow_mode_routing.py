from __future__ import annotations

import json
from pathlib import Path
from typing import Any


FULL_OPENSPEC_KINDS = {
    "new-feature",
    "behavior-change",
    "api-change",
    "data-model-change",
    "migration",
    "integration",
    "permission-change",
    "error-handling-change",
    "compatibility-change",
}

LOW_RISK_KINDS = {
    "docs-only",
    "test-only",
    "internal-maintenance",
    "low-risk-bugfix",
    "tooling",
    "refactor",
    "workflow-repair",
}

HIGH_RISK_TERMS = (
    "user-visible",
    "public api",
    "api",
    "data model",
    "schema",
    "persistence",
    "migration",
    "integration",
    "permission",
    "auth",
    "error handling",
    "compatibility",
    "behavior",
)

PROTOTYPE_TERMS = (
    "prototype",
    "proof of concept",
    "poc",
    "spike",
    "demo",
)

LEDGER_SECTIONS = [
    "Target State",
    "Scope / Non-Goals",
    "Validation Commands",
    "Execution Log",
    "Completion Claim",
]


def read_workflow_mode_config(repo: Path) -> dict[str, Any]:
    config_path = repo / ".dev-flow.json"
    raw: dict[str, Any] = {}
    if config_path.exists():
        try:
            loaded = json.loads(config_path.read_text())
            if isinstance(loaded, dict):
                raw = loaded
        except json.JSONDecodeError:
            raw = {}
    workflow = raw.get("workflow") if isinstance(raw.get("workflow"), dict) else {}
    return {
        "source": str(config_path) if config_path.exists() else "default",
        "default_mode": str(
            workflow.get("mode")
            or raw.get("workflow_mode")
            or raw.get("workflowMode")
            or "full-openspec"
        ),
        "lightweight_ledger_enabled": config_enabled(
            workflow,
            "lightweight_ledger",
            "lightweightLedger",
            "lightweight",
            "enable_lightweight_ledger",
        ),
        "prototype_mode_enabled": config_enabled(
            workflow,
            "prototype",
            "prototype_mode",
            "prototypeMode",
            "enable_prototype_mode",
            default=True,
        ),
    }


def config_enabled(config: dict[str, Any], *keys: str, default: bool = False) -> bool:
    for key in keys:
        if key not in config:
            continue
        value = config[key]
        if isinstance(value, dict):
            return bool(value.get("enabled", default))
        if isinstance(value, bool):
            return value
    return default


def route_workflow_mode(
    repo: Path,
    *,
    kind: str | None = None,
    request: str = "",
    openspec_ready: bool = False,
) -> dict[str, Any]:
    config = read_workflow_mode_config(repo)
    normalized_kind = (kind or "unspecified").strip().lower()
    request_text = request.strip()
    lowered = request_text.lower()
    high_risk = is_high_risk(normalized_kind, lowered)
    prototype_requested = is_explicit_prototype(normalized_kind, lowered)
    low_risk = is_low_risk(normalized_kind, lowered)

    if high_risk:
        failed_gates = [] if openspec_ready else ["mandatory_full_openspec", "openspec_artifacts_ready"]
        return {
            "mode": "full-openspec",
            "label": "Full OpenSpec",
            "reason": "High-risk work requires canonical OpenSpec artifacts.",
            "request_kind": normalized_kind,
            "config": config,
            "execution_allowed": bool(openspec_ready),
            "production_allowed": bool(openspec_ready),
            "failed_gates": failed_gates,
            "blocker": (
                ""
                if openspec_ready
                else "Full OpenSpec requires proposal, design, specs, and tasks before execution."
            ),
            "next_action": (
                "Use openspec-apply-change after proposal, design, specs, and tasks are ready."
                if openspec_ready
                else "Use openspec-propose to create proposal, design, specs, and tasks."
            ),
            "recommended_skill": "openspec-apply-change" if openspec_ready else "openspec-propose",
            "recommended_command": "openspec status --change <change-id> --json",
        }

    if prototype_requested and config["prototype_mode_enabled"]:
        return {
            "mode": "prototype-mode",
            "label": "Prototype Mode",
            "reason": "The user explicitly requested non-production prototype work.",
            "request_kind": normalized_kind,
            "config": config,
            "execution_allowed": True,
            "production_allowed": False,
            "failed_gates": [],
            "status": "non-production",
            "next_action": "Record cleanup or promotion criteria before using prototype output.",
            "recommended_skill": "feature-intake",
            "recommended_command": "",
            "promotion_criteria": [
                "Define production target state.",
                "Promote through Full OpenSpec before production behavior changes.",
                "Remove or isolate throwaway prototype code.",
            ],
        }

    if config["lightweight_ledger_enabled"] and low_risk:
        return {
            "mode": "lightweight-ledger",
            "label": "Lightweight Ledger",
            "reason": "Configured lightweight mode is allowed for low-risk work.",
            "request_kind": normalized_kind,
            "config": config,
            "execution_allowed": True,
            "production_allowed": True,
            "failed_gates": [],
            "ledger_sections": LEDGER_SECTIONS,
            "verification_required": True,
            "completion_requires_evidence": True,
            "next_action": "Create or update a lightweight ledger with validation evidence.",
            "recommended_skill": "execute-task",
            "recommended_command": "",
        }

    return {
        "mode": "full-openspec",
        "label": "Full OpenSpec",
        "reason": "Default route is Full OpenSpec unless low-risk lightweight routing is configured.",
        "request_kind": normalized_kind,
        "config": config,
        "execution_allowed": bool(openspec_ready),
        "production_allowed": bool(openspec_ready),
        "failed_gates": [] if openspec_ready else ["openspec_artifacts_ready"],
        "blocker": "" if openspec_ready else "Full OpenSpec artifacts must be ready before execution.",
        "next_action": (
            "Use openspec-apply-change for the approved task."
            if openspec_ready
            else "Use feature-intake, then openspec-propose if behavior-level work is confirmed."
        ),
        "recommended_skill": "openspec-apply-change" if openspec_ready else "feature-intake",
        "recommended_command": "openspec status --change <change-id> --json",
    }


def is_high_risk(kind: str, request_text: str) -> bool:
    if kind in FULL_OPENSPEC_KINDS:
        return True
    return any(term in request_text for term in HIGH_RISK_TERMS)


def is_low_risk(kind: str, request_text: str) -> bool:
    if kind in LOW_RISK_KINDS:
        return not is_high_risk(kind, request_text)
    return False


def is_explicit_prototype(kind: str, request_text: str) -> bool:
    return kind in {"prototype", "spike", "proof-of-concept"} or any(
        term in request_text for term in PROTOTYPE_TERMS
    )
