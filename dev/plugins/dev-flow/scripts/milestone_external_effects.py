#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from workflow_milestone_external_effects import (
    apply_milestone_external_effects,
    canonical_contract_relative_path,
    plan_milestone_external_effects,
    verify_milestone_external_effects,
)
from workflow_milestone_real_boundaries import (
    BoundaryConfigurationError,
    build_real_boundaries,
)


def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for key, value in pairs:
        if key in mapping:
            raise ValueError(f"duplicate JSON key: {key}")
        mapping[key] = value
    return mapping


def read_mapping(path: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            Path(path).expanduser().read_text(),
            object_pairs_hook=reject_duplicate_json_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is missing or invalid JSON: {error}") from error
    except ValueError as error:
        raise ValueError(f"{label} contains ambiguous JSON: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def result_exit_code(report: dict[str, Any]) -> int:
    if report.get("ok"):
        return 0
    if report.get("decision") == "AWAIT_HUMAN":
        return 3
    return 2


def canonical_contract_argument(
    repo: Path, supplied: str, contract: dict[str, Any]
) -> bool:
    relative = canonical_contract_relative_path(contract)
    if relative is None:
        return False
    path = Path(supplied).expanduser()
    expected = repo / relative
    try:
        return bool(
            (
                path.is_absolute()
                and path.absolute() == expected
                or not path.is_absolute()
                and path.as_posix() == relative.as_posix()
            )
            and not path.is_symlink()
            and path.resolve(strict=True) == expected.resolve(strict=True)
            and expected.is_file()
            and not expected.is_symlink()
        )
    except (OSError, ValueError):
        return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Plan, advance, or verify one exact standing Milestone External "
            "Effects Contract."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--repo", default=".")
        subparser.add_argument("--contract", required=True)
        subparser.add_argument("--receipt-dir", required=True)
        subparser.add_argument("--codex-home")
        subparser.add_argument("--json", action="store_true")

    plan = subparsers.add_parser("plan")
    common(plan)
    plan.add_argument("--candidate-manifest", required=True)
    plan.add_argument("--validation-receipt", required=True)
    plan.add_argument("--review-receipt", required=True)
    plan.add_argument("--execution-ledger", required=True)

    advance = subparsers.add_parser("advance")
    common(advance)
    advance.add_argument("--plan", required=True)
    advance.add_argument("--apply", action="store_true")

    verify = subparsers.add_parser("verify")
    common(verify)
    verify.add_argument("--receipt", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo = Path(args.repo).expanduser().resolve()
    # The workflow seam, not the caller's cwd, resolves and verifies this exact
    # repository-relative binding. Absolute or normalized-away paths fail closed.
    receipt_dir = Path(args.receipt_dir)
    try:
        contract = read_mapping(args.contract, "standing contract")
        if not canonical_contract_argument(repo, args.contract, contract):
            report = {
                "ok": False,
                "status": "blocked",
                "decision": "FAIL_CLOSED_REPAIR",
                "reasonCodes": ["CANONICAL_CONTRACT_PATH_REQUIRED"],
                "missingAuthority": [],
            }
            print(json.dumps(report, indent=2, sort_keys=True))
            return result_exit_code(report)
        if args.command == "plan":
            candidate_manifest = read_mapping(
                args.candidate_manifest, "candidate manifest"
            )
            validation_receipt = read_mapping(
                args.validation_receipt, "validation receipt"
            )
            review_receipt = read_mapping(args.review_receipt, "review receipt")
            execution_ledger = read_mapping(args.execution_ledger, "execution ledger")
            boundaries = build_real_boundaries(
                repo,
                contract,
                codex_home=(Path(args.codex_home) if args.codex_home else None),
            )
            report = plan_milestone_external_effects(
                repo,
                contract,
                candidate_manifest=candidate_manifest,
                validation_receipt=validation_receipt,
                review_receipt=review_receipt,
                execution_ledger=execution_ledger,
                receipt_dir=receipt_dir,
                boundaries=boundaries,
            )
        elif args.command == "advance":
            if not args.apply:
                report = {
                    "ok": False,
                    "status": "apply_flag_required",
                    "decision": "FAIL_CLOSED_REPAIR",
                    "reasonCodes": ["EXPLICIT_EXECUTION_SAFEGUARD_REQUIRED"],
                    "missingAuthority": [],
                }
            else:
                plan = read_mapping(args.plan, "milestone plan")
                boundaries = build_real_boundaries(
                    repo,
                    contract,
                    codex_home=(Path(args.codex_home) if args.codex_home else None),
                )
                report = apply_milestone_external_effects(
                    repo,
                    contract,
                    plan=plan,
                    receipt_dir=receipt_dir,
                    boundaries=boundaries,
                )
        else:
            receipt = read_mapping(args.receipt, "terminal receipt")
            boundaries = build_real_boundaries(
                repo,
                contract,
                codex_home=(Path(args.codex_home) if args.codex_home else None),
            )
            report = verify_milestone_external_effects(
                repo,
                contract,
                receipt=receipt,
                receipt_dir=receipt_dir,
                boundaries=boundaries,
            )
    except (ValueError, BoundaryConfigurationError, OSError) as error:
        report = {
            "ok": False,
            "status": "blocked",
            "decision": "FAIL_CLOSED_REPAIR",
            "reasonCodes": ["MILESTONE_INPUT_OR_BOUNDARY_INVALID"],
            "missingAuthority": [],
            "error": str(error),
        }
    print(json.dumps(report, indent=2, sort_keys=True))
    return result_exit_code(report)


if __name__ == "__main__":
    raise SystemExit(main())
