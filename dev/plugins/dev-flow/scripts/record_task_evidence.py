#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from workflow_generated_artifacts import (
    GeneratedArtifactError,
    load_immutable_document,
    local_path,
    validate_terminal_cleanup,
)
from workflow_planning_paths import atomic_write_devflow, verification_root


GENERATED_ARTIFACT_ARGUMENTS = (
    "generated_artifact_contract",
    "generated_artifact_manifest",
    "generated_artifact_plan",
    "generated_artifact_cleanup_receipt",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a DevFlow task evidence note.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--claim", required=True)
    parser.add_argument("--command", action="append", default=[])
    parser.add_argument("--generated-artifact-contract")
    parser.add_argument("--generated-artifact-manifest")
    parser.add_argument("--generated-artifact-plan")
    parser.add_argument("--generated-artifact-cleanup-receipt")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    repo = Path(args.repo).expanduser().resolve()
    generated_references = {
        name: getattr(args, name)
        for name in GENERATED_ARTIFACT_ARGUMENTS
    }
    provided = [name for name, value in generated_references.items() if value]
    if provided and len(provided) != len(GENERATED_ARTIFACT_ARGUMENTS):
        return fail(
            "Generated Artifact Lifecycle evidence requires contract, "
            "manifest, plan, and cleanup receipt references.",
            json_output=args.json,
        )
    lifecycle_section = ""
    if provided:
        lifecycle_section, errors = generated_artifact_evidence(
            repo,
            task_id=args.task_id,
            references=generated_references,
        )
        if errors:
            return fail(
                "; ".join(errors),
                json_output=args.json,
            )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    path = verification_root(repo) / f"{timestamp}-{args.task_id}-evidence.md"
    commands = "\n".join(f"- `{command}`" for command in args.command) or "- none"
    atomic_write_devflow(
        repo,
        path,
        f"# Evidence: {args.task_id}\n\n"
        f"## Claim\n{args.claim}\n\n"
        f"## Commands Run\n{commands}\n\n"
        f"{lifecycle_section}"
        "## Risks / Gaps\n- none recorded\n",
    )
    report = {
        "ok": True,
        "path": str(path),
        "task_id": args.task_id,
        "generatedArtifactLifecycle": (
            {"gate": "G41", "status": "passed", "cleanupComplete": True}
            if provided
            else {"gate": "G41", "status": "not_applicable", "cleanupComplete": False}
        ),
    }
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(str(path))
    return 0


def generated_artifact_evidence(
    repo: Path,
    *,
    task_id: str,
    references: dict[str, str | None],
) -> tuple[str, list[str]]:
    labels = {
        "generated_artifact_contract": "contract",
        "generated_artifact_manifest": "manifest",
        "generated_artifact_plan": "plan",
        "generated_artifact_cleanup_receipt": "cleanup receipt",
    }
    documents: dict[str, dict[str, object]] = {}
    errors: list[str] = []
    for argument, label in labels.items():
        reference = references[argument]
        if not isinstance(reference, str):
            errors.append(f"{label} reference is missing")
            continue
        try:
            path = local_path(repo, reference, require_exists=True)
            documents[argument] = load_immutable_document(path)
        except GeneratedArtifactError as error:
            errors.append(f"{label}:{error.code}")
    if errors:
        return "", sorted(set(errors))

    contract = documents["generated_artifact_contract"]
    if contract.get("taskId") != task_id:
        errors.append("generated artifact contract task id does not match evidence task id")
    errors.extend(
        validate_terminal_cleanup(
            repo,
            contract,
            documents["generated_artifact_manifest"],
            documents["generated_artifact_plan"],
            documents["generated_artifact_cleanup_receipt"],
        )
    )
    if errors:
        return "", sorted(set(errors))

    section = (
        "## Generated Artifact Lifecycle\n\n"
        "- G41: `passed`\n"
        "- cleanup_complete: `true`\n"
        f"- Contract: `{references['generated_artifact_contract']}`\n"
        f"- Manifest: `{references['generated_artifact_manifest']}`\n"
        f"- Plan: `{references['generated_artifact_plan']}`\n"
        "- Cleanup receipt: "
        f"`{references['generated_artifact_cleanup_receipt']}`\n\n"
    )
    return section, []


def fail(message: str, *, json_output: bool) -> int:
    report = {"ok": False, "error": message}
    if json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(message)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
