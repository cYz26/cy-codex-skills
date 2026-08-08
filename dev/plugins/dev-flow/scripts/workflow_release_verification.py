from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from workflow_planning_paths import atomic_write_devflow, release_verification_root
from workflow_implementation_readiness import repository_mutation_gate
from workflow_project_refresh import project_refresh_contract_snapshot
from workflow_state import resolve_state, trusted_repo_regular_file


SCHEMA_VERSION = 1
TARGET_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
REQUIRED_STATE_GATES = (
    "spec_approved",
    "plan_written",
    "implementation_done",
    "verification_passed",
    "state_updated",
)
IGNORED_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache"}
IGNORED_SUFFIXES = {".pyc", ".pyo", ".log", ".tmp"}
DEVFLOW_PREPROMOTION_COMMAND = (
    "pythondontwritebytecode=1 python3.12 "
    "dev/scripts/run_devflow_prepromotion_tests.py"
)
DEVFLOW_PREPROMOTION_RUNNER = "dev/scripts/run_devflow_prepromotion_tests.py"
PROJECT_REFRESH_MANIFEST = Path(".codex-plugin/project-migration.json")
PROJECT_REFRESH_FIXTURE_MANIFEST = Path("fixtures/project-refresh/manifest.json")
PROJECT_REFRESH_CONFIG_SENSITIVE = {
    "scripts/legacy_workflow_config.py",
    "scripts/plugin_project_migration.py",
    "scripts/workflow_project_refresh.py",
    "scripts/workflow_mode_routing.py",
    "scripts/workflow_scaffold.py",
    "scripts/scaffold_workflow.py",
}
PROJECT_REFRESH_REQUIRED_INPUTS = {
    "assets/templates/AGENTS.md.template",
    "fixtures/project-refresh/manifest.json",
    "scripts/legacy_workflow_config.py",
    "scripts/plugin_project_migration.py",
    "scripts/workflow_dependency_provenance.py",
    "scripts/workflow_methodology.py",
    "scripts/workflow_project_refresh.py",
    "scripts/workflow_project_skill_install.py",
    "scripts/workflow_validate.py",
    "skills/dev-flow-refresh/SKILL.md",
    "skills/dev-flow-refresh/references/project-refresh.md",
    "skills/plugin-project-migration/SKILL.md",
}
PROJECT_REFRESH_REVISION3_REQUIRED_INPUTS = {
    ".codex-plugin/plugin.json",
    ".codex-plugin/release-sync.json",
    "README.md",
    "assets/templates/STATE.md.template",
    "fixtures/implementation-readiness/agents-guidance-markers-revision2.json",
    "fixtures/implementation-readiness/project-refresh-cases-v3.json",
    "schemas/implementation-readiness-evidence-v1.schema.json",
    "schemas/implementation-readiness-provider-override-v1.schema.json",
    "schemas/implementation-readiness-receipt-v1.schema.json",
    "schemas/implementation-readiness-requirement-v1.schema.json",
    "scripts/implementation_readiness.py",
    "scripts/workflow_implementation_readiness.py",
    "scripts/workflow_state.py",
    "skills/execute-task/SKILL.md",
    "skills/feature-intake/SKILL.md",
    "skills/project-orchestrator/SKILL.md",
    "skills/verify-and-archive/SKILL.md",
    "skills/workflow-doctor/SKILL.md",
}
PROJECT_REFRESH_REVISION4_REQUIRED_INPUTS = {
    "fixtures/project-refresh/legacy-uninstall-cases-v4.json",
    "scripts/workflow_legacy_uninstall.py",
}
PROJECT_REFRESH_REVISION5_REQUIRED_INPUTS = {
    "fixtures/project-refresh/schema-transition-cases-v5.json",
}
PROJECT_REFRESH_REVISION6_REQUIRED_INPUTS = {
    "fixtures/project-refresh/review-hardening-cases-v6.json",
}
PROJECT_REFRESH_REVISION7_REQUIRED_INPUTS = {
    "fixtures/project-refresh/config-preimage-cases-v7.json",
}
PROJECT_REFRESH_REVISION8_REQUIRED_INPUTS = {
    "fixtures/project-refresh/rollback-preflight-cases-v8.json",
}
PROJECT_REFRESH_REVISION9_REQUIRED_INPUTS = {
    "fixtures/project-refresh/file-source-fingerprint-cases-v9.json",
}
PROJECT_REFRESH_PARITY_FILES = (
    ".codex-plugin/project-migration.json",
    "skills/dev-flow-refresh/SKILL.md",
    "skills/dev-flow-refresh/references/project-refresh.md",
    "skills/plugin-project-migration/SKILL.md",
    "schemas/project-refresh-contract.schema.json",
    "schemas/project-refresh-plan.schema.json",
    "schemas/project-refresh-receipt.schema.json",
)
PROJECT_REFRESH_REVISION3_PARITY_FILES = (
    ".codex-plugin/plugin.json",
    ".codex-plugin/release-sync.json",
    "README.md",
    "fixtures/implementation-readiness/agents-guidance-markers-revision2.json",
    "fixtures/implementation-readiness/project-refresh-cases-v3.json",
    "schemas/implementation-readiness-evidence-v1.schema.json",
    "schemas/implementation-readiness-provider-override-v1.schema.json",
    "schemas/implementation-readiness-receipt-v1.schema.json",
    "schemas/implementation-readiness-requirement-v1.schema.json",
)
PROJECT_REFRESH_MANIFEST_IDENTITY_FIELDS = (
    "schemaVersion",
    "engineSchemaVersion",
    "plugin",
    "stateKey",
    "projectSchema",
    "configTargets",
    "migrationSteps",
    "projectLocalSkills",
    "managedFiles",
    "agentsGuidance",
)
PROJECT_REFRESH_MANIFEST_CONFIG_SENSITIVE_FIELDS = (
    "projectSchema",
    "configTargets",
    "migrationSteps",
)


def project_refresh_tracked_inputs_sha256(plugin_root: Path) -> str:
    snapshot = project_refresh_contract_snapshot(plugin_root)
    return str(snapshot["trackedInputsSha256"])


def project_refresh_manifest_identity_sha256(document: dict[str, Any]) -> str:
    payload = {
        field: document.get(field)
        for field in PROJECT_REFRESH_MANIFEST_IDENTITY_FIELDS
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def analyze_project_refresh_impact(
    source_root: Path,
    baseline_root: Path | None = None,
    *,
    expected_change: str | None = None,
) -> dict[str, Any]:
    source_root = Path(source_root).expanduser().resolve()
    baseline_root = Path(baseline_root).expanduser().resolve() if baseline_root is not None else None
    errors: list[str] = []
    source_document = _read_refresh_manifest(source_root, errors, "source")
    source_snapshot = project_refresh_contract_snapshot(source_root)
    errors.extend(f"source_contract:{item}" for item in source_snapshot.get("errors", []))
    baseline_errors: list[str] = []
    baseline_document = (
        _read_refresh_manifest(baseline_root, baseline_errors, "baseline")
        if baseline_root
        else {}
    )
    errors.extend(baseline_errors)
    source_refresh = source_document.get("refreshContract", {}) if isinstance(source_document, dict) else {}
    baseline_refresh = baseline_document.get("refreshContract", {}) if isinstance(baseline_document, dict) else {}
    source_schema = source_document.get("projectSchema", {}) if isinstance(source_document, dict) else {}
    baseline_schema = baseline_document.get("projectSchema", {}) if isinstance(baseline_document, dict) else {}
    source_revision = _nonnegative_int(source_refresh.get("revision"), default=0)
    baseline_revision = _nonnegative_int(baseline_refresh.get("revision"), default=0)
    source_head = _nonnegative_int(source_schema.get("head"), default=0)
    source_minimum = _nonnegative_int(source_schema.get("minimumSupported"), default=0)
    baseline_head = _nonnegative_int(baseline_schema.get("head"), default=0)
    source_manifest_identity = project_refresh_manifest_identity_sha256(source_document)
    baseline_manifest_identity = (
        project_refresh_manifest_identity_sha256(baseline_document)
        if baseline_root is not None and baseline_document
        else None
    )
    manifest_changed = bool(
        baseline_manifest_identity is not None
        and source_manifest_identity != baseline_manifest_identity
    )
    manifest_config_sensitive = sorted(
        f"manifest:{field}"
        for field in PROJECT_REFRESH_MANIFEST_CONFIG_SENSITIVE_FIELDS
        if baseline_root is not None
        and source_document.get(field) != baseline_document.get(field)
    )

    evidence = source_refresh.get("evidence") if isinstance(source_refresh, dict) else None
    if not isinstance(evidence, dict):
        errors.append("refresh_impact_evidence_missing")
        evidence = {}
    if evidence.get("refreshContractRevision") != source_revision:
        errors.append("refresh_impact_evidence_revision_mismatch")
    if evidence.get("projectSchemaHead") != source_head:
        errors.append("refresh_impact_evidence_schema_mismatch")
    if evidence.get("trackedInputsSha256") != source_snapshot.get("trackedInputsSha256"):
        errors.append("refresh_impact_evidence_stale")
    if not isinstance(evidence.get("changeId"), str) or not evidence.get("changeId"):
        errors.append("refresh_impact_evidence_change_missing")
    elif expected_change is not None and evidence.get("changeId") != expected_change:
        errors.append("refresh_impact_evidence_change_mismatch")
    if not isinstance(evidence.get("reason"), str) or not evidence.get("reason"):
        errors.append("refresh_impact_evidence_reason_missing")
    if evidence.get("schemaDecision") not in {
        "advanced",
        "managed-refresh",
        "verified-unchanged",
        "not-applicable",
    }:
        errors.append("refresh_impact_evidence_schema_decision_invalid")
    inspected = evidence.get("inspectedSurfaces")
    if (
        not isinstance(inspected, list)
        or not inspected
        or not all(isinstance(item, str) and item for item in inspected)
    ):
        errors.append("refresh_impact_evidence_surfaces_missing")
    tracked_inputs = source_refresh.get("trackedInputs")
    tracked_set = set(map(str, tracked_inputs)) if isinstance(tracked_inputs, list) else set()
    required_inputs = set(PROJECT_REFRESH_REQUIRED_INPUTS)
    if source_revision >= 3:
        required_inputs.update(PROJECT_REFRESH_REVISION3_REQUIRED_INPUTS)
    if source_revision >= 4:
        required_inputs.update(PROJECT_REFRESH_REVISION4_REQUIRED_INPUTS)
    if source_revision >= 5:
        required_inputs.update(PROJECT_REFRESH_REVISION5_REQUIRED_INPUTS)
    if source_revision >= 6:
        required_inputs.update(PROJECT_REFRESH_REVISION6_REQUIRED_INPUTS)
    if source_revision >= 7:
        required_inputs.update(PROJECT_REFRESH_REVISION7_REQUIRED_INPUTS)
    if source_revision >= 8:
        required_inputs.update(PROJECT_REFRESH_REVISION8_REQUIRED_INPUTS)
    if source_revision >= 9:
        required_inputs.update(PROJECT_REFRESH_REVISION9_REQUIRED_INPUTS)
    for relative in sorted(required_inputs - tracked_set):
        errors.append(f"refresh_required_input_missing:{relative}")
    config_targets = source_document.get("configTargets")
    if isinstance(config_targets, dict):
        for relative in sorted(map(str, config_targets.values())):
            if relative not in tracked_set:
                errors.append(f"refresh_required_input_missing:{relative}")

    source_digests = {
        str(item["path"]): str(item["sha256"])
        for item in source_snapshot.get("inputDigests", [])
        if isinstance(item, dict) and item.get("path") and item.get("sha256")
    }
    baseline_snapshot = (
        project_refresh_contract_snapshot(baseline_root)
        if baseline_root is not None and str(baseline_document.get("schemaVersion")) == "2.0"
        else {"inputDigests": []}
    )
    baseline_digests = {
        str(item["path"]): str(item["sha256"])
        for item in baseline_snapshot.get("inputDigests", [])
        if isinstance(item, dict) and item.get("path") and item.get("sha256")
    }
    changed_inputs = sorted(
        path
        for path in set(source_digests) | set(baseline_digests)
        if source_digests.get(path) != baseline_digests.get(path)
    )
    immutable_errors = _immutable_config_target_errors(source_root, source_document, baseline_root, baseline_document)
    errors.extend(immutable_errors)
    config_sensitive = sorted(
        [
            path
            for path in changed_inputs
            if path.startswith("assets/project-refresh/") or path in PROJECT_REFRESH_CONFIG_SENSITIVE
        ]
        + manifest_config_sensitive
    )
    if changed_inputs and source_revision <= baseline_revision:
        errors.append("tracked_change_requires_refresh_revision_advance")
    if manifest_changed and source_revision <= baseline_revision:
        errors.append("manifest_change_requires_refresh_revision_advance")
    impact = source_refresh.get("impact")
    if config_sensitive and source_head <= baseline_head:
        errors.append("config_sensitive_change_requires_schema_advance")
    if (changed_inputs or manifest_changed) and impact == "not-applicable":
        errors.append("refresh_sensitive_change_cannot_be_not_applicable")
    if config_sensitive and impact != "changed":
        errors.append("config_sensitive_change_requires_changed_impact")

    migration_errors, coverage = _migration_coverage(
        source_document,
        max(source_minimum, baseline_head),
        source_head,
    )
    errors.extend(migration_errors)
    fixture_errors = _validate_refresh_fixture_matrix(source_root, source_document)
    errors.extend(fixture_errors)
    changed = bool(
        changed_inputs
        or manifest_changed
        or source_head != baseline_head
        or source_revision != baseline_revision
    )
    source_contract_digest = source_snapshot.get("identity", {}).get("refreshContractDigest")
    baseline_contract_digest = baseline_snapshot.get("identity", {}).get("refreshContractDigest")
    return {
        "ok": not errors,
        "status": "blocked" if errors else ("changed_covered" if changed else "current"),
        "sourceRoot": str(source_root),
        "baselineRoot": str(baseline_root) if baseline_root is not None else None,
        "impact": impact,
        "schemaDecision": evidence.get("schemaDecision"),
        "evidenceChange": evidence.get("changeId"),
        "expectedChange": expected_change,
        "sourceRevision": source_revision,
        "baselineRevision": baseline_revision,
        "sourceProjectSchemaHead": source_head,
        "baselineProjectSchemaHead": baseline_head,
        "trackedInputsSha256": source_snapshot.get("trackedInputsSha256"),
        "manifestIdentitySha256": source_manifest_identity,
        "baselineManifestIdentitySha256": baseline_manifest_identity,
        "manifestChanged": manifest_changed,
        "sourceRefreshContractDigest": source_contract_digest,
        "baselineRefreshContractDigest": baseline_contract_digest,
        "refreshContractDigestChanged": bool(
            baseline_contract_digest is not None
            and source_contract_digest != baseline_contract_digest
        ),
        "changedInputs": changed_inputs,
        "configSensitiveChanges": config_sensitive,
        "migrationCoverage": coverage,
        "errors": sorted(set(errors)),
        "nextAction": (
            "Project Refresh Impact is covered by the versioned contract and fixture matrix."
            if not errors
            else "Update the refresh contract, migration coverage, fixtures, and evidence before promotion."
        ),
    }


def verify_project_refresh_release_parity(
    source_root: Path,
    release_root: Path,
    cache_root: Path | None = None,
) -> dict[str, Any]:
    source_root = Path(source_root).expanduser().resolve()
    release_root = Path(release_root).expanduser().resolve()
    cache_root = Path(cache_root).expanduser().resolve() if cache_root is not None else None
    errors: list[str] = []
    source = project_refresh_contract_snapshot(source_root)
    release = project_refresh_contract_snapshot(release_root)
    errors.extend(f"source_contract:{item}" for item in source.get("errors", []))
    errors.extend(f"release_contract:{item}" for item in release.get("errors", []))
    if source.get("identity") != release.get("identity"):
        errors.append("release_contract_identity_mismatch")
    direct_files = set(PROJECT_REFRESH_PARITY_FILES)
    source_document = _read_refresh_manifest(source_root, errors, "source")
    source_refresh = source_document.get("refreshContract", {}) if isinstance(source_document, dict) else {}
    source_revision = _nonnegative_int(source_refresh.get("revision"), default=0)
    if source_revision >= 3:
        direct_files.update(PROJECT_REFRESH_REVISION3_PARITY_FILES)
    direct_files.update(
        str(path)
        for path in source_document.get("configTargets", {}).values()
        if isinstance(path, str)
    )
    fixture_root = source_root / "fixtures" / "project-refresh"
    if fixture_root.is_dir() and not fixture_root.is_symlink():
        direct_files.update(
            path.relative_to(source_root).as_posix()
            for path in fixture_root.rglob("*")
            if path.is_file() and not path.is_symlink()
        )
    for relative in sorted(direct_files):
        if not _files_match(source_root / relative, release_root / relative):
            errors.append(f"release_file_mismatch:{relative}")
    if not (release_root / "scripts" / "plugin_project_migration.py").is_file():
        errors.append("release_packaged_cli_missing")
    fixture_errors = _validate_refresh_fixture_matrix(source_root, source_document)
    errors.extend(fixture_errors)

    cache_snapshot: dict[str, Any] | None = None
    if cache_root is not None:
        cache_snapshot = project_refresh_contract_snapshot(cache_root)
        errors.extend(f"cache_contract:{item}" for item in cache_snapshot.get("errors", []))
        if cache_snapshot.get("identity") != release.get("identity"):
            errors.append("cache_contract_identity_mismatch")
        for relative in sorted(direct_files):
            if not _files_match(release_root / relative, cache_root / relative):
                errors.append(f"cache_file_mismatch:{relative}")
        if not (cache_root / "scripts" / "plugin_project_migration.py").is_file():
            errors.append("cache_packaged_cli_missing")
    return {
        "ok": not errors,
        "status": "verified" if not errors else "drift",
        "source": source,
        "release": release,
        "cache": cache_snapshot,
        "errors": sorted(set(errors)),
        "nextAction": (
            "Project-refresh source, release, and named cache identities match."
            if not errors
            else "Regenerate or refresh only through the separately authorized release/cache workflows."
        ),
    }


def _read_refresh_manifest(root: Path | None, errors: list[str], label: str) -> dict[str, Any]:
    if root is None:
        return {}
    path = root / PROJECT_REFRESH_MANIFEST
    if path.is_symlink() or not path.is_file():
        errors.append(f"{label}_refresh_manifest_missing_or_untrusted")
        return {}
    try:
        document = json.loads(path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError):
        errors.append(f"{label}_refresh_manifest_invalid")
        return {}
    if not isinstance(document, dict):
        errors.append(f"{label}_refresh_manifest_invalid")
        return {}
    return document


def _nonnegative_int(value: Any, *, default: int) -> int:
    return value if isinstance(value, int) and value >= 0 else default


def _immutable_config_target_errors(
    source_root: Path,
    source: dict[str, Any],
    baseline_root: Path | None,
    baseline: dict[str, Any],
) -> list[str]:
    if baseline_root is None:
        return []
    errors: list[str] = []
    source_targets = source.get("configTargets", {}) if isinstance(source.get("configTargets"), dict) else {}
    baseline_targets = baseline.get("configTargets", {}) if isinstance(baseline.get("configTargets"), dict) else {}
    for version in sorted(set(baseline_targets) - set(source_targets)):
        errors.append(f"immutable_config_target_removed:{version}")
    for version in sorted(set(source_targets) & set(baseline_targets)):
        source_relative = source_targets.get(version)
        baseline_relative = baseline_targets.get(version)
        if source_relative != baseline_relative or not _files_match(
            source_root / str(source_relative), baseline_root / str(baseline_relative)
        ):
            errors.append(f"immutable_config_target_mutated:{version}")
    return errors


def _migration_coverage(
    contract: dict[str, Any],
    start: int,
    head: int,
) -> tuple[list[str], dict[str, list[str]]]:
    steps = contract.get("migrationSteps", []) if isinstance(contract.get("migrationSteps"), list) else []
    outgoing: dict[int, dict[str, Any]] = {}
    errors: list[str] = []
    for step in steps:
        if not isinstance(step, dict) or not isinstance(step.get("from"), int):
            continue
        source = int(step["from"])
        if source in outgoing:
            errors.append(f"migration_path_not_unique:{source}")
        else:
            outgoing[source] = step
    coverage: dict[str, list[str]] = {}
    for observed in range(start, head):
        cursor = observed
        path: list[str] = []
        visited: set[int] = set()
        while cursor < head and cursor not in visited and cursor in outgoing:
            visited.add(cursor)
            step = outgoing[cursor]
            path.append(str(step.get("id") or ""))
            cursor = _nonnegative_int(step.get("to"), default=-1)
        if cursor != head or not all(path):
            errors.append(f"migration_path_missing:{observed}")
        else:
            coverage[str(observed)] = path
    return errors, coverage


def _validate_refresh_fixture_matrix(root: Path, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    path = root / PROJECT_REFRESH_FIXTURE_MANIFEST
    if path.is_symlink() or not path.is_file():
        return ["fixture_matrix_missing_or_untrusted"]
    try:
        document = json.loads(path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError):
        return ["fixture_matrix_invalid"]
    if not isinstance(document, dict):
        return ["fixture_matrix_invalid"]
    schema = contract.get("projectSchema", {}) if isinstance(contract.get("projectSchema"), dict) else {}
    head = _nonnegative_int(schema.get("head"), default=0)
    minimum = _nonnegative_int(schema.get("minimumSupported"), default=0)
    if document.get("currentProjectSchema") != head:
        errors.append("fixture_matrix_head_mismatch")
    entries = document.get("fixtures") if isinstance(document.get("fixtures"), list) else []
    automatic: dict[int, list[dict[str, Any]]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("fixture_matrix_entry_invalid")
            continue
        relative = entry.get("path")
        observed = entry.get("observedSchema")
        if not isinstance(relative, str) or Path(relative).name != relative:
            errors.append("fixture_matrix_path_invalid")
            continue
        fixture = path.parent / relative
        if fixture.is_symlink() or not fixture.is_file():
            errors.append(f"fixture_missing_or_untrusted:{relative}")
        if isinstance(observed, int) and not entry.get("manualOnly"):
            automatic.setdefault(observed, []).append(entry)
    _, expected_coverage = _migration_coverage(contract, minimum, head)
    expected_coverage[str(head)] = []
    for observed in range(minimum, head + 1):
        candidates = automatic.get(observed, [])
        if not candidates:
            errors.append(f"fixture_matrix_missing_schema:{observed}")
            continue
        expected = expected_coverage.get(str(observed))
        if expected is None or not any(entry.get("expectedMigrationPath") == expected for entry in candidates):
            errors.append(f"fixture_matrix_path_mismatch:{observed}")
    return errors


def _files_match(left: Path, right: Path) -> bool:
    return (
        not left.is_symlink()
        and not right.is_symlink()
        and left.is_file()
        and right.is_file()
        and left.read_bytes() == right.read_bytes()
    )


def record_release_verification(
    repo: Path,
    target: str,
    change: str,
    *,
    development_command: str,
    development_result: str,
    openspec_command: str,
    openspec_result: str,
    diff_command: str,
    diff_result: str,
) -> dict[str, Any]:
    repo = Path(repo).resolve()
    validate_target(target)
    snapshot = release_source_snapshot(repo, target)
    refresh_impact = None
    if target == "dev-flow":
        refresh_impact = analyze_project_refresh_impact(
            repo / "dev" / "plugins" / target,
            repo / "plugins" / target,
            expected_change=change,
        )
    checks = {
        "development": check_record(development_command, development_result),
        "openspec": check_record(openspec_command, openspec_result),
        "diff": check_record(diff_command, diff_result),
    }
    command_errors = validate_release_commands(target, checks)
    if not snapshot["ready"] or command_errors or (refresh_impact is not None and not refresh_impact["ok"]):
        return {
            "ok": False,
            "status": "source_or_verification_incomplete",
            "source": snapshot,
            "projectRefreshImpact": refresh_impact,
            "errors": command_errors + (refresh_impact["errors"] if refresh_impact is not None else []),
        }
    receipt = {
        "schemaVersion": SCHEMA_VERSION,
        "target": target,
        "change": change,
        "sourceSha256": snapshot["sha256"],
        "sourceFiles": snapshot["files"],
        "checks": checks,
        "projectRefreshImpact": refresh_impact,
        "recordedAt": datetime.now(timezone.utc).isoformat(),
    }
    path = release_verification_path(repo, target)
    atomic_write_devflow(repo, path, json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return {
        "ok": True,
        "status": "recorded",
        "path": path.relative_to(repo).as_posix(),
        "sourceSha256": snapshot["sha256"],
    }


def verify_release_verification(repo: Path, target: str, change: str) -> dict[str, Any]:
    repo = Path(repo).resolve()
    validate_target(target)
    path = release_verification_path(repo, target)
    if not trusted_repo_regular_file(repo, path):
        return verification_report(False, "missing_or_untrusted_evidence", path)
    try:
        receipt = json.loads(path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError):
        return verification_report(False, "invalid_evidence", path)
    if not isinstance(receipt, dict) or receipt.get("schemaVersion") != SCHEMA_VERSION:
        return verification_report(False, "invalid_evidence", path)
    if receipt.get("target") != target or receipt.get("change") != change:
        return verification_report(False, "change_or_target_mismatch", path)
    checks = receipt.get("checks")
    if not isinstance(checks, dict):
        return verification_report(False, "invalid_evidence", path)
    errors = validate_release_commands(target, checks)
    if errors:
        return verification_report(False, "incomplete_verification", path, errors=errors)
    snapshot = release_source_snapshot(repo, target)
    if not snapshot["ready"]:
        return verification_report(False, "untrusted_source", path, source=snapshot)
    if receipt.get("sourceSha256") != snapshot["sha256"]:
        return verification_report(False, "stale_evidence", path)
    if receipt.get("sourceFiles") != snapshot["files"]:
        return verification_report(False, "stale_evidence", path)
    if target == "dev-flow":
        recorded_impact = receipt.get("projectRefreshImpact")
        if not isinstance(recorded_impact, dict) or not recorded_impact.get("ok"):
            return verification_report(False, "project_refresh_impact_incomplete", path)
        source_manifest = repo / "dev" / "plugins" / target / PROJECT_REFRESH_MANIFEST
        if source_manifest.is_file():
            current_impact = analyze_project_refresh_impact(
                repo / "dev" / "plugins" / target,
                repo / "plugins" / target,
                expected_change=change,
            )
            if not current_impact["ok"]:
                return verification_report(
                    False,
                    "project_refresh_impact_incomplete",
                    path,
                    projectRefreshImpact=current_impact,
                )
            stable_fields = (
                "impact",
                "schemaDecision",
                "sourceRevision",
                "baselineRevision",
                "sourceProjectSchemaHead",
                "baselineProjectSchemaHead",
                "trackedInputsSha256",
                "manifestIdentitySha256",
                "baselineManifestIdentitySha256",
                "manifestChanged",
                "sourceRefreshContractDigest",
                "baselineRefreshContractDigest",
                "refreshContractDigestChanged",
                "changedInputs",
                "configSensitiveChanges",
                "migrationCoverage",
            )
            if any(recorded_impact.get(key) != current_impact.get(key) for key in stable_fields):
                return verification_report(False, "project_refresh_impact_stale", path)
    return verification_report(
        True,
        "ready",
        path,
        sourceSha256=snapshot["sha256"],
    )


def release_promotion_readiness(
    repo: Path,
    target: str,
    *,
    require_authorization: bool,
) -> dict[str, Any]:
    repo = Path(repo).resolve()
    resolution = resolve_state(repo)
    state = resolution.get("data", {})
    gates = state.get("gates", {}) if isinstance(state.get("gates"), dict) else {}
    change = state.get("current_change", {})
    change_id = str(change.get("id") or "") if isinstance(change, dict) else ""
    change_status = str(change.get("status") or "") if isinstance(change, dict) else ""
    blockers: list[str] = []
    if resolution.get("status") != "namespaced":
        blockers.append("trusted_namespaced_state")
    blockers.extend(key for key in REQUIRED_STATE_GATES if not bool(gates.get(key)))
    if not change_id or change_id == "none":
        blockers.append("current_change")
    if change_status != "verified":
        blockers.append("current_change_verified")
    evidence = (
        verify_release_verification(repo, target, change_id)
        if change_id and change_id != "none"
        else {"ready": False, "status": "missing_change"}
    )
    if not evidence.get("ready"):
        blockers.append("fresh_complete_release_verification")
    if require_authorization and not bool(gates.get("release_allowed")):
        blockers.append("durable_release_authorization")
    implementation_readiness = repository_mutation_gate(
        repo,
        ordinary_authority=True,
        change_id=change_id or None,
    )
    if implementation_readiness["applicable"] and not implementation_readiness["allowed"]:
        blockers.append("implementation_readiness")
    return {
        "ready": not blockers,
        "target": target,
        "change": change_id or None,
        "stateStatus": resolution.get("status"),
        "stateGates": gates,
        "evidence": evidence,
        "blockers": sorted(set(blockers)),
        "durableReleaseAuthorization": bool(gates.get("release_allowed")),
        "implementationReadiness": implementation_readiness,
    }


def release_source_snapshot(repo: Path, target: str) -> dict[str, Any]:
    repo = Path(repo).resolve()
    validate_target(target)
    roots = [repo / "dev" / "plugins" / target, repo / "dev" / "skills" / target]
    source_root = next((root for root in roots if root.exists() or root.is_symlink()), roots[0])
    if source_root.is_symlink() or not source_root.is_dir():
        return {"ready": False, "status": "missing_or_untrusted_source", "files": []}
    if not path_components_are_local(repo, source_root):
        return {"ready": False, "status": "missing_or_untrusted_source", "files": []}
    files: dict[str, str] = {}
    untrusted: list[str] = []
    for path in sorted(source_root.rglob("*")):
        relative = path.relative_to(repo).as_posix()
        if path.is_symlink() or not path_components_are_local(repo, path):
            untrusted.append(relative)
            continue
        if path.is_dir():
            continue
        if not path.is_file():
            untrusted.append(relative)
            continue
        local = path.relative_to(source_root)
        if any(part in IGNORED_PARTS for part in local.parts):
            continue
        if path.suffix in IGNORED_SUFFIXES or path.name == ".DS_Store":
            continue
        files[relative] = file_sha256(path)
    helpers, helper_errors = release_build_helpers(repo, source_root, target)
    untrusted.extend(helper_errors)
    for helper in helpers:
        if not trusted_repo_regular_file(repo, helper):
            untrusted.append(repo_relative_or_absolute(repo, helper))
            continue
        files[helper.relative_to(repo).as_posix()] = file_sha256(helper)
    canonical = "\n".join(f"{path}\0{digest}" for path, digest in sorted(files.items()))
    ready = bool(files) and not untrusted
    return {
        "ready": ready,
        "status": "ready" if ready else "untrusted_source",
        "sha256": hashlib.sha256(canonical.encode()).hexdigest() if ready else None,
        "files": [{"path": path, "sha256": digest} for path, digest in sorted(files.items())],
        "untrustedPaths": sorted(set(untrusted)),
    }


def release_build_helpers(
    repo: Path,
    source_root: Path,
    target: str,
) -> tuple[list[Path], list[str]]:
    metadata = source_root / ".codex-plugin" / "release-sync.json"
    required = target == "dev-flow"
    if not (metadata.exists() or metadata.is_symlink()):
        missing = [repo_relative_or_absolute(repo, metadata)] if required else []
        return [], missing
    if not trusted_repo_regular_file(repo, metadata):
        return [], [repo_relative_or_absolute(repo, metadata)]
    try:
        document = json.loads(metadata.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return [], [repo_relative_or_absolute(repo, metadata)]
    if not isinstance(document, dict) or not isinstance(document.get("buildCommands", []), list):
        return [], [repo_relative_or_absolute(repo, metadata)]
    helpers: list[Path] = []
    for command in document.get("buildCommands", []):
        if not isinstance(command, list):
            continue
        for token in command:
            if not isinstance(token, str) or not token.startswith("dev/"):
                continue
            # Include declared repository-local helpers even when they are
            # missing. The caller's trusted-file check then makes an absent
            # build dependency a release-source blocker instead of silently
            # omitting it from the source snapshot.
            helpers.append(repo / token)
    if required:
        helpers.append(repo / DEVFLOW_PREPROMOTION_RUNNER)
    return sorted(set(helpers)), []


def validate_release_commands(target: str, checks: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = {"development", "openspec", "diff"}
    if set(checks) != expected:
        errors.append("release verification must contain development, openspec, and diff checks")
        return errors
    for name in sorted(expected):
        record = checks.get(name)
        if not isinstance(record, dict) or record.get("result") != "pass":
            errors.append(f"{name} verification did not pass")
            continue
        command = str(record.get("command") or "")
        normalized = " ".join(command.lower().split())
        if name == "development" and not complete_development_command(normalized, target):
            errors.append("development verification is not the canonical complete test command")
        elif name == "openspec" and not all(
            marker in normalized for marker in ("openspec", "validate", "--all", "--strict")
        ):
            errors.append("OpenSpec verification must be strict and repository-wide")
        elif name == "diff" and "git diff --check" not in normalized:
            errors.append("diff verification must run git diff --check")
    return errors


def complete_development_command(command: str, target: str) -> bool:
    if target == "dev-flow":
        return command == DEVFLOW_PREPROMOTION_COMMAND
    return command == (
        "pythondontwritebytecode=1 python3.12 -m unittest discover "
        f"-s dev/plugins/{target}/tests -p 'test_*.py'"
    )


def repo_relative_or_absolute(repo: Path, path: Path) -> str:
    try:
        return path.relative_to(repo).as_posix()
    except ValueError:
        return str(path)


def check_record(command: str, result: str) -> dict[str, str]:
    return {"command": command.strip(), "result": result.strip().lower()}


def release_verification_path(repo: Path, target: str) -> Path:
    validate_target(target)
    return release_verification_root(repo) / f"{target}.json"


def validate_target(target: str) -> None:
    if not TARGET_ID.fullmatch(str(target)):
        raise ValueError(f"invalid release target: {target!r}")


def path_components_are_local(repo: Path, path: Path) -> bool:
    repo = Path(repo).resolve()
    candidate = Path(path).absolute()
    try:
        relative = candidate.relative_to(repo)
    except ValueError:
        return False
    current = repo
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return False
    return True


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verification_report(ready: bool, status: str, path: Path, **extra: Any) -> dict[str, Any]:
    return {"ready": ready, "status": status, "path": str(path), **extra}
