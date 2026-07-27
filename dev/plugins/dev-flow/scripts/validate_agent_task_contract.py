#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from workflow_agent_task_contract import (
    validate_agent_task_contract_file,
    validate_agent_task_contract_files,
    validate_agent_task_worker_result,
)
from workflow_generated_artifacts import GeneratedArtifactError, load_immutable_document


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate one or more DevFlow Agent Task Contract markdown files.")
    parser.add_argument(
        "--contract",
        action="append",
        required=True,
        help="Path to AGENT_TASK_CONTRACT.md; repeat to validate disjoint worker write scopes.",
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Repository root used to validate optional generated-artifact references.",
    )
    parser.add_argument(
        "--worker-result",
        help=(
            "Canonical JSON worker result to run G41 generated-artifact "
            "post-validation; valid only with one --contract."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    contract_paths = [Path(value) for value in args.contract]
    report = (
        validate_agent_task_contract_file(contract_paths[0], repo=repo)
        if len(contract_paths) == 1
        else validate_agent_task_contract_files(contract_paths, repo=repo)
    )
    if args.worker_result:
        if len(contract_paths) != 1:
            report["ok"] = False
            report.setdefault("errors", []).append(
                "--worker-result requires exactly one --contract."
            )
        else:
            try:
                worker_result = load_immutable_document(
                    Path(args.worker_result).expanduser()
                )
            except GeneratedArtifactError as error:
                post_validation = {
                    "ok": False,
                    "gate": "G41",
                    "status": "failed",
                    "cleanupComplete": False,
                    "errors": [f"worker_result:{error.code}"],
                }
            else:
                post_validation = validate_agent_task_worker_result(
                    repo,
                    report,
                    worker_result,
                )
            report["postValidation"] = post_validation
            report["ok"] = bool(report.get("ok")) and post_validation["ok"]
            report.setdefault("errors", []).extend(post_validation["errors"])
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("ok" if report["ok"] else "; ".join(report["errors"]))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
