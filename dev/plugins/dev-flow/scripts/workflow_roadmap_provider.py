from __future__ import annotations

import copy
import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Mapping, Sequence

from workflow_planning_paths import atomic_write_text
from workflow_provider_registry import default_plugin_root, side_effect_decision
from workflow_state import parse_state


GSD_RUNTIME = Path(".codex/gsd-core/bin/gsd-tools.cjs")
VALID_BINDING_STATUSES = {"active", "inactive", "archived"}
CANONICAL_GSD_PHASE_FILE = re.compile(
    r"^(?:M\d+-)?\d+(?:\.\d+)?-[a-z0-9][a-z0-9-]*/"
    r"(?:M\d+-)?\d+(?:\.\d+)?-\d{2}-(?:PLAN|SUMMARY|CONTEXT|VALIDATION)\.md$",
    re.IGNORECASE,
)
SAFE_GSD_PHASE_NUMBER = re.compile(r"^[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)*$")
SAFE_GSD_PHASE_DIRECTORY = re.compile(r"^[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)*$")
SAFE_CHANGE_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")


Runner = Callable[..., subprocess.CompletedProcess[str]]


def infer_roadmap_ownership(
    repo: Path,
    *,
    adapter: "GsdReadOnlyAdapter | None" = None,
) -> dict[str, Any]:
    """Infer legacy roadmap ownership from strong content, never installation.

    The result is diagnostic only. It does not persist a provider selection and
    intentionally ignores installed GSD runtime, skills, agents, and profile
    files. A ROADMAP file is evidence only when the project-local GSD adapter
    validates it; DevFlow does not implement a second roadmap parser.
    """

    repo = Path(repo).resolve()
    planning = repo / ".planning"
    gsd_evidence: list[str] = []
    devflow_evidence: list[str] = []
    conflicts: list[str] = []

    state = planning / "STATE.md"
    state_text = _read_text(state)
    if re.search(r"(?m)^\s*gsd_state_version\s*:", state_text):
        gsd_evidence.append(_evidence("gsd_state_version", state, repo))
    if re.search(r"(?m)^\s*workflow_version\s*:", state_text):
        devflow_evidence.append(_evidence("workflow_version", state, repo))

    project = planning / "PROJECT.md"
    if _is_gsd_project(_read_text(project)):
        gsd_evidence.append(_evidence("gsd_project_schema", project, repo))

    config = planning / "config.json"
    config_data = _read_json(config)
    if _is_gsd_config(config_data):
        gsd_evidence.append(_evidence("gsd_config_schema", config, repo))

    phases = planning / "phases"
    if phases.exists():
        for path in sorted(phases.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(phases).as_posix()
            if CANONICAL_GSD_PHASE_FILE.fullmatch(relative):
                gsd_evidence.append(_evidence("canonical_gsd_phase_file", path, repo))

    roadmap = planning / "ROADMAP.md"
    roadmap_text = _read_text(roadmap)
    if roadmap_text and adapter is not None:
        validation = adapter.roadmap_validate()
        if validation.get("ok"):
            gsd_evidence.append(_evidence("gsd_runtime_validated_roadmap", roadmap, repo))
        else:
            conflicts.append(
                "GSD runtime could not validate root .planning/ROADMAP.md: "
                f"{validation.get('reason') or 'unknown_error'}"
            )
    if _is_legacy_devflow_roadmap(roadmap_text):
        devflow_evidence.append(_evidence("legacy_devflow_roadmap", roadmap, repo))

    if gsd_evidence and devflow_evidence:
        conflicts.append("root planning artifacts contain both DevFlow and GSD ownership markers")
    if conflicts:
        return {
            "provider": None,
            "status": "manual_review_required",
            "confidence": "conflict",
            "evidence": [*gsd_evidence, *devflow_evidence],
            "gsdEvidence": gsd_evidence,
            "devflowEvidence": devflow_evidence,
            "conflicts": conflicts,
            "migrationRecommended": True,
        }
    if gsd_evidence:
        return {
            "provider": "gsd",
            "status": "inferred",
            "confidence": "high",
            "evidence": gsd_evidence,
            "gsdEvidence": gsd_evidence,
            "devflowEvidence": [],
            "conflicts": [],
            "migrationRecommended": True,
        }
    if devflow_evidence:
        return {
            "provider": "none",
            "status": "legacy_devflow",
            "confidence": "high",
            "evidence": devflow_evidence,
            "gsdEvidence": [],
            "devflowEvidence": devflow_evidence,
            "conflicts": [],
            "migrationRecommended": True,
        }
    return {
        "provider": "none",
        "status": "no_markers",
        "confidence": "default",
        "evidence": [],
        "gsdEvidence": [],
        "devflowEvidence": [],
        "conflicts": [],
        "migrationRecommended": False,
    }


class GsdReadOnlyAdapter:
    """Narrow adapter for the selected project-local GSD runtime.

    Only four read-only operations are exposed. Every operation requests JSON
    errors and fixes the runtime cwd explicitly. No fallback parser or phase
    directory guessing exists in this module.
    """

    def __init__(
        self,
        repo: Path,
        *,
        runner: Runner = subprocess.run,
        node: str = "node",
        timeout: int = 30,
    ) -> None:
        self.repo = Path(repo).resolve()
        self.runtime = (self.repo / GSD_RUNTIME).resolve()
        self.runner = runner
        self.node = node
        self.timeout = timeout

    def state_load(self) -> dict[str, Any]:
        return self._run(("state", "load"))

    def roadmap_validate(self) -> dict[str, Any]:
        return self._run(("roadmap", "validate"))

    def roadmap_get_phase(self, phase_id: str) -> dict[str, Any]:
        return self._run(("roadmap", "get-phase", _required_text(phase_id, "phase_id")))

    def find_phase(self, phase_id: str) -> dict[str, Any]:
        return self._run(("find-phase", _required_text(phase_id, "phase_id")))

    def resolve_uat_artifact(self, phase_id: str) -> dict[str, Any]:
        """Resolve the one canonical UAT artifact without globbing or guessing."""

        return resolve_gsd_uat_artifact(self.repo, phase_id, adapter=self)

    def diagnose(self, phase_ids: Iterable[str] = ()) -> dict[str, Any]:
        results = [self.state_load(), self.roadmap_validate()]
        phase_results: dict[str, dict[str, Any]] = {}
        for phase_id in _unique_strings(phase_ids):
            roadmap = self.roadmap_get_phase(phase_id)
            directory = self.find_phase(phase_id)
            phase_results[phase_id] = {"roadmap": roadmap, "directory": directory}
            results.extend((roadmap, directory))

        blocking: list[str] = []
        for result in results:
            if not result.get("ok"):
                blocking.append(str(result.get("reason") or "runtime_command_failed"))
        for phase_id, phase in phase_results.items():
            if not _phase_found(phase["roadmap"]) or not _phase_found(phase["directory"]):
                blocking.append(f"unresolved_phase:{phase_id}")

        state = results[0]
        commit_docs = _commit_docs(state.get("data", {})) if state.get("ok") else None
        ready = not blocking
        return {
            "ready": ready,
            "status": "ready" if ready else "manual_review_required",
            "runtime": str(self.runtime),
            "commitDocs": commit_docs,
            "state": state,
            "roadmap": results[1],
            "phases": phase_results,
            "blockingReasons": _unique_strings(blocking),
        }

    def _run(self, operation: Sequence[str]) -> dict[str, Any]:
        command = [
            self.node,
            str(self.runtime),
            *operation,
            "--cwd",
            str(self.repo),
            "--json-errors",
        ]
        if not self.runtime.is_file():
            return _adapter_error(command, "runtime_missing", f"missing GSD runtime: {self.runtime}")
        try:
            completed = self.runner(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout,
            )
        except FileNotFoundError as error:
            return _adapter_error(command, "runtime_launcher_missing", str(error))
        except subprocess.TimeoutExpired:
            return _adapter_error(command, "runtime_timeout", f"command exceeded {self.timeout} seconds")
        except OSError as error:
            return _adapter_error(command, "runtime_error", str(error))

        raw = (completed.stdout or "").strip() or (completed.stderr or "").strip()
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return _adapter_error(
                command,
                "invalid_json",
                "GSD runtime did not return one structured JSON object",
                exit_code=completed.returncode,
            )
        if not isinstance(payload, dict):
            return _adapter_error(
                command,
                "invalid_json",
                "GSD runtime JSON must be an object",
                exit_code=completed.returncode,
            )
        if completed.returncode != 0 or payload.get("ok") is False:
            reason = str(payload.get("reason") or "command_failed")
            return _adapter_error(
                command,
                reason,
                str(payload.get("message") or "GSD read-only command failed"),
                exit_code=completed.returncode,
                error=payload,
            )
        return {
            "ok": True,
            "status": "ready",
            "reason": "",
            "command": command,
            "exitCode": completed.returncode,
            "data": payload,
        }


def resolve_gsd_uat_artifact(
    repo: Path,
    phase_id: str,
    *,
    adapter: GsdReadOnlyAdapter | None = None,
) -> dict[str, Any]:
    """Resolve ``<phase-number>-UAT.md`` from two trusted read-only GSD queries.

    Only the flat, active ``.planning/phases/<phase-dir>`` namespace is
    accepted. Archived milestone directories, traversal, absolute paths, and
    symlinked path components fail closed.
    """

    repo = Path(repo).resolve()
    phase_id = _required_text(phase_id, "phase_id")
    selected = adapter or GsdReadOnlyAdapter(repo)
    roadmap = selected.roadmap_get_phase(phase_id)
    directory = selected.find_phase(phase_id)
    if not (
        roadmap.get("ok")
        and directory.get("ok")
        and _phase_found(roadmap)
        and _phase_found(directory)
    ):
        reasons = [
            str(result.get("reason") or "phase_not_found")
            for result in (roadmap, directory)
            if not result.get("ok") or not _phase_found(result)
        ]
        return {
            "ok": False,
            "status": "manual_review_required",
            "reason": "gsd_phase_unresolved",
            "phase": phase_id,
            "blockingReasons": _unique_strings(reasons),
            "roadmap": roadmap,
            "directory": directory,
        }

    roadmap_data = roadmap.get("data", {})
    directory_data = directory.get("data", {})
    roadmap_number = str(roadmap_data.get("phase_number") or "").strip()
    phase_number = str(directory_data.get("phase_number") or "").strip()
    raw_directory = directory_data.get("directory")
    if not phase_number or not SAFE_GSD_PHASE_NUMBER.fullmatch(phase_number) or len(phase_number) > 64:
        return _uat_resolution_error(phase_id, "invalid_phase_number")
    if roadmap_number and roadmap_number != phase_number:
        return _uat_resolution_error(phase_id, "phase_number_mismatch")
    if not isinstance(raw_directory, str):
        return _uat_resolution_error(phase_id, "phase_directory_missing")

    relative = PurePosixPath(raw_directory)
    if (
        relative.is_absolute()
        or tuple(relative.parts[:2]) != (".planning", "phases")
        or len(relative.parts) != 3
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        return _uat_resolution_error(phase_id, "phase_directory_outside_canonical_root")
    directory_name = relative.parts[-1]
    if not SAFE_GSD_PHASE_DIRECTORY.fullmatch(directory_name) or len(directory_name) > 128:
        return _uat_resolution_error(phase_id, "invalid_phase_directory")
    if directory_name != phase_number and not directory_name.startswith(f"{phase_number}-"):
        return _uat_resolution_error(phase_id, "phase_directory_number_mismatch")

    phase_root = repo / ".planning" / "phases"
    phase_directory = repo.joinpath(*relative.parts)
    for component in (repo / ".planning", phase_root, phase_directory):
        if component.is_symlink():
            return _uat_resolution_error(phase_id, "phase_directory_symlink")
    if not phase_directory.is_dir():
        return _uat_resolution_error(phase_id, "phase_directory_missing")
    try:
        phase_directory.resolve().relative_to(phase_root.resolve())
    except ValueError:
        return _uat_resolution_error(phase_id, "phase_directory_outside_canonical_root")

    artifact = phase_directory / f"{phase_number}-UAT.md"
    if artifact.is_symlink():
        return _uat_resolution_error(phase_id, "uat_artifact_symlink")
    try:
        artifact.resolve().relative_to(phase_directory.resolve())
    except ValueError:
        return _uat_resolution_error(phase_id, "uat_artifact_outside_phase_directory")
    return {
        "ok": True,
        "status": "resolved",
        "reason": "",
        "phase": phase_id,
        "canonicalPhaseId": directory_name,
        "phaseNumber": phase_number,
        "phaseDirectory": relative.as_posix(),
        "relativePath": artifact.relative_to(repo).as_posix(),
        "path": str(artifact.resolve()),
        "exists": artifact.is_file(),
        "roadmap": roadmap,
        "directory": directory,
    }


def validate_roadmap_bindings(
    repo: Path,
    bindings: Mapping[str, Any],
    roadmap_provider: str,
    *,
    adapter: GsdReadOnlyAdapter | None = None,
) -> dict[str, Any]:
    """Validate binding schema and references without modifying configuration."""

    repo = Path(repo).resolve()
    if roadmap_provider not in {"none", "gsd"}:
        return _binding_report({}, "invalid_schema", ["invalid_roadmap_provider"])
    if not isinstance(bindings, Mapping):
        return _binding_report({}, "invalid_schema", ["roadmap_bindings_must_be_an_object"])

    checked: dict[str, dict[str, Any]] = {}
    schema_errors: list[str] = []
    blocking: list[str] = []
    selected_adapter = adapter or (GsdReadOnlyAdapter(repo) if roadmap_provider == "gsd" else None)

    for change_id, value in bindings.items():
        change_key = str(change_id)
        if not change_key or not isinstance(value, Mapping):
            schema_errors.append(f"invalid_binding:{change_key or '<empty>'}")
            continue
        phase_id = value.get("phase_id")
        milestone = value.get("milestone")
        configured_status = value.get("status")
        errors: list[str] = []
        if not SAFE_CHANGE_ID.fullmatch(change_key):
            errors.append("invalid_change_id")
        if not isinstance(phase_id, str) or not phase_id.strip():
            errors.append("phase_id_required")
        if not isinstance(milestone, str) or not milestone.strip():
            errors.append("milestone_required")
        if configured_status not in VALID_BINDING_STATUSES:
            errors.append("invalid_status")
        if errors:
            schema_errors.extend(
                error if error == "invalid_change_id" else f"{change_key}:{error}"
                for error in errors
            )
            checked[change_key] = {
                "configuredStatus": configured_status,
                "effectiveStatus": "invalid",
                "errors": errors,
            }
            continue

        change_location = _openspec_change_location(repo, change_key)
        if change_location is None:
            blocking.append("missing_openspec_change")
            errors.append("missing_openspec_change")

        effective_status = configured_status
        if roadmap_provider == "none" and configured_status != "archived":
            effective_status = "inactive"

        phase_checks: dict[str, Any] = {}
        if roadmap_provider == "gsd" and configured_status == "active" and selected_adapter is not None:
            roadmap_result = selected_adapter.roadmap_get_phase(phase_id)
            directory_result = selected_adapter.find_phase(phase_id)
            phase_checks = {"roadmap": roadmap_result, "directory": directory_result}
            if not (
                roadmap_result.get("ok")
                and directory_result.get("ok")
                and _phase_found(roadmap_result)
                and _phase_found(directory_result)
            ):
                blocking.append("unresolved_gsd_phase")
                errors.append("unresolved_gsd_phase")

        checked[change_key] = {
            "phaseId": phase_id,
            "milestone": milestone,
            "configuredStatus": configured_status,
            "effectiveStatus": effective_status,
            "changePath": str(change_location) if change_location else None,
            "phaseChecks": phase_checks,
            "errors": errors,
        }

    if schema_errors:
        return _binding_report(checked, "invalid_schema", [*schema_errors, *blocking])
    if blocking:
        return _binding_report(checked, "manual_review_required", blocking)
    return _binding_report(checked, "ready", [])


def archive_roadmap_binding(
    bindings: Mapping[str, Any],
    change_id: str,
    *,
    openspec_verified: bool,
    openspec_archived: bool,
    gsd_verified: bool,
) -> dict[str, Any]:
    """Return an archived copy only after all explicit lifecycle gates pass."""

    updated = copy.deepcopy(dict(bindings))
    binding = updated.get(change_id)
    if not isinstance(binding, dict):
        return {
            "applied": False,
            "status": "manual_review_required",
            "bindings": updated,
            "missingGates": [],
            "reason": "binding_missing",
        }
    if binding.get("status") == "archived":
        return {
            "applied": False,
            "status": "already_archived",
            "bindings": updated,
            "missingGates": [],
            "reason": "",
        }

    gates = {
        "openspec_verification": openspec_verified,
        "openspec_archive": openspec_archived,
        "gsd_verification": gsd_verified,
    }
    missing = [name for name, passed in gates.items() if passed is not True]
    if missing:
        return {
            "applied": False,
            "status": "blocked",
            "bindings": updated,
            "missingGates": missing,
            "reason": "archive_gates_incomplete",
        }
    binding["status"] = "archived"
    return {
        "applied": True,
        "status": "archived",
        "bindings": updated,
        "missingGates": [],
        "reason": "",
    }


def archive_binding_gate_status(
    repo: Path,
    change_id: str,
    binding: Mapping[str, Any],
    *,
    adapter: GsdReadOnlyAdapter | None = None,
) -> dict[str, Any]:
    """Derive lifecycle gates from canonical artifacts, never CLI booleans."""

    repo = Path(repo).resolve()
    state = parse_state(repo)
    state_gates = state.get("gates", {}) if isinstance(state.get("gates"), Mapping) else {}
    current_change = (
        state.get("current_change", {})
        if isinstance(state.get("current_change"), Mapping)
        else {}
    )
    openspec_verified = (
        current_change.get("id") == change_id
        and state_gates.get("verification_passed") is True
    )
    openspec_archived = (
        not (repo / "openspec" / "changes" / change_id).exists()
        and _openspec_change_archive_location(repo, change_id) is not None
    )

    phase_id = str(binding.get("phase_id") or "")
    state_matches = (
        state_gates.get("gsd_verification_passed") is True
        and str(state_gates.get("gsd_verification_change")) == change_id
        and str(state_gates.get("gsd_verification_phase")) == phase_id
    )
    # Late import avoids a module cycle while keeping the evidence producer and
    # verifier in workflow_verification.
    from workflow_verification import gsd_verification_status

    evidence = gsd_verification_status(
        repo,
        change=change_id,
        phase=phase_id,
        adapter=adapter,
    )
    gsd_verified = state_matches and evidence.get("verified") is True
    return {
        "openspec_verified": openspec_verified,
        "openspec_archived": openspec_archived,
        "gsd_verified": gsd_verified,
        "stateMatches": state_matches,
        "gsdEvidence": evidence,
        "openspecArchivePath": (
            str(_openspec_change_archive_location(repo, change_id))
            if openspec_archived
            else None
        ),
    }


def persist_archived_roadmap_binding(
    repo: Path,
    change_id: str,
    *,
    apply: bool = False,
    authorized: bool = False,
    adapter: GsdReadOnlyAdapter | None = None,
) -> dict[str, Any]:
    """Atomically archive one binding after derived gates and central policy.

    The default is a read-only plan. Mutation requires both ``apply`` and an
    explicit authorization that satisfies the central ``canonical.write`` and
    ``archive_release`` policies.
    """

    repo = Path(repo).resolve()
    if not SAFE_CHANGE_ID.fullmatch(change_id):
        return _binding_persistence_error("invalid_change_id")
    config_path = repo / ".dev-flow.json"
    if config_path.is_symlink():
        return _binding_persistence_error("config_symlink")
    try:
        original = config_path.read_text()
        loaded = json.loads(original)
    except FileNotFoundError:
        return _binding_persistence_error("config_missing")
    except (OSError, json.JSONDecodeError):
        return _binding_persistence_error("config_invalid")
    if not isinstance(loaded, dict):
        return _binding_persistence_error("config_invalid")
    workflow = loaded.get("workflow")
    if not isinstance(workflow, dict) or workflow.get("roadmap_provider") != "gsd":
        return _binding_persistence_error("gsd_not_selected")
    bindings = workflow.get("roadmap_bindings")
    if not isinstance(bindings, Mapping):
        return _binding_persistence_error("roadmap_bindings_invalid")
    binding = bindings.get(change_id)
    if not isinstance(binding, Mapping):
        return _binding_persistence_error("binding_missing")
    if binding.get("status") == "archived":
        return {
            "ok": True,
            "status": "already_archived",
            "changed": False,
            "path": str(config_path),
            "missingGates": [],
            "sideEffects": [],
        }

    gates = archive_binding_gate_status(repo, change_id, binding, adapter=adapter)
    archived = archive_roadmap_binding(
        bindings,
        change_id,
        openspec_verified=gates["openspec_verified"],
        openspec_archived=gates["openspec_archived"],
        gsd_verified=gates["gsd_verified"],
    )
    if not archived["applied"]:
        return {
            "ok": False,
            "status": archived["status"],
            "changed": False,
            "path": str(config_path),
            "missingGates": archived["missingGates"],
            "reason": archived["reason"],
            "gates": gates,
            "sideEffects": [],
        }

    grants = (
        {"approved_promoter_write_set", "verified_and_explicit_user_request"}
        if authorized
        else set()
    )
    effects = [
        side_effect_decision(default_plugin_root(), "canonical.write", grants),
        side_effect_decision(default_plugin_root(), "archive_release", grants),
    ]
    if not apply:
        return {
            "ok": True,
            "status": "planned",
            "changed": False,
            "path": str(config_path),
            "missingGates": [],
            "gates": gates,
            "sideEffects": effects,
            "plannedBindings": archived["bindings"],
        }
    if not authorized or not all(effect["authorized"] for effect in effects):
        return {
            "ok": False,
            "status": "authorization_required",
            "changed": False,
            "path": str(config_path),
            "missingGates": [],
            "gates": gates,
            "sideEffects": effects,
        }

    updated = copy.deepcopy(loaded)
    updated_workflow = dict(updated["workflow"])
    updated_workflow["roadmap_bindings"] = archived["bindings"]
    updated["workflow"] = updated_workflow
    rendered = f"{json.dumps(updated, indent=2, sort_keys=True)}\n"
    if config_path.is_symlink():
        return _binding_persistence_error("config_symlink")
    current = config_path.read_text()
    if current != original:
        return _binding_persistence_error("config_changed_during_operation")
    if current == rendered:
        return {
            "ok": True,
            "status": "already_archived",
            "changed": False,
            "path": str(config_path),
            "missingGates": [],
            "gates": gates,
            "sideEffects": effects,
        }
    atomic_write_text(config_path, rendered)
    return {
        "ok": True,
        "status": "archived",
        "changed": True,
        "path": str(config_path),
        "missingGates": [],
        "gates": gates,
        "sideEffects": effects,
    }


def roadmap_phase_transition_gate(
    bindings: Mapping[str, Any],
    phase_id: str,
    *,
    roadmap_provider: str,
    openspec_verification: Mapping[str, bool],
    gsd_phase_verified: bool,
) -> dict[str, Any]:
    """Block a selected GSD phase transition on active unverified bindings."""

    phase_id = _required_text(phase_id, "phase_id")
    if roadmap_provider == "none":
        return {
            "ready": True,
            "status": "roadmap_provider_inactive",
            "activeBindings": [],
            "unverifiedChanges": [],
            "blockingReasons": [],
        }
    if roadmap_provider != "gsd":
        return {
            "ready": False,
            "status": "invalid_schema",
            "activeBindings": [],
            "unverifiedChanges": [],
            "blockingReasons": ["invalid_roadmap_provider"],
        }

    active = sorted(
        str(change_id)
        for change_id, binding in bindings.items()
        if isinstance(binding, Mapping)
        and binding.get("status") == "active"
        and binding.get("phase_id") == phase_id
    )
    unverified = [change_id for change_id in active if openspec_verification.get(change_id) is not True]
    blocking = [f"openspec_verification:{change_id}" for change_id in unverified]
    if gsd_phase_verified is not True:
        blocking.append("gsd_phase_verification")
    return {
        "ready": not blocking,
        "status": "ready" if not blocking else "blocked",
        "activeBindings": active,
        "unverifiedChanges": unverified,
        "blockingReasons": blocking,
    }


def planning_tracking_report(
    repo: Path,
    required_paths: Iterable[str | Path],
    *,
    roadmap_provider: str,
    commit_docs: bool,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    """Report Git coverage separately from canonical artifact ownership."""

    repo = Path(repo).resolve()
    normalized = _expanded_tracking_paths(repo, required_paths)
    tracked: list[str] = []
    local_only: list[str] = []
    ignored: list[str] = []
    untracked: list[str] = []
    missing: list[str] = []

    git_available = _inside_git_worktree(repo, runner)
    for relative in normalized:
        path = repo / PurePosixPath(relative)
        if not path.exists():
            missing.append(relative)
            local_only.append(relative)
            continue
        if git_available and _git_has_tracked_path(repo, relative, runner):
            tracked.append(relative)
            continue
        local_only.append(relative)
        if git_available and _git_ignored(repo, relative, runner):
            ignored.append(relative)
        else:
            untracked.append(relative)

    if not local_only:
        status = "tracked"
    elif tracked:
        status = "partially_tracked"
    else:
        status = "local_only"

    commit_gate = roadmap_provider == "gsd" and commit_docs is True
    roadmap_ready = not commit_gate or status == "tracked"
    residual_risk = ""
    if status != "tracked":
        residual_risk = (
            "provider planning artifacts are not fully recoverable or shareable through Git"
        )
    return {
        "status": status,
        "trackedPaths": tracked,
        "localOnlyPaths": local_only,
        "ignoredPaths": ignored,
        "untrackedPaths": untracked,
        "missingPaths": missing,
        "gitAvailable": git_available,
        "commitDocs": bool(commit_docs),
        "commitDocsRequired": commit_gate,
        "roadmapReady": roadmap_ready,
        "advisory": status != "tracked" and not commit_gate,
        "blockingReason": "gsd_commit_docs_not_tracked" if not roadmap_ready else "",
        "residualRisk": residual_risk,
    }


def _binding_report(
    bindings: dict[str, dict[str, Any]],
    status: str,
    blocking: Iterable[str],
) -> dict[str, Any]:
    reasons = _unique_strings(blocking)
    return {
        "ready": status == "ready",
        "status": status,
        "bindings": bindings,
        "blockingReasons": reasons,
    }


def _uat_resolution_error(phase_id: str, reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "status": "manual_review_required",
        "reason": reason,
        "phase": phase_id,
        "blockingReasons": [reason],
    }


def _binding_persistence_error(reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "status": "manual_review_required",
        "changed": False,
        "reason": reason,
        "missingGates": [],
        "sideEffects": [],
    }


def _adapter_error(
    command: Sequence[str],
    reason: str,
    message: str,
    *,
    exit_code: int | None = None,
    error: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "status": "manual_review_required",
        "reason": reason,
        "message": message,
        "command": list(command),
        "exitCode": exit_code,
        "error": dict(error or {}),
    }


def _phase_found(result: Mapping[str, Any]) -> bool:
    data = result.get("data", {})
    return isinstance(data, Mapping) and data.get("found") is True


def _commit_docs(payload: Mapping[str, Any]) -> bool | None:
    config = payload.get("config", {})
    if not isinstance(config, Mapping):
        return None
    if isinstance(config.get("commit_docs"), bool):
        return bool(config["commit_docs"])
    planning = config.get("planning", {})
    if isinstance(planning, Mapping) and isinstance(planning.get("commit_docs"), bool):
        return bool(planning["commit_docs"])
    return None


def _openspec_change_location(repo: Path, change_id: str) -> Path | None:
    if not SAFE_CHANGE_ID.fullmatch(change_id):
        return None
    active = repo / "openspec" / "changes" / change_id
    if active.is_dir():
        return active
    return _openspec_change_archive_location(repo, change_id)


def _openspec_change_archive_location(repo: Path, change_id: str) -> Path | None:
    if not SAFE_CHANGE_ID.fullmatch(change_id):
        return None
    archive = repo / "openspec" / "changes" / "archive"
    if archive.is_dir():
        matches = sorted(path for path in archive.glob(f"*-{change_id}") if path.is_dir())
        if len(matches) == 1:
            return matches[0]
    return None


def _is_gsd_project(text: str) -> bool:
    headings = {match.group(1).strip().casefold() for match in re.finditer(r"(?m)^##\s+(.+?)\s*$", text)}
    return {"what this is", "core value", "requirements", "key decisions"}.issubset(headings)


def _is_gsd_config(data: Any) -> bool:
    if not isinstance(data, Mapping):
        return False
    planning = data.get("planning")
    gates = data.get("gates")
    if not isinstance(planning, Mapping) or not isinstance(gates, Mapping):
        return False
    planning_markers = {"commit_docs", "search_gitignored", "sub_repos"}
    gate_markers = {"confirm_project", "confirm_phases", "confirm_roadmap", "confirm_plan"}
    return bool(planning_markers.intersection(planning)) and bool(gate_markers.intersection(gates))


def _is_legacy_devflow_roadmap(text: str) -> bool:
    markers = ("Project mode:", "## Current Phase", "## Next Milestones")
    return bool(text) and all(marker in text for marker in markers)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(errors="ignore") if path.is_file() else ""
    except OSError:
        return ""


def _read_json(path: Path) -> Any:
    text = _read_text(path)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _evidence(marker: str, path: Path, repo: Path) -> str:
    return f"{marker}:{path.relative_to(repo).as_posix()}"


def _required_text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _unique_strings(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _safe_relative_path(value: str | Path) -> str:
    path = PurePosixPath(Path(value).as_posix())
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"required planning path must be repository-relative: {value}")
    return path.as_posix()


def _expanded_tracking_paths(repo: Path, required_paths: Iterable[str | Path]) -> list[str]:
    expanded: list[str] = []
    for value in required_paths:
        relative = _safe_relative_path(value)
        path = repo / PurePosixPath(relative)
        if not path.is_symlink() and path.is_dir():
            files = [
                child.relative_to(repo).as_posix()
                for child in sorted(path.rglob("*"), key=lambda item: item.as_posix())
                if child.is_file() or child.is_symlink()
            ]
            expanded.extend(files or [relative])
        else:
            expanded.append(relative)
    return _unique_strings(expanded)


def _inside_git_worktree(repo: Path, runner: Runner) -> bool:
    try:
        result = runner(
            ["git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return False
    return result.returncode == 0 and (result.stdout or "").strip() == "true"


def _git_has_tracked_path(repo: Path, relative: str, runner: Runner) -> bool:
    result = runner(
        ["git", "-C", str(repo), "ls-files", "--", relative],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and bool((result.stdout or "").strip())


def _git_ignored(repo: Path, relative: str, runner: Runner) -> bool:
    result = runner(
        ["git", "-C", str(repo), "check-ignore", "-q", "--", relative],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0
