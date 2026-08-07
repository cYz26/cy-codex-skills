#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from workflow_implementation_readiness import (
    ReadinessError,
    active_context_from_repo,
    inspect_repository_readiness,
    load_canonical_requirement,
    plan_provider_override,
    plan_ready_receipt,
    plan_requirement_promotion,
    promote_requirement,
    record_provider_override,
    repository_mutation_gate,
    write_ready_receipt,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect or explicitly record project-directed implementation readiness."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Read and evaluate canonical readiness inputs.")
    add_common(inspect_parser)

    mutation_parser = subparsers.add_parser(
        "check-mutation",
        help="Check the current Ready Receipt together with caller-confirmed ordinary authority.",
    )
    add_common(mutation_parser)
    mutation_parser.add_argument("--ordinary-authority", action="store_true")

    promote_parser = subparsers.add_parser(
        "promote",
        help="Validate an explicit Requirement candidate and optionally promote it without provider selection.",
    )
    add_common(promote_parser)
    promote_parser.add_argument("--requirement", required=True)
    promote_parser.add_argument("--apply", action="store_true")

    receipt_parser = subparsers.add_parser(
        "write-receipt",
        help="Plan or write a content-bound receipt for a current Ready evaluation.",
    )
    add_common(receipt_parser)
    receipt_parser.add_argument("--recorded-at", required=True)
    receipt_parser.add_argument("--apply", action="store_true")

    override_parser = subparsers.add_parser(
        "record-override",
        help="Validate and optionally record an explicit named-human provider override.",
    )
    add_common(override_parser)
    override_parser.add_argument("--override", required=True)
    override_parser.add_argument("--apply", action="store_true")

    args = parser.parse_args()
    try:
        report = run(args)
    except (ReadinessError, OSError, UnicodeError, json.JSONDecodeError) as error:
        payload = {
            "ok": False,
            "status": "blocked",
            "error": getattr(error, "code", error.__class__.__name__),
            "message": str(error),
        }
        emit(payload, json_output=args.json)
        return 1
    emit(report, json_output=args.json)
    if args.command == "check-mutation" and not report.get("allowed"):
        return 2
    return 0


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", default=".")
    parser.add_argument("--change-id", required=True)
    parser.add_argument("--evaluated-at")
    parser.add_argument("--json", action="store_true")


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo = Path(args.repo).expanduser().resolve()
    if args.command == "inspect":
        return inspect_repository_readiness(repo, args.change_id, evaluated_at=args.evaluated_at)

    if args.command == "check-mutation":
        return repository_mutation_gate(
            repo,
            ordinary_authority=bool(args.ordinary_authority),
            change_id=args.change_id,
            evaluated_at=args.evaluated_at,
        )

    if args.command == "promote":
        requirement = read_document(Path(args.requirement))
        context = active_context_from_repo(
            repo,
            args.change_id,
            project_id=str(requirement.get("consumer", {}).get("projectId") or ""),
            target_profile=requirement.get("targetProfile", {}),
            evaluated_at=args.evaluated_at,
        )
        if args.apply:
            return promote_requirement(repo, args.change_id, requirement, context)
        return plan_requirement_promotion(repo, args.change_id, requirement, context)

    inspection = inspect_repository_readiness(repo, args.change_id, evaluated_at=args.evaluated_at)
    requirement = load_canonical_requirement(repo, args.change_id)
    context = active_context_from_repo(
        repo,
        args.change_id,
        project_id=str(requirement.get("consumer", {}).get("projectId") or ""),
        target_profile=requirement.get("targetProfile", {}),
        evaluated_at=args.evaluated_at,
    )
    if args.command == "write-receipt":
        report = inspection.get("report")
        if not isinstance(report, dict):
            raise ReadinessError("readiness_not_applicable", "No active readiness contract exists")
        if args.apply:
            return write_ready_receipt(
                repo,
                args.change_id,
                report,
                recorded_at=args.recorded_at,
            )
        return plan_ready_receipt(
            repo,
            args.change_id,
            report,
            recorded_at=args.recorded_at,
        )
    if args.command == "record-override":
        override = read_document(Path(args.override))
        if args.apply:
            return record_provider_override(repo, args.change_id, override, context)
        return plan_provider_override(repo, args.change_id, override, context)
    raise ReadinessError("unsupported_command", "Unsupported readiness command")


def read_document(path: Path) -> dict[str, Any]:
    candidate = path.expanduser().absolute()
    if candidate.is_symlink() or not candidate.is_file():
        raise ReadinessError("document_untrusted", "Readiness input must be a regular non-symlink file", path=candidate)
    value = json.loads(candidate.read_text())
    if not isinstance(value, dict):
        raise ReadinessError("document_invalid", "Readiness input must be a JSON object", path=candidate)
    return value


def emit(report: dict[str, Any], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        nested = report.get("report")
        state = nested.get("state", "ok") if isinstance(nested, dict) else "ok"
        print(f"{report.get('status', state)}: {report.get('path', '')}".strip())


if __name__ == "__main__":
    raise SystemExit(main())
