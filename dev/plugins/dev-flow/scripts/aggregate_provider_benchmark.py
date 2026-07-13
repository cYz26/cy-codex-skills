#!/usr/bin/env python3
"""Aggregate reproducible DevFlow provider evidence with no third-party code."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

from run_provider_benchmark import (
    HIGH_RISK_TASK_IDS,
    PROFILES,
    PROFILE_PROVIDER_IDS,
    PROFILE_SKILLS,
    REQUIRED_RAW_ARTIFACTS,
    REQUIRED_TASK_IDS,
)


EXPECTED_REPETITIONS = (1, 2, 3)
EXPECTED_RUNS_PER_PROFILE = len(REQUIRED_TASK_IDS) * len(EXPECTED_REPETITIONS)
REQUIRED_RAW_CATEGORIES = ("telemetry", "route", "canonical", "side_effects", "source")
THRESHOLDS = {
    "validPairsPerProfile": 30,
    "leanMachineVerifierPasses": 29,
    "maxLeanFailureDelta": 1,
    "highRiskPassesPerClass": 3,
    "canonicalCompliancePct": 100.0,
    "tokenTelemetryCoveragePct": 90.0,
    "pairedTokenImprovementPct": 20.0,
    "improvedTaskClassCount": 7,
    "maxTaskClassTokenDegradationPct": 15.0,
    "maxToolCallDegradationPct": 10.0,
    "maxElapsedDegradationPct": 10.0,
    "maxBlindReviewScoreDelta": 0.25,
    "maxHumanCorrectionDelta": 1.0,
}
BLIND_IDENTITY_MARKERS = frozenset(
    {
        *PROFILES,
        *PROFILE_PROVIDER_IDS.values(),
        *(skill for skills in PROFILE_SKILLS.values() for skill in skills),
        "mattpocock",
        "superpowers",
    }
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()


def _sha256_json(payload: object) -> str:
    return hashlib.sha256(_json_bytes(payload)).hexdigest()


def _write_json(path: Path, payload: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _json_bytes(payload)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def _is_sha256(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _safe_evidence_path(root: Path, value: object) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _load_json(path: Path) -> object:
    return json.loads(path.read_text())


def _review_artifacts(raw_manifest: dict, evidence_root: Path) -> list[dict]:
    integrity_reasons, _ = _verify_additional_artifacts(raw_manifest, evidence_root)
    integrity_reasons.extend(
        _verify_required_artifacts(raw_manifest, evidence_root)
    )
    if integrity_reasons:
        raise ValueError(
            "raw manifest auxiliary artifacts are invalid: "
            + ", ".join(sorted(set(integrity_reasons)))
        )
    artifacts = []
    additional = raw_manifest.get("additionalArtifacts", {})
    if not isinstance(additional, dict):
        raise ValueError("raw manifest additionalArtifacts must be an object")
    for relative_path, expected_sha in sorted(additional.items()):
        if relative_path.endswith("/workspace-task-output.json"):
            review_name = "task-output.json"
        elif "/workspace-artifacts/" in relative_path:
            review_name = relative_path.split("/workspace-artifacts/", 1)[1]
        else:
            continue
        path = _safe_evidence_path(evidence_root, relative_path)
        if path is None or not path.is_file() or _sha256_file(path) != expected_sha:
            raise ValueError(f"blind-review artifact is missing or hash-invalid: {relative_path}")
        content = path.read_text(errors="replace")
        lowered = content.lower()
        for task_id in REQUIRED_TASK_IDS:
            lowered = lowered.replace(task_id, "")
        leaks = [
            marker
            for marker in BLIND_IDENTITY_MARKERS
            if re.search(rf"(?<![a-z0-9]){re.escape(marker)}(?![a-z0-9])", lowered)
        ]
        if leaks:
            raise ValueError(f"blind-review artifact leaks profile identity: {relative_path}")
        artifacts.append(
            {
                "name": review_name,
                "sha256": expected_sha,
                "content": content,
            }
        )
    return artifacts


def prepare_blind_review(execution: dict, *, evidence_root: Path | str) -> tuple[dict, dict]:
    """Create a deterministic public packet and separate private identity map."""
    root = Path(evidence_root).resolve()
    executed = execution.get("executed") if isinstance(execution, dict) else None
    if not isinstance(executed, list) or not executed:
        raise ValueError("execution manifest must contain executed runs")
    run_id = execution.get("runId")
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("execution manifest runId is missing")
    prepared = []
    for index, entry in enumerate(executed):
        draft = entry.get("normalized_run_draft") if isinstance(entry, dict) else None
        if not isinstance(draft, dict):
            raise ValueError(f"execution entry {index} has no normalized run draft")
        reference = draft.get("raw_manifest")
        manifest_path = _safe_evidence_path(root, reference.get("path") if isinstance(reference, dict) else None)
        if manifest_path is None or not manifest_path.is_file():
            raise ValueError(f"execution entry {index} raw manifest is missing")
        if _sha256_file(manifest_path) != reference.get("sha256"):
            raise ValueError(f"execution entry {index} raw manifest hash mismatch")
        manifest = _load_json(manifest_path)
        if not isinstance(manifest, dict):
            raise ValueError(f"execution entry {index} raw manifest is invalid")
        artifacts = _review_artifacts(manifest, root)
        if not artifacts:
            artifacts = [
                {
                    "name": "run-status.json",
                    "content": json.dumps(
                        {
                            "exit_code": entry.get("exit_code"),
                            "machine_verifier": draft.get("machine_verifier"),
                            "timed_out": entry.get("timed_out", False),
                        },
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n",
                }
            ]
            artifacts[0]["sha256"] = hashlib.sha256(artifacts[0]["content"].encode()).hexdigest()
        public_item = {
            "task_id": draft.get("task_id"),
            "repetition": draft.get("repetition"),
            "high_risk": draft.get("high_risk"),
            "artifacts": artifacts,
        }
        public_item["artifactSetSha256"] = _sha256_json(artifacts)
        sort_key = hashlib.sha256(
            (
                f"{run_id}|{reference.get('sha256')}|{draft.get('profile')}|"
                f"{draft.get('task_id')}|{draft.get('repetition')}|blind-v1"
            ).encode()
        ).hexdigest()
        prepared.append((sort_key, index, draft, reference, public_item))
    prepared.sort(key=lambda item: item[0])
    packet_items = []
    mapping_items = []
    for blind_index, (_, execution_index, draft, reference, public_item) in enumerate(prepared, 1):
        blind_id = f"B{blind_index:03d}"
        packet_items.append({"blind_id": blind_id, **public_item})
        mapping_items.append(
            {
                "blind_id": blind_id,
                "execution_index": execution_index,
                "profile": draft.get("profile"),
                "task_id": draft.get("task_id"),
                "repetition": draft.get("repetition"),
                "raw_manifest": reference,
            }
        )
    packet = {
        "kind": "devflow-provider-blind-review-packet",
        "schemaVersion": 1,
        "runId": run_id,
        "rubric": "evals/provider-profiles/rubric.md#human-quality-gates",
        "items": packet_items,
    }
    mapping = {
        "kind": "devflow-provider-blind-review-map",
        "schemaVersion": 1,
        "runId": run_id,
        "packetSha256": _sha256_json(packet),
        "items": mapping_items,
    }
    return packet, mapping


def blind_review_decision_template(packet: dict) -> dict:
    return {
        "kind": "devflow-provider-blind-review-decisions",
        "schemaVersion": 1,
        "packetSha256": _sha256_json(packet),
        "reviewer": None,
        "decisions": [
            {
                "blind_id": item["blind_id"],
                "artifactSetSha256": item["artifactSetSha256"],
                "score": None,
                "corrections": None,
                "notes": "",
            }
            for item in packet.get("items", ())
        ],
    }


def validate_blind_review_package(
    execution: dict,
    packet: dict,
    mapping: dict,
    *,
    evidence_root: Path | str,
) -> None:
    expected_packet, expected_mapping = prepare_blind_review(execution, evidence_root=evidence_root)
    if packet != expected_packet or mapping != expected_mapping:
        raise ValueError("blind-review packet or private map differs from raw execution evidence")


def _validated_decisions(packet: dict, decisions: dict) -> tuple[str, dict[str, dict]]:
    if decisions.get("kind") != "devflow-provider-blind-review-decisions":
        raise ValueError("blind-review decisions schema is invalid")
    if decisions.get("packetSha256") != _sha256_json(packet):
        raise ValueError("blind-review decisions do not match the public packet")
    reviewer = decisions.get("reviewer")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError("blind-review reviewer identity is required")
    packet_items = {item.get("blind_id"): item for item in packet.get("items", ())}
    decision_items = decisions.get("decisions")
    if not isinstance(decision_items, list):
        raise ValueError("blind-review decisions must be a list")
    decision_map = {}
    for decision in decision_items:
        if not isinstance(decision, dict) or not isinstance(decision.get("blind_id"), str):
            raise ValueError("blind-review decision item is invalid")
        blind_id = decision["blind_id"]
        packet_item = packet_items.get(blind_id)
        if packet_item is None or blind_id in decision_map:
            raise ValueError("blind-review decision IDs must match the packet exactly")
        if decision.get("artifactSetSha256") != packet_item.get("artifactSetSha256"):
            raise ValueError(f"blind-review decision artifact hash mismatch: {blind_id}")
        score = decision.get("score")
        corrections = decision.get("corrections")
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= score <= 5:
            raise ValueError(f"blind-review score is invalid: {blind_id}")
        if not isinstance(corrections, (int, float)) or isinstance(corrections, bool) or corrections < 0:
            raise ValueError(f"blind-review corrections are invalid: {blind_id}")
        decision_map[blind_id] = decision
    if set(decision_map) != set(packet_items):
        raise ValueError("blind-review decisions must cover every packet item exactly once")
    return reviewer.strip(), decision_map


def build_normalized_evidence(
    execution: dict,
    packet: dict,
    mapping: dict,
    decisions: dict,
    *,
    review_provenance: dict,
) -> dict:
    if mapping.get("packetSha256") != _sha256_json(packet):
        raise ValueError("private blind-review map does not match the public packet")
    if mapping.get("runId") != execution.get("runId") or packet.get("runId") != execution.get("runId"):
        raise ValueError("blind-review run IDs do not match the execution manifest")
    reviewer, decision_map = _validated_decisions(packet, decisions)
    packet_items = {item["blind_id"]: item for item in packet.get("items", ())}
    mapping_items = mapping.get("items")
    executed = execution.get("executed")
    if not isinstance(mapping_items, list) or not isinstance(executed, list):
        raise ValueError("blind-review map or execution entries are missing")
    runs_by_index = {}
    for item in mapping_items:
        if not isinstance(item, dict):
            raise ValueError("blind-review map item is invalid")
        blind_id = item.get("blind_id")
        execution_index = item.get("execution_index")
        if blind_id not in packet_items or not isinstance(execution_index, int):
            raise ValueError("blind-review map item identity is invalid")
        if execution_index < 0 or execution_index >= len(executed) or execution_index in runs_by_index:
            raise ValueError("blind-review execution index is invalid or duplicated")
        draft = executed[execution_index].get("normalized_run_draft")
        if not isinstance(draft, dict) or draft.get("blind_review") is not None:
            raise ValueError("execution draft is missing or already contains review data")
        for key in ("profile", "task_id", "repetition", "raw_manifest"):
            if item.get(key) != draft.get(key):
                raise ValueError(f"blind-review map does not match execution draft: {blind_id}")
        packet_item = packet_items[blind_id]
        for key in ("task_id", "repetition", "high_risk"):
            if packet_item.get(key) != draft.get(key):
                raise ValueError(f"blind-review packet does not match execution draft: {blind_id}")
        decision = decision_map[blind_id]
        decision_payload = {
            "blind_id": blind_id,
            "reviewer": reviewer,
            "artifactSetSha256": decision["artifactSetSha256"],
            "score": decision["score"],
            "corrections": decision["corrections"],
            "notes": decision.get("notes", ""),
        }
        normalized = copy.deepcopy(draft)
        normalized["blind_review"] = {
            **decision_payload,
            "decision_sha256": _sha256_json(decision_payload),
        }
        runs_by_index[execution_index] = normalized
    if set(runs_by_index) != set(range(len(executed))):
        raise ValueError("blind-review map must cover every execution entry exactly once")
    return {
        "kind": "devflow-provider-benchmark-evidence",
        "schema_version": 1,
        "runId": execution.get("runId"),
        "reviewProvenance": review_provenance,
        "runs": [runs_by_index[index] for index in range(len(executed))],
    }


def _load_hashed_reference(root: Path, reference: object, label: str) -> dict:
    if not isinstance(reference, dict):
        raise ValueError(f"review provenance {label} reference is missing")
    path = _safe_evidence_path(root, reference.get("path"))
    if path is None or not path.is_file():
        raise ValueError(f"review provenance {label} path is invalid")
    if not _is_sha256(reference.get("sha256")) or _sha256_file(path) != reference.get("sha256"):
        raise ValueError(f"review provenance {label} hash mismatch")
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"review provenance {label} payload is invalid")
    return payload


def verify_review_provenance(payload: dict, *, evidence_root: Path | str) -> list[str]:
    root = Path(evidence_root).resolve()
    provenance = payload.get("reviewProvenance") if isinstance(payload, dict) else None
    if not isinstance(provenance, dict):
        return ["review_provenance_missing"]
    try:
        execution = _load_hashed_reference(root, provenance.get("executionManifest"), "execution")
        packet = _load_hashed_reference(root, provenance.get("packet"), "packet")
        mapping = _load_hashed_reference(root, provenance.get("mapping"), "mapping")
        decisions = _load_hashed_reference(root, provenance.get("decisions"), "decisions")
        validate_blind_review_package(
            execution,
            packet,
            mapping,
            evidence_root=root,
        )
        expected = build_normalized_evidence(
            execution,
            packet,
            mapping,
            decisions,
            review_provenance=provenance,
        )
    except (OSError, ValueError, json.JSONDecodeError):
        return ["review_provenance_invalid"]
    if expected != payload:
        return ["normalized_evidence_provenance_mismatch"]
    return []


def _round(value: float | None, digits: int = 4) -> float | None:
    return None if value is None or not math.isfinite(value) else round(value, digits)


def _median(values: list[float]) -> float | None:
    return float(statistics.median(values)) if values else None


def _mean(values: list[float]) -> float | None:
    return float(statistics.fmean(values)) if values else None


def _degradation_pct(strict_values: list[float], lean_values: list[float]) -> float | None:
    strict_median = _median(strict_values)
    lean_median = _median(lean_values)
    if strict_median is None or lean_median is None:
        return None
    if strict_median == 0:
        return 0.0 if lean_median == 0 else math.inf
    return ((lean_median - strict_median) / strict_median) * 100.0


def _semantic_evidence(run: dict, category: str) -> object:
    return {
        "telemetry": run.get("telemetry"),
        "route": run.get("route_evidence"),
        "canonical": run.get("canonical_artifacts"),
        "side_effects": run.get("side_effects"),
        "source": {
            "profile": run.get("profile"),
            "task_id": run.get("task_id"),
            "task_class": run.get("task_class"),
            "repetition": run.get("repetition"),
            "high_risk": run.get("high_risk"),
            "hashes": run.get("hashes"),
        },
    }[category]


def _verify_additional_artifacts(
    manifest: dict,
    evidence_root: Path,
) -> tuple[list[str], dict[str, tuple[Path, str]]]:
    reasons: list[str] = []
    additional = manifest.get("additionalArtifacts")
    if not isinstance(additional, dict):
        return ["raw_additional_artifacts_missing"], {}
    verified: dict[str, tuple[Path, str]] = {}
    seen_paths: set[Path] = set()
    for relative_path, expected_sha in sorted(additional.items(), key=lambda item: str(item[0])):
        if (
            not isinstance(relative_path, str)
            or not relative_path
            or Path(relative_path).is_absolute()
        ):
            reasons.append("raw_additional_path_invalid")
            continue
        artifact_path = _safe_evidence_path(evidence_root, relative_path)
        if artifact_path is None:
            reasons.append("raw_additional_path_invalid")
            continue
        if artifact_path in seen_paths:
            reasons.append("raw_additional_path_duplicate")
            continue
        seen_paths.add(artifact_path)
        if not artifact_path.is_file():
            reasons.append("raw_additional_missing")
            continue
        if not _is_sha256(expected_sha) or _sha256_file(artifact_path) != expected_sha:
            reasons.append("raw_additional_hash_mismatch")
            continue
        verified[relative_path] = (artifact_path, expected_sha)
    return reasons, verified


def _verify_required_artifacts(manifest: dict, evidence_root: Path) -> list[str]:
    reasons: list[str] = []
    required = manifest.get("requiredArtifacts")
    if not isinstance(required, dict):
        return ["raw_required_artifacts_missing"]
    additional = manifest.get("additionalArtifacts")
    additional = additional if isinstance(additional, dict) else {}
    seen_paths: set[Path] = set()
    for category in REQUIRED_RAW_ARTIFACTS:
        reference = required.get(category)
        if not isinstance(reference, dict):
            reasons.append(f"raw_required_{category}_missing")
            continue
        relative_path = reference.get("path")
        expected_sha = reference.get("sha256")
        artifact_path = _safe_evidence_path(evidence_root, relative_path)
        if (
            not isinstance(relative_path, str)
            or Path(relative_path).is_absolute()
            or artifact_path is None
        ):
            reasons.append(f"raw_required_{category}_path_invalid")
            continue
        if artifact_path in seen_paths:
            reasons.append("raw_required_artifact_duplicate")
            continue
        seen_paths.add(artifact_path)
        if (
            not _is_sha256(expected_sha)
            or additional.get(relative_path) != expected_sha
            or not artifact_path.is_file()
            or _sha256_file(artifact_path) != expected_sha
        ):
            reasons.append(f"raw_required_{category}_hash_mismatch")
    return reasons


def _verify_raw_manifest(run: dict, evidence_root: Path) -> tuple[list[str], dict | None]:
    reasons: list[str] = []
    reference = run.get("raw_manifest")
    if not isinstance(reference, dict):
        return ["raw_manifest_reference_missing"], None
    manifest_path = _safe_evidence_path(evidence_root, reference.get("path"))
    if manifest_path is None:
        return ["raw_manifest_path_invalid"], None
    if not manifest_path.is_file():
        return ["raw_manifest_missing"], None
    if not _is_sha256(reference.get("sha256")) or _sha256_file(manifest_path) != reference.get("sha256"):
        return ["raw_manifest_hash_mismatch"], None
    try:
        manifest = _load_json(manifest_path)
    except (OSError, json.JSONDecodeError):
        return ["raw_manifest_invalid_json"], None
    if not isinstance(manifest, dict) or manifest.get("kind") != "devflow-provider-benchmark-raw-manifest":
        return ["raw_manifest_schema_invalid"], None
    for key in ("profile", "task_id", "repetition"):
        if manifest.get(key) != run.get(key):
            reasons.append(f"raw_manifest_{key}_mismatch")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        return reasons + ["raw_artifacts_missing"], manifest
    loaded_artifacts: dict[Path, object] = {}
    for category in REQUIRED_RAW_CATEGORIES:
        artifact = artifacts.get(category)
        if not isinstance(artifact, dict):
            reasons.append(f"raw_{category}_missing")
            continue
        artifact_path = _safe_evidence_path(evidence_root, artifact.get("path"))
        if artifact_path is None or not artifact_path.is_file():
            reasons.append(f"raw_{category}_path_invalid")
            continue
        if not _is_sha256(artifact.get("sha256")) or _sha256_file(artifact_path) != artifact.get("sha256"):
            reasons.append(f"raw_{category}_hash_mismatch")
            continue
        if artifact_path not in loaded_artifacts:
            try:
                loaded_artifacts[artifact_path] = _load_json(artifact_path)
            except (OSError, json.JSONDecodeError):
                reasons.append(f"raw_{category}_invalid_json")
                continue
        payload = loaded_artifacts.get(artifact_path)
        if not isinstance(payload, dict) or payload.get(category) != _semantic_evidence(run, category):
            reasons.append(f"raw_{category}_semantic_mismatch")
    additional_reasons, _ = _verify_additional_artifacts(manifest, evidence_root)
    reasons.extend(additional_reasons)
    reasons.extend(_verify_required_artifacts(manifest, evidence_root))
    return reasons, manifest


def _run_reasons(run: object, evidence_root: Path) -> tuple[list[str], dict | None]:
    if not isinstance(run, dict):
        return ["run_not_object"], None
    reasons: list[str] = []
    profile = run.get("profile")
    task_id = run.get("task_id")
    repetition = run.get("repetition")
    if profile not in PROFILES:
        reasons.append("unknown_profile")
    if task_id not in REQUIRED_TASK_IDS:
        reasons.append("unknown_task_id")
    if repetition not in EXPECTED_REPETITIONS:
        reasons.append("invalid_repetition")
    if run.get("task_class") != task_id:
        reasons.append("task_class_mismatch")
    if run.get("high_risk") is not (task_id in HIGH_RISK_TASK_IDS):
        reasons.append("high_risk_classification_mismatch")

    machine = run.get("machine_verifier")
    if not isinstance(machine, dict) or not isinstance(machine.get("passed"), bool):
        reasons.append("machine_verifier_evidence_missing")
    canonical = run.get("canonical_artifacts")
    if not isinstance(canonical, dict):
        reasons.append("canonical_evidence_missing")
    elif not isinstance(canonical.get("compliant"), bool) or not isinstance(canonical.get("corruption"), bool):
        reasons.append("canonical_evidence_invalid")
    side_effects = run.get("side_effects")
    if not isinstance(side_effects, dict) or not isinstance(side_effects.get("unauthorized"), list):
        reasons.append("side_effect_evidence_missing")

    route = run.get("route_evidence")
    if not isinstance(route, dict):
        reasons.append("actual_route_missing")
    else:
        if route.get("selected_profile") != profile:
            reasons.append("actual_route_profile_mismatch")
        if route.get("provider_invoked") is not True:
            reasons.append("actual_route_not_invoked")
        if not route.get("capability"):
            reasons.append("actual_route_capability_missing")
        if not isinstance(route.get("invoked_skills"), list) or not route.get("invoked_skills"):
            reasons.append("actual_route_invoked_skills_missing")
        if not isinstance(route.get("skill_sha256"), dict) or not route.get("skill_sha256"):
            reasons.append("actual_route_skill_hashes_missing")

    blind = run.get("blind_review")
    if not isinstance(blind, dict):
        reasons.append("blind_review_missing")
    else:
        score = blind.get("score")
        corrections = blind.get("corrections")
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= score <= 5:
            reasons.append("blind_review_score_invalid")
        if not isinstance(corrections, (int, float)) or isinstance(corrections, bool) or corrections < 0:
            reasons.append("human_corrections_invalid")
        decision_payload = {
            "blind_id": blind.get("blind_id"),
            "reviewer": blind.get("reviewer"),
            "artifactSetSha256": blind.get("artifactSetSha256"),
            "score": score,
            "corrections": corrections,
            "notes": blind.get("notes", ""),
        }
        if (
            not isinstance(blind.get("blind_id"), str)
            or not isinstance(blind.get("reviewer"), str)
            or not _is_sha256(blind.get("artifactSetSha256"))
            or blind.get("decision_sha256") != _sha256_json(decision_payload)
        ):
            reasons.append("blind_review_provenance_invalid")

    hashes = run.get("hashes")
    if not isinstance(hashes, dict):
        reasons.append("source_hash_evidence_missing")
    else:
        for key in ("repository_sha256", "prompt_sha256", "provider_sha256"):
            if not _is_sha256(hashes.get(key)):
                reasons.append(f"{key}_invalid")
        skills = hashes.get("skill_sha256")
        if not isinstance(skills, dict) or not skills or not all(_is_sha256(item) for item in skills.values()):
            reasons.append("skill_sha256_invalid")
        if isinstance(route, dict) and route.get("provider_sha256") != hashes.get("provider_sha256"):
            reasons.append("actual_route_provider_hash_mismatch")
        if isinstance(route, dict) and isinstance(skills, dict):
            invoked_skills = route.get("invoked_skills")
            route_skill_hashes = route.get("skill_sha256")
            if isinstance(invoked_skills, list) and isinstance(route_skill_hashes, dict):
                expected_route_hashes = {
                    skill_name: skills.get(skill_name)
                    for skill_name in invoked_skills
                    if isinstance(skill_name, str)
                }
                if route_skill_hashes != expected_route_hashes or None in expected_route_hashes.values():
                    reasons.append("actual_route_skill_hash_mismatch")

    raw_reasons, manifest = _verify_raw_manifest(run, evidence_root)
    reasons.extend(raw_reasons)
    return reasons, manifest


def _failure(reasons: list[dict], identifier: str, message: str, actual: object, threshold: object) -> None:
    if any(item["id"] == identifier for item in reasons):
        return
    reasons.append({"id": identifier, "message": message, "actual": actual, "threshold": threshold})


def aggregate_benchmark(payload: dict, *, evidence_root: Path | str) -> dict:
    """Return default-switch eligibility without changing the selected default."""
    root = Path(evidence_root).resolve()
    runs = payload.get("runs") if isinstance(payload, dict) else None
    if not isinstance(runs, list):
        raise ValueError("benchmark evidence must contain a runs array")
    review_provenance_reasons = verify_review_provenance(payload, evidence_root=root)

    keyed = Counter(
        (run.get("profile"), run.get("task_id"), run.get("repetition"))
        for run in runs
        if isinstance(run, dict)
    )
    valid_runs: list[dict] = []
    invalid_runs: list[dict] = []
    raw_hashes: list[dict] = []
    raw_integrity_failed = False
    route_integrity_failed = False
    source_hash_failed = False
    for index, run in enumerate(runs):
        reasons, raw_manifest = _run_reasons(run, root)
        if isinstance(run, dict):
            key = (run.get("profile"), run.get("task_id"), run.get("repetition"))
            if keyed[key] != 1:
                reasons.append("duplicate_pair_key")
            reference = run.get("raw_manifest")
            if raw_manifest is not None and isinstance(reference, dict):
                raw_hashes.append(
                    {
                        "profile": run.get("profile"),
                        "task_id": run.get("task_id"),
                        "repetition": run.get("repetition"),
                        "path": reference.get("path"),
                        "sha256": reference.get("sha256"),
                    }
                )
        if any(item.startswith("raw_") for item in reasons):
            raw_integrity_failed = True
        if any(item.startswith("actual_route") for item in reasons):
            route_integrity_failed = True
        if any("sha256" in item or item == "source_hash_evidence_missing" for item in reasons):
            source_hash_failed = True
        if reasons:
            invalid_runs.append(
                {
                    "index": index,
                    "profile": run.get("profile") if isinstance(run, dict) else None,
                    "task_id": run.get("task_id") if isinstance(run, dict) else None,
                    "repetition": run.get("repetition") if isinstance(run, dict) else None,
                    "reasons": sorted(set(reasons)),
                }
            )
        else:
            valid_runs.append(run)

    by_profile = {profile: [] for profile in PROFILES}
    by_key = {profile: {} for profile in PROFILES}
    for run in valid_runs:
        profile = run["profile"]
        by_profile[profile].append(run)
        by_key[profile][(run["task_id"], run["repetition"])] = run
    expected_keys = {(task_id, repetition) for task_id in REQUIRED_TASK_IDS for repetition in EXPECTED_REPETITIONS}
    paired_keys = sorted(set(by_key[PROFILES[0]]) & set(by_key[PROFILES[1]]))
    exact_pairs = all(set(by_key[profile]) == expected_keys for profile in PROFILES)

    machine_passes = {
        profile: sum(run["machine_verifier"]["passed"] is True for run in by_profile[profile])
        for profile in PROFILES
    }
    machine_failures = {profile: EXPECTED_RUNS_PER_PROFILE - machine_passes[profile] for profile in PROFILES}
    high_risk_passes = {}
    for task_id in sorted(HIGH_RISK_TASK_IDS):
        selected = [run for run in by_profile["lean-matt"] if run["task_id"] == task_id]
        high_risk_passes[task_id] = sum(run["machine_verifier"]["passed"] is True for run in selected)

    canonical_compliance = {
        profile: (
            100.0
            * sum(run["canonical_artifacts"]["compliant"] is True for run in by_profile[profile])
            / len(by_profile[profile])
            if by_profile[profile]
            else 0.0
        )
        for profile in PROFILES
    }
    canonical_corruption = {
        profile: sum(run["canonical_artifacts"]["corruption"] is True for run in by_profile[profile])
        for profile in PROFILES
    }
    unauthorized_effects = {
        profile: sum(len(run["side_effects"]["unauthorized"]) for run in by_profile[profile])
        for profile in PROFILES
    }

    complete_pairs = []
    for key in paired_keys:
        strict = by_key["strict-superpowers"][key]
        lean = by_key["lean-matt"][key]
        strict_telemetry = strict.get("telemetry")
        lean_telemetry = lean.get("telemetry")
        values = []
        for telemetry in (strict_telemetry, lean_telemetry):
            if not isinstance(telemetry, dict):
                values.append(None)
                continue
            total = telemetry.get("total_tokens")
            tools = telemetry.get("tool_calls")
            elapsed = telemetry.get("elapsed_seconds")
            if (
                not isinstance(total, (int, float))
                or isinstance(total, bool)
                or total <= 0
                or not isinstance(tools, (int, float))
                or isinstance(tools, bool)
                or tools < 0
                or not isinstance(elapsed, (int, float))
                or isinstance(elapsed, bool)
                or elapsed <= 0
            ):
                values.append(None)
            else:
                values.append((float(total), float(tools), float(elapsed)))
        if all(item is not None for item in values):
            complete_pairs.append((key, values[0], values[1]))

    telemetry_coverage = 100.0 * len(complete_pairs) / EXPECTED_RUNS_PER_PROFILE
    token_improvements = [((strict[0] - lean[0]) / strict[0]) * 100.0 for _, strict, lean in complete_pairs]
    per_class_values: dict[str, list[float]] = defaultdict(list)
    for (task_id, _), strict, lean in complete_pairs:
        per_class_values[task_id].append(((strict[0] - lean[0]) / strict[0]) * 100.0)
    per_class_improvement = {
        task_id: _round(_median(per_class_values.get(task_id, [])))
        for task_id in REQUIRED_TASK_IDS
    }
    improved_class_count = sum(
        value is not None and value > 0 for value in per_class_improvement.values()
    )
    strict_tools = [strict[1] for _, strict, _ in complete_pairs]
    lean_tools = [lean[1] for _, _, lean in complete_pairs]
    strict_elapsed = [strict[2] for _, strict, _ in complete_pairs]
    lean_elapsed = [lean[2] for _, _, lean in complete_pairs]
    tool_degradation = _degradation_pct(strict_tools, lean_tools)
    elapsed_degradation = _degradation_pct(strict_elapsed, lean_elapsed)
    blind_means = {
        profile: _mean([float(run["blind_review"]["score"]) for run in by_profile[profile]])
        for profile in PROFILES
    }
    correction_means = {
        profile: _mean([float(run["blind_review"]["corrections"]) for run in by_profile[profile]])
        for profile in PROFILES
    }

    failures: list[dict] = []
    if review_provenance_reasons:
        _failure(
            failures,
            "blind_review_provenance",
            "Normalized runs are not bound to hashed execution and blind-review artifacts.",
            review_provenance_reasons,
            [],
        )
    if raw_integrity_failed:
        _failure(failures, "raw_evidence_integrity", "Raw evidence is missing or hash-invalid.", False, True)
    if route_integrity_failed:
        _failure(
            failures,
            "actual_route_evidence",
            "Installed provider was not proven to be the actual route.",
            False,
            True,
        )
    if source_hash_failed:
        _failure(
            failures,
            "source_hash_evidence",
            "Repository, prompt, provider, or skill hashes are incomplete.",
            False,
            True,
        )
    if not exact_pairs or len(paired_keys) != EXPECTED_RUNS_PER_PROFILE:
        _failure(
            failures,
            "valid_pair_count",
            "Exactly 30 task_id+repetition pairs are required for each profile.",
            {profile: len(by_key[profile]) for profile in PROFILES} | {"paired": len(paired_keys)},
            THRESHOLDS["validPairsPerProfile"],
        )
    if machine_passes["lean-matt"] < THRESHOLDS["leanMachineVerifierPasses"]:
        _failure(
            failures,
            "lean_machine_verifier_passes",
            "Lean machine-verifier passes are below the minimum.",
            machine_passes["lean-matt"],
            THRESHOLDS["leanMachineVerifierPasses"],
        )
    failure_delta = machine_failures["lean-matt"] - machine_failures["strict-superpowers"]
    if failure_delta > THRESHOLDS["maxLeanFailureDelta"]:
        _failure(
            failures,
            "machine_failure_delta",
            "Lean has more than one additional machine-verifier failure.",
            failure_delta,
            THRESHOLDS["maxLeanFailureDelta"],
        )
    if any(value != THRESHOLDS["highRiskPassesPerClass"] for value in high_risk_passes.values()):
        _failure(
            failures,
            "high_risk_machine_passes",
            "Every high-risk lean task class must pass three of three runs.",
            high_risk_passes,
            THRESHOLDS["highRiskPassesPerClass"],
        )
    if unauthorized_effects["lean-matt"] != 0:
        _failure(
            failures,
            "unauthorized_side_effects",
            "Lean runs contain unauthorized side effects.",
            unauthorized_effects["lean-matt"],
            0,
        )
    if canonical_compliance["lean-matt"] != THRESHOLDS["canonicalCompliancePct"]:
        _failure(
            failures,
            "canonical_artifact_compliance",
            "Lean canonical artifact compliance is not 100%.",
            _round(canonical_compliance["lean-matt"]),
            THRESHOLDS["canonicalCompliancePct"],
        )
    if canonical_corruption["lean-matt"] != 0:
        _failure(
            failures,
            "canonical_artifact_corruption",
            "Lean runs contain canonical artifact corruption.",
            canonical_corruption["lean-matt"],
            0,
        )
    if telemetry_coverage < THRESHOLDS["tokenTelemetryCoveragePct"]:
        _failure(
            failures,
            "token_telemetry_coverage",
            "Paired telemetry coverage is below 90%.",
            _round(telemetry_coverage),
            THRESHOLDS["tokenTelemetryCoveragePct"],
        )
    token_median = _median(token_improvements)
    if token_median is None or token_median < THRESHOLDS["pairedTokenImprovementPct"]:
        _failure(
            failures,
            "paired_total_token_improvement",
            "Median paired total-token improvement is below 20%.",
            _round(token_median),
            THRESHOLDS["pairedTokenImprovementPct"],
        )
    if improved_class_count < THRESHOLDS["improvedTaskClassCount"]:
        _failure(
            failures,
            "improved_task_class_count",
            "Fewer than seven task classes improve on paired median tokens.",
            improved_class_count,
            THRESHOLDS["improvedTaskClassCount"],
        )
    degraded_classes = {
        task_id: value
        for task_id, value in per_class_improvement.items()
        if value is None or value < -THRESHOLDS["maxTaskClassTokenDegradationPct"]
    }
    if degraded_classes:
        _failure(
            failures,
            "task_class_token_degradation",
            "One or more task classes degrade by more than 15% median tokens.",
            degraded_classes,
            THRESHOLDS["maxTaskClassTokenDegradationPct"],
        )
    if tool_degradation is None or tool_degradation > THRESHOLDS["maxToolCallDegradationPct"]:
        _failure(
            failures,
            "tool_call_degradation",
            "Aggregate median tool calls degrade by more than 10%.",
            _round(tool_degradation),
            THRESHOLDS["maxToolCallDegradationPct"],
        )
    if elapsed_degradation is None or elapsed_degradation > THRESHOLDS["maxElapsedDegradationPct"]:
        _failure(
            failures,
            "elapsed_time_degradation",
            "Aggregate median elapsed time degrades by more than 10%.",
            _round(elapsed_degradation),
            THRESHOLDS["maxElapsedDegradationPct"],
        )
    blind_delta = None
    if all(blind_means[profile] is not None for profile in PROFILES):
        blind_delta = blind_means["lean-matt"] - blind_means["strict-superpowers"]
    if blind_delta is None or blind_delta < -THRESHOLDS["maxBlindReviewScoreDelta"]:
        _failure(
            failures,
            "blind_review_quality",
            "Lean arithmetic-mean blind score is more than 0.25 below strict.",
            _round(blind_delta),
            -THRESHOLDS["maxBlindReviewScoreDelta"],
        )
    correction_delta = None
    if all(correction_means[profile] is not None for profile in PROFILES):
        correction_delta = correction_means["lean-matt"] - correction_means["strict-superpowers"]
    if correction_delta is None or correction_delta > THRESHOLDS["maxHumanCorrectionDelta"]:
        _failure(
            failures,
            "human_correction_delta",
            "Lean arithmetic-mean human corrections exceed strict by more than one.",
            _round(correction_delta),
            THRESHOLDS["maxHumanCorrectionDelta"],
        )

    metrics = {
        "validRunsByProfile": {profile: len(by_profile[profile]) for profile in PROFILES},
        "validPairCount": len(paired_keys),
        "machineVerifierPasses": machine_passes,
        "machineVerifierFailures": machine_failures,
        "highRiskMachinePasses": high_risk_passes,
        "canonicalCompliancePct": {profile: _round(value) for profile, value in canonical_compliance.items()},
        "canonicalCorruptionCount": canonical_corruption,
        "unauthorizedSideEffectCount": unauthorized_effects,
        "tokenTelemetryCoveragePct": _round(telemetry_coverage),
        "pairedTokenImprovementMedianPct": _round(token_median),
        "taskClassTokenImprovementMedianPct": per_class_improvement,
        "improvedTaskClassCount": improved_class_count,
        "toolCallDegradationPct": _round(tool_degradation),
        "elapsedDegradationPct": _round(elapsed_degradation),
        "blindReviewMean": {profile: _round(value) for profile, value in blind_means.items()},
        "blindReviewDelta": _round(blind_delta),
        "humanCorrectionsMean": {profile: _round(value) for profile, value in correction_means.items()},
        "humanCorrectionDelta": _round(correction_delta),
        "metricPairCount": len(complete_pairs),
    }
    eligible = not failures
    return {
        "kind": "devflow-provider-benchmark-aggregate",
        "schemaVersion": 1,
        "eligibleForDefaultProposal": eligible,
        "decision": "eligible_for_separate_default_change" if eligible else "lean_matt_remains_opt_in",
        "thresholds": THRESHOLDS,
        "metrics": metrics,
        "failureReasons": failures,
        "invalidRuns": invalid_runs,
        "rawManifestHashes": raw_hashes,
        "claimBoundary": "This aggregate never changes the default and cannot replace a separately approved change.",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare, import, or aggregate reproducible DevFlow provider benchmark evidence.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--input", help="Normalized benchmark evidence JSON to aggregate.")
    mode.add_argument("--prepare-review-from", help="Execution manifest used to create blind-review files.")
    mode.add_argument("--apply-review-from", help="Execution manifest used to import blind decisions.")
    parser.add_argument(
        "--evidence-root",
        help="Immutable raw evidence root; defaults to the input file's directory.",
    )
    parser.add_argument("--review-packet", help="Public blind-review packet path.")
    parser.add_argument("--review-map", help="Private blind-ID mapping path.")
    parser.add_argument("--review-decisions", help="Reviewer decision/template path.")
    parser.add_argument("--output", help="Aggregate report or normalized evidence output path.")
    return parser


def _reference_for_path(root: Path, path: Path) -> dict:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"provenance artifact must be inside evidence root: {resolved}") from exc
    if not resolved.is_file():
        raise ValueError(f"provenance artifact does not exist: {resolved}")
    return {"path": relative, "sha256": _sha256_file(resolved)}


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.prepare_review_from:
            execution_path = Path(args.prepare_review_from).resolve()
            root = Path(args.evidence_root).resolve() if args.evidence_root else execution_path.parent
            if not args.review_packet or not args.review_map or not args.review_decisions:
                raise ValueError("review preparation requires --review-packet, --review-map, and --review-decisions")
            execution = _load_json(execution_path)
            if not isinstance(execution, dict):
                raise ValueError("execution manifest must be a JSON object")
            packet, mapping = prepare_blind_review(execution, evidence_root=root)
            packet_path = Path(args.review_packet).resolve()
            mapping_path = Path(args.review_map).resolve()
            decisions_path = Path(args.review_decisions).resolve()
            packet_sha = _write_json(packet_path, packet)
            mapping_sha = _write_json(mapping_path, mapping)
            decisions_sha = _write_json(decisions_path, blind_review_decision_template(packet))
            for path in (packet_path, mapping_path, decisions_path):
                _reference_for_path(root, path)
            print(
                json.dumps(
                    {
                        "ok": True,
                        "mode": "blind-review-prepared",
                        "itemCount": len(packet["items"]),
                        "packetSha256": packet_sha,
                        "mappingSha256": mapping_sha,
                        "decisionTemplateSha256": decisions_sha,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.apply_review_from:
            execution_path = Path(args.apply_review_from).resolve()
            root = Path(args.evidence_root).resolve() if args.evidence_root else execution_path.parent
            if not args.review_packet or not args.review_map or not args.review_decisions or not args.output:
                raise ValueError(
                    "review import requires --review-packet, --review-map, --review-decisions, and --output"
                )
            packet_path = Path(args.review_packet).resolve()
            mapping_path = Path(args.review_map).resolve()
            decisions_path = Path(args.review_decisions).resolve()
            execution = _load_json(execution_path)
            packet = _load_json(packet_path)
            mapping = _load_json(mapping_path)
            decisions = _load_json(decisions_path)
            if not all(isinstance(item, dict) for item in (execution, packet, mapping, decisions)):
                raise ValueError("review import artifacts must be JSON objects")
            validate_blind_review_package(
                execution,
                packet,
                mapping,
                evidence_root=root,
            )
            provenance = {
                "executionManifest": _reference_for_path(root, execution_path),
                "packet": _reference_for_path(root, packet_path),
                "mapping": _reference_for_path(root, mapping_path),
                "decisions": _reference_for_path(root, decisions_path),
            }
            normalized = build_normalized_evidence(
                execution,
                packet,
                mapping,
                decisions,
                review_provenance=provenance,
            )
            _write_json(Path(args.output).resolve(), normalized)
            print(json.dumps({"ok": True, "mode": "blind-review-applied", "runCount": len(normalized["runs"])}))
            return 0
        input_path = Path(args.input).resolve()
        payload = _load_json(input_path)
        if not isinstance(payload, dict):
            raise ValueError("benchmark evidence root must be a JSON object")
        report = aggregate_benchmark(
            payload,
            evidence_root=Path(args.evidence_root).resolve() if args.evidence_root else input_path.parent,
        )
        rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.output:
            output = Path(args.output).resolve()
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(rendered)
        else:
            print(rendered, end="")
        return 0 if report["eligibleForDefaultProposal"] else 1
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
