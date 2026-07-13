from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from workflow_routing_matrix import full_openspec_kinds, load_routing_matrix, low_risk_kinds


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

METHODOLOGY_PROFILES = {"core", "lean-matt", "strict-superpowers"}
ROADMAP_PROVIDERS = {"none", "gsd"}
METHODOLOGY_KEYS = ("methodology_profile", "methodologyProfile")
ROADMAP_KEYS = ("roadmap_provider", "roadmapProvider")
PROVIDER_SELECTOR_KEYS = ("provider_selectors", "providerSelectors")
ROADMAP_BINDING_KEYS = ("roadmap_bindings", "roadmapBindings")


def validate_devflow_config(raw: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    workflow_value = raw.get("workflow")
    if "workflow" in raw and not isinstance(workflow_value, dict):
        errors.append("workflow must be a JSON object")
    workflow = workflow_value if isinstance(workflow_value, dict) else {}
    for mapping, scope in ((workflow, "workflow"), (raw, "root")):
        validate_enum_fields(
            mapping,
            scope,
            METHODOLOGY_KEYS,
            METHODOLOGY_PROFILES,
            "methodology profile",
            errors,
        )
        validate_enum_fields(
            mapping,
            scope,
            ROADMAP_KEYS,
            ROADMAP_PROVIDERS,
            "roadmap provider",
            errors,
        )
        validate_mapping_fields(mapping, scope, PROVIDER_SELECTOR_KEYS, "provider selectors", errors)
        validate_mapping_fields(mapping, scope, ROADMAP_BINDING_KEYS, "roadmap bindings", errors)
    return errors


def validate_enum_fields(
    mapping: dict[str, Any],
    scope: str,
    keys: tuple[str, ...],
    allowed: set[str],
    label: str,
    errors: list[str],
) -> None:
    for key in keys:
        if key not in mapping:
            continue
        value = mapping[key]
        if not isinstance(value, str) or value.strip() not in allowed:
            errors.append(
                f"{scope}.{key} ({label}) must be one of: {', '.join(sorted(allowed))}"
            )


def validate_mapping_fields(
    mapping: dict[str, Any],
    scope: str,
    keys: tuple[str, ...],
    label: str,
    errors: list[str],
) -> None:
    for key in keys:
        if key in mapping and not isinstance(mapping[key], dict):
            errors.append(f"{scope}.{key} ({label}) must be a JSON object")


def read_workflow_mode_config(repo: Path) -> dict[str, Any]:
    config_path = repo / ".dev-flow.json"
    raw: dict[str, Any] = {}
    errors: list[str] = []
    if config_path.exists():
        try:
            loaded = json.loads(config_path.read_text())
            if isinstance(loaded, dict):
                raw = loaded
                errors.extend(validate_devflow_config(raw))
            else:
                errors.append(".dev-flow.json must contain a JSON object")
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"invalid .dev-flow.json: {error}")
    workflow = raw.get("workflow") if isinstance(raw.get("workflow"), dict) else {}
    return {
        "source": str(config_path) if config_path.exists() else "default",
        "valid": not errors,
        "config_errors": errors,
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
        "methodology_profile": provider_value(
            workflow,
            raw,
            "methodology_profile",
            "methodologyProfile",
            default="core",
        ),
        "roadmap_provider": provider_value(
            workflow,
            raw,
            "roadmap_provider",
            "roadmapProvider",
            default="none",
        ),
        "provider_selectors": provider_mapping(
            workflow,
            raw,
            "provider_selectors",
            "providerSelectors",
        ),
        "roadmap_bindings": provider_mapping(
            workflow,
            raw,
            "roadmap_bindings",
            "roadmapBindings",
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


def provider_value(
    workflow: dict[str, Any],
    raw: dict[str, Any],
    *keys: str,
    default: str,
) -> str:
    for mapping in (workflow, raw):
        for key in keys:
            value = mapping.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return default


def provider_mapping(
    workflow: dict[str, Any],
    raw: dict[str, Any],
    *keys: str,
) -> dict[str, Any]:
    for mapping in (workflow, raw):
        for key in keys:
            value = mapping.get(key)
            if isinstance(value, dict):
                return dict(value)
    return {}


def route_workflow_mode(
    repo: Path,
    *,
    kind: str | None = None,
    request: str = "",
    openspec_ready: bool = False,
) -> dict[str, Any]:
    config = read_workflow_mode_config(repo)
    matrix = load_routing_matrix()
    normalized_kind = (kind or "unspecified").strip().lower()
    request_text = request.strip()
    lowered = request_text.lower()
    high_risk = is_high_risk(normalized_kind, lowered)
    prototype_requested = is_explicit_prototype(normalized_kind, lowered)
    low_risk = is_low_risk(normalized_kind, lowered)

    if not config["valid"]:
        return {
            "route_id": "invalid-workflow-config",
            "routing_matrix": matrix["sourcePath"],
            "mode": "blocked",
            "label": "Invalid DevFlow configuration",
            "reason": "Workflow routing cannot safely default across a malformed configuration.",
            "request_kind": normalized_kind,
            "config": config,
            "execution_allowed": False,
            "production_allowed": False,
            "failed_gates": ["workflow_config_valid"],
            "blocker": "; ".join(config["config_errors"]),
            "next_action": "Repair .dev-flow.json and rerun workflow routing.",
            "recommended_skill": "workflow-doctor",
            "recommended_command": "python3 scripts/validate_workflow_state.py --repo . --json",
        }

    if high_risk:
        failed_gates = [] if openspec_ready else ["mandatory_full_openspec", "openspec_artifacts_ready"]
        return {
            "route_id": "mandatory-full-openspec",
            "routing_matrix": matrix["sourcePath"],
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
            "route_id": "prototype-explicit-only",
            "routing_matrix": matrix["sourcePath"],
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
            "route_id": "lightweight-ledger-low-risk",
            "routing_matrix": matrix["sourcePath"],
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
        "route_id": "default-full-openspec",
        "routing_matrix": matrix["sourcePath"],
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
    if kind in full_openspec_kinds() or kind in FULL_OPENSPEC_KINDS:
        return True
    return any(term in request_text for term in HIGH_RISK_TERMS)


def is_low_risk(kind: str, request_text: str) -> bool:
    if kind in low_risk_kinds() or kind in LOW_RISK_KINDS:
        return not is_high_risk(kind, request_text)
    return False


def is_explicit_prototype(kind: str, request_text: str) -> bool:
    return kind in {"prototype", "spike", "proof-of-concept"} or any(
        term in request_text for term in PROTOTYPE_TERMS
    )
