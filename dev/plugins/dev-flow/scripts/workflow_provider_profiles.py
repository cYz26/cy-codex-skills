from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable

from workflow_dependency_plugin_checks import (
    find_plugin_roots,
    read_json,
    session_start_hook_present,
    session_start_hook_trusted,
    source_channel_for_root,
)
from workflow_provider_activation import provider_activation_plan
from workflow_dependency_provenance import load_dependency_provenance
from workflow_dependency_catalog import PROJECT_ORCHESTRATOR_SKILLS
from workflow_mode_routing import validate_devflow_config
from workflow_provider_registry import load_provider_registry as _load_provider_registry
from workflow_roadmap_provider import (
    GSD_RUNTIME,
    GsdReadOnlyAdapter,
    infer_roadmap_ownership,
    planning_tracking_report,
    validate_roadmap_bindings,
)


def plugin_root() -> Path:
    configured = os.environ.get("DEVFLOW_PLUGIN_ROOT") or os.environ.get("PLUGIN_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[1]


def load_provider_registry(root: Path | None = None) -> dict[str, Any]:
    return _load_provider_registry(root or plugin_root())


def resolve_provider_selection(
    repo: Path,
    codex_home: Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    repo = Path(repo).resolve()
    codex_home = Path(codex_home).resolve()
    registry = load_provider_registry()
    project_config, config_error = read_project_config(repo)
    workflow = project_config.get("workflow", {}) if isinstance(project_config.get("workflow"), dict) else {}
    profile = first_value(
        workflow,
        project_config,
        names=("methodology_profile", "methodologyProfile"),
    )
    roadmap = first_value(
        workflow,
        project_config,
        names=("roadmap_provider", "roadmapProvider"),
    )
    selectors = first_mapping(workflow, project_config, names=("provider_selectors", "providerSelectors"))
    bindings = first_mapping(workflow, project_config, names=("roadmap_bindings", "roadmapBindings"))
    provider_lock, lock_error = read_provider_lock(repo)
    source = "explicit_config" if profile or roadmap else "default"
    inference_evidence: list[str] = []
    inference_errors: list[str] = []
    methodology_confidence = "explicit" if profile else "none"
    roadmap_confidence = "explicit" if roadmap else "none"
    if not profile:
        profile_inference = infer_methodology_selection(repo, codex_home)
        profile = profile_inference["profile"]
        profile_evidence = list(profile_inference["evidence"])
        methodology_confidence = str(profile_inference["confidence"])
        inference_evidence.extend(profile_evidence)
        if profile_inference["status"] == "manual_review_required":
            source = "legacy_inference_conflict"
            inference_errors.extend(str(item) for item in profile_inference["conflicts"])
        elif profile_evidence:
            source = "legacy_profile_inferred"
    if not roadmap:
        roadmap_inference = infer_legacy_roadmap_selection(repo)
        roadmap = roadmap_inference.get("provider") or registry["defaults"]["roadmapProvider"]
        roadmap_confidence = str(roadmap_inference.get("confidence") or "none")
        roadmap_evidence = list(roadmap_inference.get("evidence", []))
        inference_evidence.extend(roadmap_evidence)
        if roadmap_inference.get("status") == "manual_review_required":
            source = "legacy_inference_conflict"
            inference_errors.extend(str(item) for item in roadmap_inference.get("conflicts", []))
        elif roadmap_evidence:
            source = "legacy_profile_inferred"
    profile = str(profile or registry["defaults"]["methodologyProfile"])
    roadmap = str(roadmap or registry["defaults"]["roadmapProvider"])
    errors = list(inference_errors)
    if config_error:
        errors.append(config_error)
    if lock_error:
        errors.append(lock_error)
    if profile not in registry["methodologyProfiles"]:
        errors.append(f"unknown methodology profile: {profile}")
    if roadmap not in registry["roadmapProviders"]:
        errors.append(f"unknown roadmap provider: {roadmap}")
    return {
        "explicitMethodologyProfile": first_value(
            workflow,
            project_config,
            names=("methodology_profile", "methodologyProfile"),
        ),
        "effectiveMethodologyProfile": profile,
        "explicitRoadmapProvider": first_value(
            workflow,
            project_config,
            names=("roadmap_provider", "roadmapProvider"),
        ),
        "effectiveRoadmapProvider": roadmap,
        "selectionSource": source,
        "inferenceEvidence": inference_evidence,
        "inferenceConfidence": {
            "methodology": methodology_confidence,
            "roadmap": roadmap_confidence,
        },
        "migrationRecommended": source in {"legacy_profile_inferred", "legacy_inference_conflict"},
        "providerSelectors": selectors,
        "roadmapBindings": bindings,
        "providerLock": provider_lock,
        "configPath": str(repo / ".dev-flow.json"),
        "configErrors": errors,
        "repo": str(repo),
        "codexHome": str(codex_home),
    }


def diagnose_provider_selection(
    selection: dict[str, Any],
    repo: Path,
    codex_home: Path,
    triggered_capabilities: Iterable[str] | None = None,
    trusted_install_receipts: dict[str, Any] | None = None,
    core_plugin_root: Path | None = None,
) -> dict[str, Any]:
    repo = Path(repo).resolve()
    codex_home = Path(codex_home).resolve()
    registry = load_provider_registry()
    profile = selection["effectiveMethodologyProfile"]
    roadmap = selection["effectiveRoadmapProvider"]
    triggered = set(triggered_capabilities or [])
    providers: dict[str, Any] = {}
    selected: list[str] = []
    blocking = list(selection.get("configErrors", []))
    unknown_capabilities = sorted(triggered - set(registry["capabilities"]))
    blocking.extend(f"unknown capability: {item}" for item in unknown_capabilities)

    superpowers = diagnose_superpowers(selection, codex_home, selected=profile == "strict-superpowers")
    providers["superpowers"] = superpowers
    matt = diagnose_matt(
        selection,
        repo,
        codex_home,
        selected=profile == "lean-matt",
        registry=registry,
    )
    providers["mattpocock-skills"] = matt
    gsd = diagnose_gsd(
        repo,
        selected=roadmap == "gsd",
        registry=registry,
        bindings=selection.get("roadmapBindings", {}),
        selector=selection.get("providerSelectors", {}).get("gsd", {}),
        lock=selection.get("providerLock", {}).get("providers", {}).get("gsd", {}),
        install_receipt=(trusted_install_receipts or {}).get("gsd"),
    )
    providers["gsd"] = gsd

    resolved_core_plugin_root = Path(core_plugin_root or plugin_root()).resolve()
    core_project_skills = diagnose_core_project_skills(repo, resolved_core_plugin_root)

    methodology_ready = True
    if profile == "strict-superpowers":
        selected.append("superpowers")
        methodology_ready = superpowers["ready"]
        if not methodology_ready:
            blocking.append(f"superpowers: {superpowers['status']}")
    elif profile == "lean-matt":
        selected.append("mattpocock-skills")
        methodology_ready = matt["ready"]
        if not methodology_ready:
            blocking.append(f"mattpocock-skills: {matt['status']}")
    if roadmap == "gsd":
        selected.append("gsd")
        roadmap_ready = gsd["ready"]
        if not roadmap_ready:
            blocking.append(f"gsd: {gsd['status']}")
    else:
        roadmap_ready = True

    core_ready = bool(
        (repo / "openspec" / "config.yaml").is_file()
        and not selection.get("configErrors")
        and core_project_skills["ready"]
    )
    if not core_ready:
        if not (repo / "openspec" / "config.yaml").is_file():
            blocking.append("core: openspec project configuration missing")
        if selection.get("configErrors"):
            blocking.append("core: provider config invalid")
        if not core_project_skills["ready"]:
            blocking.append(f"core: project skill routing {core_project_skills['status']}")
    capabilities = diagnose_capabilities(
        registry,
        profile,
        roadmap,
        providers,
        repo,
        codex_home,
        triggered,
        core_project_skills,
    )
    unavailable_triggered = [
        capability_id
        for capability_id, capability in capabilities.items()
        if capability.get("triggered") and not capability.get("ready")
    ]
    unavailable_methodology = [
        capability_id
        for capability_id in unavailable_triggered
        if capabilities[capability_id].get("provider")
        in {"superpowers", "mattpocock-skills", "devflow-native"}
        and capability_id not in {"goal-definition", "roadmap-lifecycle"}
    ]
    methodology_ready = methodology_ready and not unavailable_methodology
    blocking.extend(f"capability unavailable: {capability_id}" for capability_id in unavailable_triggered)
    return {
        "ok": (
            core_ready
            and methodology_ready
            and roadmap_ready
            and not unavailable_triggered
            and not unknown_capabilities
        ),
        "selection": selection,
        "corePluginRoot": str(resolved_core_plugin_root),
        "coreReady": core_ready,
        "coreProjectSkills": core_project_skills,
        "methodologyReady": methodology_ready,
        "roadmapReady": roadmap_ready,
        "goalReady": capabilities["goal-definition"]["ready"],
        "selectedProviders": selected,
        "providers": providers,
        "capabilities": capabilities,
        "blockingReasons": blocking,
    }


def diagnose_superpowers(
    selection: dict[str, Any],
    codex_home: Path,
    *,
    selected: bool,
) -> dict[str, Any]:
    roots = find_plugin_roots(codex_home, "superpowers")
    candidates = [superpowers_candidate(codex_home, root) for root in roots]
    if not selected:
        return unselected_provider(candidates)
    selector = selection.get("providerSelectors", {}).get("superpowers", {})
    lock = selection.get("providerLock", {}).get("providers", {}).get("superpowers", {})
    required = load_provider_registry()["methodologyProfiles"]["strict-superpowers"]["requiredSkills"]
    conditional = load_provider_registry()["methodologyProfiles"]["strict-superpowers"]["conditionalSkills"]
    trusted_sources = trusted_provider_sources("superpowers")
    if selector:
        bound_source = matching_superpowers_source(selector, trusted_sources)
        if bound_source is None:
            return provider_result("source_mismatch", False, candidates=candidates)
        identity_candidates = filter_superpowers_candidates(candidates, selector)
        selection_source = "explicit_selector"
    elif lock:
        bound_source = matching_superpowers_source(lock, trusted_sources)
        if bound_source is None:
            return provider_result("stale_lock", False, candidates=candidates)
        identity_candidates = filter_superpowers_candidates(candidates, lock)
        selection_source = "matching_lock"
        if not identity_candidates:
            return provider_result("stale_lock", False, candidates=candidates)
    else:
        bound_source = None
        identity_candidates = candidates
        selection_source = "unique_discovery"
    compatible: list[dict[str, Any]] = []
    source_by_root: dict[str, dict[str, Any]] = {}
    for candidate in identity_candidates:
        matched = bound_source or matching_superpowers_source(candidate, trusted_sources)
        if matched and superpowers_candidate_hashes_match(candidate, matched, required):
            compatible.append(candidate)
            source_by_root[candidate["root"]] = matched
    if not compatible:
        status = "source_drift" if identity_candidates else "missing"
        return provider_result(status, False, candidates=candidates)
    if len(compatible) > 1:
        return provider_result("ambiguous_source", False, candidates=compatible)
    candidate = compatible[0]
    root = Path(candidate["root"])
    trusted_source = source_by_root[candidate["root"]]
    mapped_skills = [*required, *conditional]
    skills = {skill: (root / "skills" / skill / "SKILL.md").exists() for skill in mapped_skills}
    skill_paths = {skill: str(root / "skills" / skill / "SKILL.md") for skill in mapped_skills}
    missing = [skill for skill in required if not skills[skill]]
    missing_conditional = [skill for skill in conditional if not skills[skill]]
    current_hashes = {
        skill: file_digest(root / "skills" / skill / "SKILL.md")
        for skill, present in skills.items()
        if present
    }
    authoritative_hashes = trusted_source.get("skillHashes", {})
    expected_hashes = lock.get("skillHashes", {}) if isinstance(lock, dict) else {}
    lock_invalid = bool(lock) and (
        not set(required).issubset(expected_hashes)
        or any(authoritative_hashes.get(skill) != digest for skill, digest in expected_hashes.items())
    )
    drifted = sorted(
        skill
        for skill, expected in authoritative_hashes.items()
        if skill in required and current_hashes.get(skill) != expected
    )
    drifted_conditional = sorted(
        skill
        for skill in conditional
        if skills.get(skill) and current_hashes.get(skill) != authoritative_hashes.get(skill)
    )
    skill_integrity = {
        skill: bool(skills.get(skill)) and current_hashes.get(skill) == authoritative_hashes.get(skill)
        for skill in mapped_skills
    }
    manifest = read_json(root / ".codex-plugin" / "plugin.json")
    hook_policy_valid = superpowers_hook_policy_valid(root, manifest, trusted_source)
    hook_declared = trusted_source.get("hookPolicy", {}).get("mode") == "session-start"
    hook_present = session_start_hook_present(root, manifest) if hook_declared else False
    hook_trusted = session_start_hook_trusted(codex_home, root) if hook_declared and hook_present else False
    if lock_invalid:
        status = "stale_lock"
        ready = False
    elif not hook_policy_valid:
        status = "source_drift"
        ready = False
    elif missing:
        status = "missing_capabilities"
        ready = False
    elif drifted:
        status = "source_drift"
        ready = False
    elif hook_declared and not hook_present:
        status = "hook_missing_when_declared"
        ready = False
    elif hook_declared and not hook_trusted:
        status = "hook_untrusted_when_declared"
        ready = False
    else:
        status = "ready"
        ready = True
    return {
        **provider_result(status, ready, candidates=compatible),
        **candidate,
        "skills": skills,
        "skillIntegrity": skill_integrity,
        "skillPaths": skill_paths,
        "skillHashes": current_hashes,
        "driftedSkills": drifted,
        "driftedConditionalSkills": drifted_conditional,
        "missingSkills": missing,
        "missingConditionalSkills": missing_conditional,
        "hookDeclared": hook_declared,
        "hookPresent": hook_present,
        "hookTrusted": hook_trusted,
        "hookPolicyValid": hook_policy_valid,
        "selectionSource": selection_source,
        "sourceIdentity": source_identity(trusted_source),
    }


def diagnose_matt(
    selection: dict[str, Any],
    repo: Path,
    codex_home: Path,
    *,
    selected: bool,
    registry: dict[str, Any],
) -> dict[str, Any]:
    profile = registry["methodologyProfiles"]["lean-matt"]
    implicit = list(profile["implicitSkills"])
    root = Path(repo).resolve() / ".agents" / "skills"
    global_root = (Path(codex_home).resolve() / "skills").resolve()
    available = {skill: (root / skill / "SKILL.md").exists() for skill in implicit}
    global_available = {
        skill: (global_root / skill / "SKILL.md").exists()
        for skill in implicit
    }
    present = any(available.values()) or any(global_available.values())
    location_details = matt_location_details(
        root,
        global_root,
        available,
        global_available,
    )
    route_details = matt_route_details(root, available)
    if not selected:
        status = "available_unselected" if present else "absent_unselected"
        return {
            **provider_result(status, True),
            **location_details,
            **route_details,
            "implicitSkills": implicit,
            "excludedImplicitSkills": profile["excludedImplicitSkills"],
            "skills": available,
        }
    missing = [skill for skill, exists in available.items() if not exists]
    hashes = skill_hashes(root, implicit)
    selector = selection.get("providerSelectors", {}).get("mattpocock-skills", {})
    lock = selection.get("providerLock", {}).get("providers", {}).get("mattpocock-skills", {})
    trusted_sources = trusted_provider_sources("mattpocock-skills")
    selector_source = matching_trusted_source(selector, trusted_sources) if selector else None
    lock_source = matching_trusted_source(lock, trusted_sources) if lock else None
    if selector and selector_source is None:
        return matt_source_failure(
            "source_mismatch",
            root,
            global_root,
            implicit,
            profile,
            available,
            global_available,
            missing,
            hashes,
            selector,
        )
    if lock and lock_source is None:
        return matt_source_failure(
            "stale_lock",
            root,
            global_root,
            implicit,
            profile,
            available,
            global_available,
            missing,
            hashes,
            selector,
        )
    locked_root = lock.get("sourceRoot") if isinstance(lock, dict) else None
    if locked_root and Path(str(locked_root)).resolve() != root.resolve():
        return matt_source_failure(
            "stale_lock",
            root,
            global_root,
            implicit,
            profile,
            available,
            global_available,
            missing,
            hashes,
            selector,
        )
    if selector_source and lock_source and source_identity(selector_source) != source_identity(lock_source):
        return matt_source_failure(
            "stale_lock",
            root,
            global_root,
            implicit,
            profile,
            available,
            global_available,
            missing,
            hashes,
            selector,
        )
    trusted_source = selector_source or lock_source
    expected_hashes = trusted_source.get("skillHashes", {}) if trusted_source else {}
    if lock:
        locked_hashes = lock.get("skillHashes", {}) if isinstance(lock, dict) else {}
        if locked_hashes != expected_hashes or set(locked_hashes) != set(implicit):
            return matt_source_failure(
                "stale_lock",
                root,
                global_root,
                implicit,
                profile,
                available,
                global_available,
                missing,
                hashes,
                selector,
                expected_hashes=expected_hashes,
            )
    if not trusted_source and not selector and not lock:
        matching_hash_sources = [
            source
            for source in trusted_sources
            if source.get("skillHashes")
            and all(hashes.get(skill) == expected for skill, expected in source["skillHashes"].items())
        ]
        if len(matching_hash_sources) == 1:
            trusted_source = matching_hash_sources[0]
            expected_hashes = trusted_source["skillHashes"]
        elif len(matching_hash_sources) > 1:
            return matt_source_failure(
                "ambiguous_source",
                root,
                global_root,
                implicit,
                profile,
                available,
                global_available,
                missing,
                hashes,
                selector,
            )
        elif not missing:
            return matt_source_failure(
                "unverifiable_source",
                root,
                global_root,
                implicit,
                profile,
                available,
                global_available,
                missing,
                hashes,
                selector,
            )
    drifted = sorted(
        skill
        for skill, expected in expected_hashes.items()
        if hashes.get(skill) != expected
    )
    nonlocal_skills = route_details["nonLocalSkills"]
    ready = not missing and not drifted and not nonlocal_skills
    status = "ready"
    if missing:
        status = "missing_capabilities"
    elif nonlocal_skills:
        status = "nonlocal_skill_route"
    elif drifted:
        status = "source_drift"
    return {
        **provider_result(status, ready),
        **location_details,
        **route_details,
        "implicitSkills": implicit,
        "excludedImplicitSkills": profile["excludedImplicitSkills"],
        "skills": available,
        "missingSkills": missing,
        "skillHashes": hashes,
        "expectedSkillHashes": expected_hashes,
        "driftedSkills": drifted,
        "selector": selector,
        "sourceIdentity": source_identity(trusted_source or {}),
        "selectionSource": "matching_lock" if lock else ("explicit_selector" if selector else "unique_discovery"),
    }


def diagnose_gsd(
    repo: Path,
    *,
    selected: bool,
    registry: dict[str, Any],
    bindings: dict[str, Any] | None = None,
    selector: dict[str, Any] | None = None,
    lock: dict[str, Any] | None = None,
    install_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profile = registry["roadmapProviders"]["gsd"]
    runtime = repo / ".codex" / "gsd-core" / "bin" / "gsd-tools.cjs"
    skills = {skill: (repo / ".agents" / "skills" / skill / "SKILL.md").exists() for skill in profile["skills"]}
    agents = {agent: (repo / ".codex" / "agents" / agent).exists() for agent in profile["agents"]}
    present = runtime.exists() or any(skills.values()) or any(agents.values())
    if not selected:
        return {
            **provider_result("available_unselected" if present else "absent_unselected", True),
            "runtime": str(runtime),
        }
    base_ready = runtime.exists() and all(skills.values()) and all(agents.values())
    version_path = runtime.parents[1] / "VERSION"
    version = version_path.read_text().strip() if version_path.exists() else "unknown"
    runtime_digest = file_digest(runtime)
    if not base_ready:
        return {
            **provider_result("missing_capabilities", False),
            "runtime": str(runtime),
            "version": version,
            "skills": skills,
            "agents": agents,
            "runtimeDiagnosis": {},
            "bindingDiagnosis": {},
            "tracking": {},
        }

    selector = selector if isinstance(selector, dict) else {}
    lock = lock if isinstance(lock, dict) else {}
    trusted_sources = trusted_provider_sources("gsd")
    expected_source = matching_trusted_source(selector, trusted_sources) if selector else None
    locked_source = matching_trusted_source(lock, trusted_sources) if lock else None
    if selector and expected_source is None:
        return gsd_source_failure(runtime, version, skills, agents, "source_mismatch", runtime_digest)
    if lock and locked_source is None:
        return gsd_source_failure(runtime, version, skills, agents, "stale_lock", runtime_digest)
    source = expected_source or locked_source
    expected_version = str((selector or lock or source or {}).get("version") or "")
    if expected_version and version != expected_version:
        return gsd_source_failure(runtime, version, skills, agents, "source_drift", runtime_digest)
    locked_root = lock.get("sourceRoot") if isinstance(lock, dict) else None
    if locked_root and Path(str(locked_root)).resolve() != runtime.parents[1].resolve():
        return gsd_source_failure(runtime, version, skills, agents, "stale_lock", runtime_digest)
    if not source:
        source = next(
            (candidate for candidate in trusted_sources if str(candidate.get("version")) == version),
            None,
        )
    if source is None:
        return gsd_source_failure(runtime, version, skills, agents, "unverifiable_source", runtime_digest)
    expected_digest = source.get("runtimeSha256")
    locked_digest = lock.get("runtimeSha256") if isinstance(lock, dict) else None
    if not isinstance(expected_digest, str) or len(expected_digest) != 64:
        return gsd_source_failure(runtime, version, skills, agents, "unverifiable_source", runtime_digest)
    if lock and locked_digest != expected_digest:
        return gsd_source_failure(runtime, version, skills, agents, "stale_lock", runtime_digest)
    if runtime_digest != expected_digest:
        return gsd_source_failure(runtime, version, skills, agents, "source_drift", runtime_digest)

    manifest_path = repo / str(source.get("contentManifestPath") or ".codex/gsd-file-manifest.json")
    try:
        content_manifest = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError):
        return gsd_source_failure(
            runtime,
            version,
            skills,
            agents,
            "content_manifest_invalid",
            runtime_digest,
            contentManifest=str(manifest_path),
            sourceIdentity=source_identity(source),
        )
    if not isinstance(content_manifest, dict) or not isinstance(content_manifest.get("files"), dict):
        return gsd_source_failure(
            runtime,
            version,
            skills,
            agents,
            "content_manifest_invalid",
            runtime_digest,
            contentManifest=str(manifest_path),
            sourceIdentity=source_identity(source),
        )
    manifest_files = content_manifest.get("files", {}) if isinstance(content_manifest, dict) else {}
    skill_hash_values = {
        skill: file_digest(repo / ".agents" / "skills" / skill / "SKILL.md")
        for skill in profile["skills"]
    }
    agent_hash_values = {
        agent: file_digest(repo / ".codex" / "agents" / agent)
        for agent in profile["agents"]
    }
    manifest_skill_hashes = {
        skill: manifest_files.get(f"skills/{skill}/SKILL.md")
        for skill in profile["skills"]
    }
    manifest_agent_hashes = {
        agent: manifest_files.get(f"agents/{agent}")
        for agent in profile["agents"]
    }
    content_identity = gsd_content_identity(version, skill_hash_values, agent_hash_values)
    manifest_ready = (
        content_manifest.get("version") == version
        and skill_hash_values == manifest_skill_hashes
        and agent_hash_values == manifest_agent_hashes
        and all(skill_hash_values.values())
        and all(agent_hash_values.values())
    )
    attestation = gsd_content_attestation(source)
    bootstrap_authorized = valid_gsd_install_receipt(install_receipt, source)
    if not lock and not bootstrap_authorized:
        return gsd_source_failure(
            runtime,
            version,
            skills,
            agents,
            "content_lock_required",
            runtime_digest,
            contentManifest=str(manifest_path),
            contentIdentitySha256=content_identity,
            contentManifestSha256=content_identity,
            skillHashes=skill_hash_values,
            agentHashes=agent_hash_values,
            sourceIdentity=source_identity(source),
            bootstrapEligible=bool(manifest_ready),
        )
    lock_content_ready = bootstrap_authorized or (
        lock.get("contentIdentitySha256") == content_identity
        and lock.get("contentManifestSha256") == content_identity
        and lock.get("skillHashes") == skill_hash_values
        and lock.get("agentHashes") == agent_hash_values
        and lock.get("contentAttestation") == attestation
    )
    if not manifest_ready or not lock_content_ready:
        return gsd_source_failure(runtime, version, skills, agents, "content_drift", runtime_digest)

    configured_bindings = bindings if isinstance(bindings, dict) else {}
    active_phase_ids = [
        str(binding.get("phase_id"))
        for binding in configured_bindings.values()
        if isinstance(binding, dict)
        and binding.get("status") == "active"
        and binding.get("phase_id")
    ]
    adapter = GsdReadOnlyAdapter(repo)
    runtime_diagnosis = adapter.diagnose(active_phase_ids)
    binding_diagnosis = validate_roadmap_bindings(
        repo,
        configured_bindings,
        "gsd",
        adapter=adapter,
    )
    tracking = planning_tracking_report(
        repo,
        gsd_owned_paths(repo),
        roadmap_provider="gsd",
        commit_docs=runtime_diagnosis.get("commitDocs") is True,
    )
    ready = runtime_diagnosis["ready"] and binding_diagnosis["ready"] and tracking["roadmapReady"]
    status = "ready"
    if not runtime_diagnosis["ready"]:
        status = runtime_diagnosis["status"]
    elif not binding_diagnosis["ready"]:
        status = binding_diagnosis["status"]
    elif not tracking["roadmapReady"]:
        status = "tracking_contract_unsatisfied"
    return {
        **provider_result(status, ready),
        "runtime": str(runtime),
        "version": version,
        "runtimeSha256": runtime_digest,
        "skills": skills,
        "agents": agents,
        "runtimeDiagnosis": runtime_diagnosis,
        "bindingDiagnosis": binding_diagnosis,
        "tracking": tracking,
        "contentManifest": str(manifest_path),
        "contentIdentitySha256": content_identity,
        "contentManifestSha256": content_identity,
        "contentAttestation": attestation,
        "attestationAuthority": "authorized-pinned-install" if bootstrap_authorized else "provider-lock",
        "skillHashes": skill_hash_values,
        "agentHashes": agent_hash_values,
        "sourceIdentity": source_identity(source),
    }


def gsd_owned_paths(repo: Path) -> list[str]:
    candidates = [
        repo / ".planning" / "STATE.md",
        repo / ".planning" / "PROJECT.md",
        repo / ".planning" / "REQUIREMENTS.md",
        repo / ".planning" / "ROADMAP.md",
        repo / ".planning" / "config.json",
        repo / ".planning" / "phases",
        repo / ".planning" / "milestones",
        repo / ".planning" / "todos",
        repo / ".planning" / "codebase",
    ]
    return [path.relative_to(repo).as_posix() for path in candidates if path.exists()]


def gsd_content_identity(
    version: str,
    skill_hashes: dict[str, str | None],
    agent_hashes: dict[str, str | None],
) -> str:
    files = {
        **{f"skills/{name}/SKILL.md": digest for name, digest in skill_hashes.items()},
        **{f"agents/{name}": digest for name, digest in agent_hashes.items()},
    }
    canonical = json.dumps(
        {"version": version, "files": files},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def gsd_content_attestation(source: dict[str, Any]) -> dict[str, str]:
    command = source.get("installCommand")
    if not isinstance(command, list) or not command or not all(isinstance(item, str) for item in command):
        return {}
    digest = hashlib.sha256(
        json.dumps(command, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "kind": "authorized-pinned-install",
        "sourceId": str(source.get("source_id") or ""),
        "installCommandSha256": digest,
    }


def valid_gsd_install_receipt(receipt: dict[str, Any] | None, source: dict[str, Any]) -> bool:
    return bool(
        isinstance(receipt, dict)
        and receipt.get("ok") is True
        and receipt.get("source_id") == source.get("source_id")
        and receipt.get("command") == source.get("installCommand")
        and gsd_content_attestation(source)
    )


def diagnose_core_project_skills(repo: Path, source_root: Path) -> dict[str, Any]:
    skills = {
        skill: diagnose_bound_project_skill(
            repo / ".agents" / "skills" / skill,
            source_root / "skills" / skill,
            file_digest(source_root / "skills" / skill / "SKILL.md"),
        )
        for skill in PROJECT_ORCHESTRATOR_SKILLS
    }
    statuses = {item["status"] for item in skills.values() if not item["ready"]}
    if not statuses:
        status = "ready"
    elif "source_conflict" in statuses:
        status = "source_conflict"
    elif "source_untrusted" in statuses:
        status = "source_untrusted"
    else:
        status = "missing_capabilities"
    return {
        "ready": not statuses,
        "status": status,
        "sourceRoot": str(source_root / "skills"),
        "skills": skills,
    }


def diagnose_bound_project_skill(
    project_skill_dir: Path,
    source_skill_dir: Path,
    expected_hash: str | None,
) -> dict[str, Any]:
    project_file = project_skill_dir / "SKILL.md"
    source_file = source_skill_dir / "SKILL.md"
    source_hash = file_digest(source_file)
    project_hash = file_digest(project_file)
    base = {
        "projectPath": str(project_file),
        "sourcePath": str(source_file),
        "projectHash": project_hash,
        "sourceHash": source_hash,
        "expectedHash": expected_hash,
    }
    if not source_file.is_file() or not expected_hash or source_hash != expected_hash:
        return {**base, "ready": False, "status": "source_untrusted"}
    if not project_file.is_file():
        return {**base, "ready": False, "status": "missing"}
    symlink_route = any(
        path.is_symlink()
        for path in (
            project_skill_dir.parent.parent,
            project_skill_dir.parent,
            project_skill_dir,
            project_file,
        )
    )
    if symlink_route:
        try:
            route_matches = project_file.resolve() == source_file.resolve()
        except OSError:
            route_matches = False
    else:
        route_matches = project_hash == expected_hash
    if not route_matches or project_hash != expected_hash:
        return {**base, "ready": False, "status": "source_conflict"}
    return {
        **base,
        "ready": True,
        "status": "ready",
        "route": "source_symlink" if symlink_route else "exact_copy",
    }


def diagnose_capabilities(
    registry: dict[str, Any],
    profile: str,
    roadmap: str,
    providers: dict[str, Any],
    repo: Path,
    codex_home: Path,
    triggered: set[str],
    core_project_skills: dict[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    provider_id = registry["methodologyProfiles"].get(profile, {}).get("provider", "invalid")
    selected_provider_ready = (
        core_project_skills["ready"]
        if provider_id == "devflow-native"
        else providers.get(provider_id, {}).get("ready", False)
    )
    for capability_id, contract in registry["capabilities"].items():
        is_triggered = capability_id in triggered
        mapping = list(contract.get(profile, []))
        capability_provider = provider_id
        if profile == "lean-matt" and capability_id in {
            "implementation-planning",
            "completion-proof",
            "execution-orchestration",
        }:
            capability_provider = "devflow-native"
        if profile == "strict-superpowers" and capability_id in {"architecture-guidance", "goal-definition"}:
            capability_provider = "devflow-native" if capability_id == "architecture-guidance" else "define-goal"
        provider_ready = (
            core_project_skills["ready"]
            if capability_provider == "devflow-native"
            else selected_provider_ready
        )
        ready = provider_ready
        status = "ready" if provider_ready else "missing"
        project_skills: dict[str, Any] = {}
        if profile == "strict-superpowers" and capability_provider == "superpowers":
            availability = providers["superpowers"].get("skillIntegrity", {})
            expected_hashes = providers["superpowers"].get("skillHashes", {})
            project_availability = {
                skill: file_digest(repo / ".agents" / "skills" / skill / "SKILL.md")
                == expected_hashes.get(skill)
                for skill in mapping
            }
            if capability_id == "execution-orchestration":
                mapping_ready = any(
                    availability.get(skill, False) and project_availability.get(skill, False)
                    for skill in mapping
                )
            else:
                mapping_ready = all(
                    availability.get(skill, False) and project_availability.get(skill, False)
                    for skill in mapping
                )
            if is_triggered:
                ready = provider_ready and mapping_ready
                status = "ready" if ready else "missing"
        if profile == "lean-matt" and capability_provider == "mattpocock-skills":
            matt_report = providers["mattpocock-skills"]
            expected_hashes = matt_report.get("expectedSkillHashes", {})
            matt_root = Path(
                str(matt_report.get("root") or (repo / ".agents" / "skills"))
            )
            project_skills = {
                skill: diagnose_bound_project_skill(
                    repo / ".agents" / "skills" / skill,
                    matt_root / skill,
                    expected_hashes.get(skill),
                )
                for skill in mapping
            }
            if is_triggered:
                mapping_ready = all(item["ready"] for item in project_skills.values())
                ready = provider_ready and mapping_ready
                status = "ready" if ready else "missing"
        if capability_id == "roadmap-lifecycle":
            capability_provider = roadmap
            ready = roadmap == "none" or providers["gsd"]["ready"]
            status = "not_triggered" if roadmap == "none" and not is_triggered else ("ready" if ready else "missing")
        elif capability_id == "goal-definition":
            available = (codex_home / "skills" / "define-goal" / "SKILL.md").exists()
            ready = available if is_triggered else True
            status = "ready" if is_triggered and available else ("missing" if is_triggered else "not_triggered")
        evidence_satisfied = not is_triggered
        evidence_status = "not_triggered"
        if is_triggered:
            evidence_satisfied = False
            evidence_status = (
                "missing_red_evidence" if capability_id == "test-first-execution" else "missing_canonical_evidence"
            )
        result[capability_id] = {
            "provider": capability_provider,
            "skills": mapping,
            "triggered": is_triggered,
            "ready": ready,
            "status": status,
            "projectSkills": project_skills,
            "evidenceSatisfied": evidence_satisfied,
            "evidenceStatus": evidence_status,
            "nextAction": (
                "Use define-goal."
                if capability_id == "goal-definition" and is_triggered and not ready
                else ""
            ),
        }
    return result


def read_project_config(repo: Path) -> tuple[dict[str, Any], str]:
    path = repo / ".dev-flow.json"
    if not path.exists():
        return {}, ""
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        return {}, f"invalid provider config: {error.msg}"
    if not isinstance(data, dict):
        return {}, "provider config must be a JSON object"
    errors = validate_devflow_config(data)
    return data, "; ".join(errors)


def read_provider_lock(repo: Path) -> tuple[dict[str, Any], str]:
    path = repo / ".planning" / "devflow" / "providers.lock.json"
    if not path.exists():
        return {}, ""
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        return {}, f"invalid provider lock: {error.msg}"
    if not isinstance(data, dict) or not isinstance(data.get("providers", {}), dict):
        return {}, "provider lock must contain a providers object"
    return data, ""


def first_value(*mappings: dict[str, Any], names: tuple[str, ...]) -> Any:
    for mapping in mappings:
        for name in names:
            value = mapping.get(name)
            if value not in (None, ""):
                return value
    return None


def first_mapping(*mappings: dict[str, Any], names: tuple[str, ...]) -> dict[str, Any]:
    value = first_value(*mappings, names=names)
    return dict(value) if isinstance(value, dict) else {}


def infer_methodology_profile(
    repo: Path,
    codex_home: Path | None = None,
) -> tuple[str, list[str]]:
    inference = infer_methodology_selection(repo, codex_home)
    return str(inference["profile"]), list(inference["evidence"])


def infer_methodology_selection(repo: Path, codex_home: Path | None) -> dict[str, Any]:
    repo = Path(repo).resolve()
    root = repo / ".agents" / "skills"
    marker_names = ("brainstorming", "writing-plans", "test-driven-development")
    marker_roots = [root / skill for skill in marker_names]
    present = [path for path in marker_roots if path.exists() or path.is_symlink()]
    evidence = [path.relative_to(repo).as_posix() for path in present]
    if not present:
        return methodology_inference("core", "default", "none", [], [])
    if len(present) != len(marker_roots) or any(not path.is_symlink() for path in marker_roots):
        return methodology_inference(
            "core",
            "manual_review_required",
            "conflicting",
            evidence,
            ["legacy Superpowers markers are partial or are not project-local symlinks"],
        )
    resolved_targets = [path.resolve() for path in marker_roots]
    if any(
        target.name != skill or target.parent.name != "skills" or not (target / "SKILL.md").is_file()
        for target, skill in zip(resolved_targets, marker_names)
    ):
        return methodology_inference(
            "core",
            "manual_review_required",
            "conflicting",
            evidence,
            ["legacy Superpowers links do not resolve to canonical provider skill directories"],
        )
    provider_roots = {target.parent.parent.resolve() for target in resolved_targets}
    if len(provider_roots) != 1 or codex_home is None:
        return methodology_inference(
            "core",
            "manual_review_required",
            "unverified",
            evidence,
            ["legacy Superpowers links do not resolve to one verifiable provider source"],
        )
    provider_root = next(iter(provider_roots))
    candidate = superpowers_candidate(Path(codex_home).resolve(), provider_root)
    trusted_sources = trusted_provider_sources("superpowers")
    source = matching_superpowers_source(candidate, trusted_sources)
    if source is None or not superpowers_candidate_hashes_match(candidate, source, list(marker_names)):
        return methodology_inference(
            "core",
            "manual_review_required",
            "unverified",
            evidence,
            ["legacy Superpowers link target identity or skill hashes are not authoritative"],
        )
    return {
        **methodology_inference(
            "strict-superpowers",
            "legacy_profile_inferred",
            "high",
            evidence,
            [],
        ),
        "sourceIdentity": source_identity(source),
    }


def methodology_inference(
    profile: str,
    status: str,
    confidence: str,
    evidence: list[str],
    conflicts: list[str],
) -> dict[str, Any]:
    return {
        "profile": profile,
        "status": status,
        "confidence": confidence,
        "evidence": evidence,
        "conflicts": conflicts,
        "migrationRecommended": bool(evidence),
    }


def infer_roadmap_provider(repo: Path) -> tuple[str, list[str]]:
    inference = infer_legacy_roadmap_selection(repo)
    return str(inference.get("provider") or "none"), list(inference.get("evidence", []))


def infer_legacy_roadmap_selection(repo: Path) -> dict[str, Any]:
    inference = infer_roadmap_ownership(repo)
    roadmap = Path(repo).resolve() / ".planning" / "ROADMAP.md"
    if inference.get("status") != "no_markers" or not roadmap.is_file() or not roadmap.read_text().strip():
        return inference
    adapter = trusted_gsd_inference_adapter(repo)
    if adapter is not None:
        return infer_roadmap_ownership(repo, adapter=adapter)
    return {
        "provider": None,
        "status": "manual_review_required",
        "confidence": "unverified",
        "evidence": [str(roadmap.relative_to(Path(repo).resolve()))],
        "gsdEvidence": [],
        "devflowEvidence": [],
        "conflicts": [
            "root .planning/ROADMAP.md requires explicit selection or a hash-verified GSD runtime"
        ],
        "migrationRecommended": True,
    }


def trusted_gsd_inference_adapter(repo: Path) -> GsdReadOnlyAdapter | None:
    repo = Path(repo).resolve()
    runtime = repo / GSD_RUNTIME
    version_path = runtime.parents[1] / "VERSION"
    if not runtime.is_file() or not version_path.is_file():
        return None
    version = version_path.read_text().strip()
    matches = [
        source
        for source in trusted_provider_sources("gsd")
        if str(source.get("version")) == version
        and source.get("runtimeSha256") == file_digest(runtime)
    ]
    return GsdReadOnlyAdapter(repo) if len(matches) == 1 else None


def superpowers_candidate(codex_home: Path, root: Path) -> dict[str, Any]:
    manifest_path = root / ".codex-plugin" / "plugin.json"
    manifest = read_json(manifest_path)
    return {
        "root": str(root),
        "pluginId": str(manifest.get("name") or ""),
        "sourceChannel": source_channel_for_root(codex_home, root),
        "version": str(manifest.get("version") or "unknown"),
        "manifestDigest": file_digest(manifest_path),
    }


def matching_superpowers_source(
    binding: dict[str, Any],
    sources: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Resolve exactly one authoritative Superpowers source identity."""
    if not isinstance(binding, dict) or not binding:
        return None
    aliases = {
        "source_id": ("source_id", "sourceId"),
        "source_channel": ("source_channel", "sourceChannel"),
        "plugin_id": ("plugin_id", "pluginId"),
        "version": ("version",),
        "kind": ("kind",),
    }

    def value(key: str) -> Any:
        return next(
            (binding[name] for name in aliases[key] if binding.get(name) not in (None, "")),
            None,
        )

    source_id = value("source_id")
    source_channel = value("source_channel")
    version = value("version")
    if source_id in (None, "") and (source_channel in (None, "") or version in (None, "")):
        return None
    matches = []
    for source in sources:
        if source_id not in (None, "") and str(source.get("source_id")) != str(source_id):
            continue
        if any(
            value(key) not in (None, "")
            and str(source.get(key)) != str(value(key))
            for key in ("source_channel", "plugin_id", "version", "kind")
        ):
            continue
        matches.append(source)
    return matches[0] if len(matches) == 1 else None


def superpowers_candidate_hashes_match(
    candidate: dict[str, Any],
    source: dict[str, Any],
    skills: list[str],
) -> bool:
    expected = source.get("skillHashes", {})
    manifest_digest = source.get("manifestSha256")
    if (
        not isinstance(expected, dict)
        or not set(skills).issubset(expected)
        or not isinstance(manifest_digest, str)
        or candidate.get("manifestDigest") != manifest_digest
    ):
        return False
    root = Path(str(candidate.get("root", "")))
    return all(
        file_digest(root / "skills" / skill / "SKILL.md") == expected.get(skill)
        for skill in skills
    )


def superpowers_hook_policy_valid(
    root: Path,
    manifest: dict[str, Any],
    source: dict[str, Any],
) -> bool:
    policy = source.get("hookPolicy", {})
    if not isinstance(policy, dict):
        return False
    mode = policy.get("mode")
    if mode == "hookless":
        return manifest.get("hooks") in (None, {})
    if mode != "session-start":
        return False
    manifest_path = policy.get("manifestPath")
    if not isinstance(manifest_path, str) or manifest.get("hooks") != manifest_path:
        return False
    file_hashes = policy.get("fileHashes", {})
    return bool(file_hashes) and all(
        isinstance(relative, str)
        and isinstance(expected, str)
        and file_digest(root / relative) == expected
        for relative, expected in file_hashes.items()
    )


def filter_superpowers_candidates(
    candidates: list[dict[str, Any]],
    selector: dict[str, Any],
) -> list[dict[str, Any]]:
    source_channel = selector.get("source_channel") or selector.get("sourceChannel")
    version = selector.get("version")
    manifest_digest = selector.get("manifestDigest") or selector.get("manifest_digest")
    source_root = selector.get("sourceRoot") or selector.get("source_root")
    result = candidates
    if source_channel:
        result = [candidate for candidate in result if candidate["sourceChannel"] == source_channel]
    if version:
        result = [candidate for candidate in result if candidate["version"] == str(version)]
    if manifest_digest:
        result = [candidate for candidate in result if candidate["manifestDigest"] == manifest_digest]
    if source_root:
        resolved = Path(str(source_root)).resolve()
        result = [candidate for candidate in result if Path(candidate["root"]).resolve() == resolved]
    return result


def trusted_provider_sources(provider: str) -> list[dict[str, Any]]:
    records = load_dependency_provenance(plugin_root()).get("providerSources", {})
    return [
        {"source_id": source_id, **record}
        for source_id, record in records.items()
        if isinstance(record, dict) and record.get("provider") == provider
    ]


def matching_trusted_source(
    selector: dict[str, Any],
    sources: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not isinstance(selector, dict) or not selector:
        return None
    source_id = selector.get("source_id")
    if source_id:
        candidate = next((source for source in sources if source.get("source_id") == source_id), None)
        if candidate is None:
            return None
        identity_fields = ("repository", "ref", "commit", "package", "version")
        if any(
            selector.get(key) not in (None, "")
            and str(selector.get(key)) != str(candidate.get(key))
            for key in identity_fields
        ):
            return None
        return candidate
    identity_keys = {
        "mattpocock-skills": ("repository", "ref", "commit"),
        "gsd": ("version",),
    }
    provider = str(sources[0].get("provider")) if sources else ""
    keys = identity_keys.get(provider, ())
    if not keys or not all(selector.get(key) not in (None, "") for key in keys):
        return None
    candidates = [
        source
        for source in sources
        if all(str(source.get(key)) == str(selector.get(key)) for key in keys)
        and (
            selector.get("package") in (None, "")
            or str(source.get("package")) == str(selector.get("package"))
        )
    ]
    return candidates[0] if len(candidates) == 1 else None


def source_identity(source: dict[str, Any]) -> dict[str, Any]:
    return {
        key: source[key]
        for key in (
            "source_id",
            "provider",
            "kind",
            "plugin_id",
            "source_channel",
            "repository",
            "ref",
            "commit",
            "package",
            "version",
        )
        if source.get(key) not in (None, "")
    }


def matt_source_failure(
    status: str,
    root: Path,
    global_root: Path,
    implicit: list[str],
    profile: dict[str, Any],
    available: dict[str, bool],
    global_available: dict[str, bool],
    missing: list[str],
    hashes: dict[str, str],
    selector: dict[str, Any],
    *,
    expected_hashes: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        **provider_result(status, False),
        **matt_location_details(root, global_root, available, global_available),
        **matt_route_details(root, available),
        "implicitSkills": implicit,
        "excludedImplicitSkills": profile["excludedImplicitSkills"],
        "skills": available,
        "missingSkills": missing,
        "skillHashes": hashes,
        "expectedSkillHashes": dict(expected_hashes or {}),
        "driftedSkills": [],
        "selector": selector,
        "selectionSource": "explicit_selector" if selector else "unique_discovery",
    }


def matt_location_details(
    root: Path,
    global_root: Path,
    available: dict[str, bool],
    global_available: dict[str, bool],
) -> dict[str, Any]:
    return {
        "root": str(root),
        "projectPackPresent": any(available.values()),
        "globalRoot": str(global_root),
        "globalSkills": global_available,
        "globalPackPresent": any(global_available.values()),
    }


def matt_route_details(root: Path, available: dict[str, bool]) -> dict[str, Any]:
    declared_root = root.absolute()
    resolved_root = root.resolve()
    project_root_local = declared_root == resolved_root
    local_routes: dict[str, bool] = {}
    for skill, exists in available.items():
        if not exists or not project_root_local:
            local_routes[skill] = False
            continue
        try:
            (root / skill / "SKILL.md").resolve().relative_to(declared_root)
            local_routes[skill] = True
        except (OSError, ValueError):
            local_routes[skill] = False
    return {
        "projectRootLocal": project_root_local,
        "localSkillRoutes": local_routes,
        "nonLocalSkills": sorted(
            skill
            for skill, exists in available.items()
            if exists and not local_routes[skill]
        ),
    }


def gsd_source_failure(
    runtime: Path,
    version: str,
    skills: dict[str, bool],
    agents: dict[str, bool],
    status: str,
    runtime_digest: str | None = None,
    **details: Any,
) -> dict[str, Any]:
    return {
        **provider_result(status, False),
        "runtime": str(runtime),
        "version": version,
        "runtimeSha256": runtime_digest,
        "skills": skills,
        "agents": agents,
        "runtimeDiagnosis": {},
        "bindingDiagnosis": {},
        "tracking": {},
        **details,
    }


def unselected_provider(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    status = "available_unselected" if candidates else "absent_unselected"
    return provider_result(status, True, candidates=candidates)


def provider_result(status: str, ready: bool, *, candidates: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"status": status, "ready": ready, "candidates": list(candidates or [])}


def file_digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def skill_hashes(root: Path, skills: Iterable[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for skill in skills:
        path = root / skill / "SKILL.md"
        if path.exists():
            hashes[skill] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


__all__ = [
    "diagnose_provider_selection",
    "load_provider_registry",
    "provider_activation_plan",
    "resolve_provider_selection",
]
