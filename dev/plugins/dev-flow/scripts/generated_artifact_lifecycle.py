#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from workflow_generated_artifacts import (
    GeneratedArtifactError,
    apply_cleanup,
    canonical_document_bytes,
    load_immutable_document,
    observe_artifacts,
    plan_cleanup,
    prepare_contract,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generated Artifact Lifecycle: read-only prepare, observe, and plan; "
            "persist prepare output before the bound command; cleanup mutates "
            "only with --apply."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser(
        "prepare",
        help="Emit the canonical pre-creation contract for caller persistence.",
    )
    add_repo_argument(prepare)
    prepare.add_argument("--task-id", required=True)
    prepare.add_argument("--run-id", required=True)
    prepare.add_argument("--owner-id", required=True)
    prepare.add_argument("--owner-pid", type=int, required=True)
    prepare.add_argument("--command-json", required=True)
    prepare.add_argument("--isolated-root", action="append", default=[])
    prepare.add_argument("--adjacent-output", action="append", default=[])
    prepare.add_argument(
        "--retention",
        choices=("cleanup", "retain", "promote"),
        default="cleanup",
    )
    prepare.add_argument("--contract-id")
    prepare.add_argument("--lease-path")

    observe = subparsers.add_parser(
        "observe",
        help="Read-only post-command observation.",
    )
    add_repo_argument(observe)
    observe.add_argument("--contract", required=True)
    observe.add_argument("--exit-code", type=int, required=True)

    plan = subparsers.add_parser(
        "plan",
        help="Read-only deterministic cleanup classification.",
    )
    add_repo_argument(plan)
    plan.add_argument("--contract", required=True)
    plan.add_argument("--manifest", required=True)

    cleanup = subparsers.add_parser(
        "cleanup",
        help="Exact cleanup; --apply is mandatory for mutation.",
    )
    add_repo_argument(cleanup)
    cleanup.add_argument("--contract", required=True)
    cleanup.add_argument("--manifest", required=True)
    cleanup.add_argument("--plan", required=True)
    cleanup.add_argument("--receipt")
    cleanup.add_argument(
        "--apply",
        action="store_true",
        help="Apply the current AUTO_CLEAN plan after complete revalidation.",
    )
    return parser


def add_repo_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", default=".")


def parse_json_argument(value: str, label: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError as error:
        raise GeneratedArtifactError(f"invalid_{label}") from error


def run(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    repo = Path(args.repo)
    if args.command == "prepare":
        command = parse_json_argument(args.command_json, "command_json")
        adjacent = [
            parse_json_argument(value, "adjacent_output")
            for value in args.adjacent_output
        ]
        return (
            prepare_contract(
                repo=repo,
                task_id=args.task_id,
                run_id=args.run_id,
                owner_id=args.owner_id,
                owner_pid=args.owner_pid,
                command=command,
                isolated_roots=args.isolated_root,
                adjacent_outputs=adjacent,
                retention=args.retention,
                contract_id=args.contract_id,
                lease_path=args.lease_path,
            ),
            0,
        )
    contract = load_immutable_document(Path(args.contract))
    if args.command == "observe":
        return (
            observe_artifacts(
                repo,
                contract,
                exit_code=args.exit_code,
            ),
            0,
        )
    manifest = load_immutable_document(Path(args.manifest))
    if args.command == "plan":
        return plan_cleanup(repo, contract, manifest), 0
    plan = load_immutable_document(Path(args.plan))
    if not args.apply:
        return (
            {
                "ok": False,
                "status": "authorization_required",
                "decision": plan.get("decision"),
                "nextAction": "rerun cleanup with --apply only for a current AUTO_CLEAN plan",
            },
            3,
        )
    prior_receipt = (
        load_immutable_document(Path(args.receipt))
        if args.receipt
        else None
    )
    receipt = apply_cleanup(
        repo,
        contract,
        manifest,
        plan,
        prior_receipt=prior_receipt,
    )
    return receipt, {"complete": 0, "failed": 1, "blocked": 3}[receipt["status"]]


def emit(document: dict[str, Any]) -> None:
    sys.stdout.buffer.write(canonical_document_bytes(document))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        document, returncode = run(args)
    except GeneratedArtifactError as error:
        emit(
            {
                "ok": False,
                "status": "invalid",
                "error": error.code,
                "detail": error.detail,
            }
        )
        return 2
    emit(document)
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
