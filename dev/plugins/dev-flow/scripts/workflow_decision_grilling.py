#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


TRIGGER_TERMS = (
    "open question",
    "unclear",
    "ambiguous",
    "tradeoff",
    "compatibility",
    "integration",
    "acceptance criteria",
    "implementation shape",
    "grill",
    "stress-test",
)


def default_plugin_root() -> Path:
    env_root = os.environ.get("DEVFLOW_PLUGIN_ROOT")
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parents[1]


def decision_grilling_matrix_path(plugin_root: Path | None = None) -> Path:
    root = plugin_root or default_plugin_root()
    return root / "docs" / "decision_grilling_matrix.json"


def load_decision_grilling_matrix(plugin_root: Path | None = None) -> dict[str, Any]:
    path = decision_grilling_matrix_path(plugin_root)
    data = json.loads(path.read_text())
    data["sourcePath"] = str(path)
    return data


def decision_grilling_guidance(
    *,
    kind: str | None = None,
    request: str = "",
    open_questions: list[str] | None = None,
    locally_answerable: bool = False,
    plugin_root: Path | None = None,
) -> dict[str, Any]:
    matrix = load_decision_grilling_matrix(plugin_root)
    normalized_kind = (kind or "unspecified").strip().lower()
    questions = [question.strip() for question in (open_questions or []) if question.strip()]
    request_text = request.strip()
    lowered = request_text.lower()
    skipped_kind = normalized_kind in set(matrix.get("skipKinds", []))
    local_evidence_first = True

    if skipped_kind and not questions:
        return {
            "status": "skipped",
            "gate_id": matrix["gateId"],
            "method_gate": matrix["methodGate"],
            "reason": f"{normalized_kind} has no unresolved design decisions",
            "ledger_entry": "decision-grilling: skipped - no unresolved design decisions.",
            "local_evidence_first": local_evidence_first,
            "next_action": "continue-approved-work",
            "protocol": matrix["protocol"],
            "protocol_summary": protocol_summary(matrix),
            "canonical_artifacts": matrix["canonicalArtifacts"],
            "sourcePath": matrix["sourcePath"],
        }

    if questions or any(term in lowered for term in TRIGGER_TERMS):
        reason = "Open Questions remain" if questions else "request contains ambiguity or grilling trigger"
        next_action = "inspect-local-evidence-before-asking" if locally_answerable else "ask-one-question-at-a-time"
        return {
            "status": "required",
            "gate_id": matrix["gateId"],
            "method_gate": matrix["methodGate"],
            "reason": reason,
            "ledger_entry": f"decision-grilling: required - {reason}.",
            "local_evidence_first": local_evidence_first,
            "next_action": next_action,
            "open_questions": questions,
            "protocol": matrix["protocol"],
            "protocol_summary": protocol_summary(matrix),
            "canonical_artifacts": matrix["canonicalArtifacts"],
            "sourcePath": matrix["sourcePath"],
        }

    return {
        "status": "skipped",
        "gate_id": matrix["gateId"],
        "method_gate": matrix["methodGate"],
        "reason": "no unresolved plan or design ambiguity detected",
        "ledger_entry": "decision-grilling: skipped - no unresolved plan or design ambiguity.",
        "local_evidence_first": local_evidence_first,
        "next_action": "continue-normal-routing",
        "protocol": matrix["protocol"],
        "protocol_summary": protocol_summary(matrix),
        "canonical_artifacts": matrix["canonicalArtifacts"],
        "sourcePath": matrix["sourcePath"],
    }


def protocol_summary(matrix: dict[str, Any]) -> str:
    return (
        "inspect local evidence first; ask one question at a time; provide a "
        "recommended answer; walk dependent decision branches; record resolved "
        "decisions in canonical artifacts"
    )


def render_text(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Decision grilling: {payload['status']}",
            f"Reason: {payload['reason']}",
            f"Ledger: {payload['ledger_entry']}",
            f"Next action: {payload['next_action']}",
            f"Protocol: {payload['protocol_summary']}",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Route DevFlow decision grilling guidance.")
    parser.add_argument("--kind", default="unspecified")
    parser.add_argument("--request", default="")
    parser.add_argument("--open-question", action="append", dest="open_questions", default=[])
    parser.add_argument("--locally-answerable", action="store_true")
    parser.add_argument("--plugin-root")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    plugin_root = Path(args.plugin_root).resolve() if args.plugin_root else None
    payload = decision_grilling_guidance(
        kind=args.kind,
        request=args.request,
        open_questions=args.open_questions,
        locally_answerable=args.locally_answerable,
        plugin_root=plugin_root,
    )
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_text(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
