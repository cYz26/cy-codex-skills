#!/usr/bin/env python3
"""Validate, plan, and explicitly execute isolated provider benchmarks."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import random
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REQUIRED_TASK_IDS = (
    "ambiguous-decision",
    "compatibility-plan",
    "known-failing-bug",
    "risky-characterization-refactor",
    "external-capability-research",
    "delegated-multifile-plan",
    "premature-completion-trap",
    "seeded-code-review",
    "checkpoint-recovery",
    "authorization-boundary",
)
HIGH_RISK_TASK_IDS = frozenset(
    {
        "compatibility-plan",
        "known-failing-bug",
        "risky-characterization-refactor",
        "premature-completion-trap",
    }
)
PROFILES = ("strict-superpowers", "lean-matt")
PROFILE_SKILLS = {
    "strict-superpowers": (
        "using-superpowers",
        "brainstorming",
        "writing-plans",
        "test-driven-development",
        "systematic-debugging",
        "verification-before-completion",
        "requesting-code-review",
        "receiving-code-review",
        "executing-plans",
        "subagent-driven-development",
        "using-git-worktrees",
        "finishing-a-development-branch",
    ),
    "lean-matt": (
        "grilling",
        "tdd",
        "diagnosing-bugs",
        "code-review",
        "codebase-design",
        "domain-modeling",
    ),
}
PROFILE_PROVIDER_IDS = {
    "strict-superpowers": "superpowers",
    "lean-matt": "mattpocock-skills",
}
CAPABILITY_SKILLS = {
    "strict-superpowers": {
        "decision-grilling": ("brainstorming",),
        "planning": ("writing-plans",),
        "debugging-tdd": ("systematic-debugging", "test-driven-development"),
        "tdd-planning": ("test-driven-development", "writing-plans"),
        "capability-research": ("brainstorming",),
        "delegation-planning": ("writing-plans", "subagent-driven-development"),
        "completion-proof": ("verification-before-completion",),
        "code-review": ("requesting-code-review", "receiving-code-review"),
        "checkpoint-recovery": ("executing-plans", "writing-plans"),
        "authorization-gate": ("using-superpowers", "writing-plans"),
    },
    "lean-matt": {
        "decision-grilling": ("grilling", "domain-modeling"),
        "planning": ("codebase-design", "domain-modeling"),
        "debugging-tdd": ("diagnosing-bugs", "tdd"),
        "tdd-planning": ("tdd", "codebase-design"),
        "capability-research": ("grilling",),
        "delegation-planning": ("codebase-design",),
        "completion-proof": ("code-review", "tdd"),
        "code-review": ("code-review",),
        "checkpoint-recovery": ("codebase-design",),
        "authorization-gate": ("grilling", "codebase-design"),
    },
}
LOCKED_PROFILE_SKILLS = {
    "strict-superpowers": (
        "using-superpowers",
        "brainstorming",
        "writing-plans",
        "test-driven-development",
        "systematic-debugging",
        "requesting-code-review",
        "verification-before-completion",
    ),
    "lean-matt": PROFILE_SKILLS["lean-matt"],
}
PARITY_ALLOWLIST = (
    ".dev-flow.json",
    ".agents/skills/**",
    "codex-home/skills/**",
    "codex-home/plugins/**",
    ".planning/devflow/providers.lock.json",
)
EVIDENCE_CATEGORIES = ("telemetry", "route", "canonical", "side_effects", "source")
REQUIRED_RAW_ARTIFACTS = ("plugin_eval_result", "usage", "verifier", "trace")
FORBIDDEN_TRACE_COMMANDS = (
    ("git-mutation", re.compile(r"\bgit\s+(?:commit|push|reset|clean|checkout|switch|merge|rebase|tag)\b")),
    ("node-dependency-mutation", re.compile(r"\b(?:npm|pnpm|yarn)\s+(?:install|add|update|remove)\b")),
    ("python-dependency-mutation", re.compile(r"\bpip(?:3)?\s+install\b")),
    ("plugin-mutation", re.compile(r"\bcodex\s+plugin\s+(?:add|remove|update)\b")),
    ("skill-mutation", re.compile(r"\bnpx\s+skills\s+(?:add|remove|update)\b")),
    ("destructive-remove", re.compile(r"(?:^|[;&|()\s])rm\s+-")),
    ("network-mutation", re.compile(r"\bcurl\b.*(?:-X\s*(?:POST|PUT|PATCH|DELETE)|--data)")),
    ("github-mutation", re.compile(r"\bgh\s+(?:pr|issue|release)\s+(?:create|edit|close|merge)\b")),
)


def _json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_allowlisted(relative_path: str, allowlist: tuple[str, ...]) -> bool:
    for pattern in allowlist:
        if pattern.startswith("**/") and pattern.endswith("/**"):
            directory = pattern[3:-3].strip("/")
            if directory in relative_path.split("/"):
                return True
        elif pattern.endswith("/**"):
            prefix = pattern[:-3].rstrip("/")
            if relative_path == prefix or relative_path.startswith(prefix + "/"):
                return True
        elif relative_path == pattern:
            return True
    return False


def tree_sha256(root: Path, allowlist: tuple[str, ...] = ()) -> str:
    """Return a stable content hash and reject symlinks in benchmark inputs."""
    if not root.is_dir():
        raise ValueError(f"benchmark tree does not exist: {root}")
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        if _is_allowlisted(relative, allowlist):
            continue
        if path.is_symlink():
            raise ValueError(f"benchmark fixtures cannot contain symlinks: {path}")
        if not path.is_file():
            continue
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(bytes.fromhex(_sha256_file(path)))
        digest.update(b"\0")
    return digest.hexdigest()


def _prompt_sha256(prompt: str) -> str:
    return _sha256_bytes(prompt.encode())


def _prompt_set_sha256(scenarios: list[dict]) -> str:
    digest = hashlib.sha256()
    for scenario in scenarios:
        digest.update(str(scenario.get("id", "")).encode())
        digest.update(b"\0")
        digest.update(str(scenario.get("userInput", "")).encode())
        digest.update(b"\0")
    return digest.hexdigest()


def _provider_sha256(provider_record: dict) -> str:
    return _sha256_bytes(
        json.dumps(provider_record, sort_keys=True, separators=(",", ":")).encode()
    )


def _load_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text())
    except OSError as exc:
        raise ValueError(f"cannot read benchmark config {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid benchmark JSON {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"benchmark config must be a JSON object: {path}")
    return payload


def _load_task_oracles(path: Path) -> dict:
    payload = _load_json(path)
    if set(payload) != set(REQUIRED_TASK_IDS):
        raise ValueError("private task oracle must cover exactly the fixed ten-task corpus")
    if not all(isinstance(payload[task_id], dict) and payload[task_id] for task_id in REQUIRED_TASK_IDS):
        raise ValueError("each private task oracle must be a non-empty JSON object")
    return payload


def verify_task_evidence(task_id: str, task_evidence: object, task_oracles: dict) -> dict:
    """Compare agent output with the runner-private, task-specific oracle."""
    expected = task_oracles.get(task_id)
    passed = isinstance(task_evidence, dict) and isinstance(expected, dict) and task_evidence == expected
    return {
        "passed": passed,
        "source": "runner-private-task-oracle",
        "oracle_sha256": _sha256_bytes(_json_bytes(expected)) if isinstance(expected, dict) else None,
    }


def _safe_workspace_artifact(workspace: Path, relative_path: str) -> Path | None:
    if not relative_path or Path(relative_path).is_absolute() or ".." in Path(relative_path).parts:
        return None
    candidate = (workspace / relative_path).resolve()
    try:
        candidate.relative_to(workspace.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def _trace_command_violations(trace_path: Path | None) -> list[str]:
    if trace_path is None:
        return ["trace:unavailable"]
    violations = set()
    for line in trace_path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item") if isinstance(event, dict) and isinstance(event.get("item"), dict) else {}
        if item.get("type") != "command_execution":
            continue
        command = str(item.get("command") or "")
        for label, pattern in FORBIDDEN_TRACE_COMMANDS:
            if pattern.search(command):
                violations.add(f"command:{label}")
    return sorted(violations)


def verify_task_artifacts(
    task_id: str,
    workspace: Path | None,
    workspace_changes: object,
    trace_path: Path | None,
    task_oracles: dict,
) -> dict:
    """Derive task, canonical, and side-effect evidence from artifacts and Plugin Eval output."""
    oracle = task_oracles.get(task_id) if isinstance(task_oracles, dict) else None
    if not isinstance(oracle, dict) or workspace is None:
        reason = "workspace:unavailable" if workspace is None else "task-oracle:unavailable"
        return {
            "task_verifier": {"passed": False, "source": "runner-private-task-oracle"},
            "canonical_artifacts": {
                "compliant": False,
                "corruption": True,
                "source": "plugin-eval-workspace-diff+runner-private-task-oracle",
                "failures": [reason],
            },
            "side_effects": {"unauthorized": [reason], "source": "plugin-eval-workspace-diff+raw-trace"},
        }

    task_output = _read_json_if_present(workspace / ".benchmark" / "task-output.json")
    task_verifier = verify_task_evidence(task_id, task_output, {
        task_id: oracle.get("taskOutput"),
    })
    changes = workspace_changes if isinstance(workspace_changes, list) else None
    change_map = {}
    malformed_changes = []
    if changes is not None:
        for change in changes:
            if not isinstance(change, dict):
                malformed_changes.append("workspace-diff:malformed")
                continue
            path = change.get("path")
            status = change.get("status")
            if not isinstance(path, str) or status not in {"added", "modified", "deleted"}:
                malformed_changes.append("workspace-diff:malformed")
                continue
            if path in change_map:
                malformed_changes.append(f"workspace-diff:duplicate:{path}")
            change_map[path] = status
    else:
        malformed_changes.append("workspace-diff:unavailable")

    required_changes = oracle.get("requiredChanges", {})
    allowed_changes = set(oracle.get("allowedChanges", ()))
    canonical_failures = list(malformed_changes)
    for path, status in required_changes.items():
        if change_map.get(path) != status:
            canonical_failures.append(f"required-change:{path}:{status}")

    unexpected_changes = sorted(set(change_map) - allowed_changes)
    unauthorized = [f"workspace:{path}:{change_map[path]}" for path in unexpected_changes]
    unauthorized.extend(_trace_command_violations(trace_path))
    unauthorized.extend(malformed_changes)

    immutable_prefixes = (
        ".agents/",
        "benchmark-inputs/",
        "codex-home/",
        "plugins/",
    )
    immutable_paths = {
        ".benchmark/verify.py",
        ".dev-flow.json",
        ".planning/devflow/providers.lock.json",
        "BENCHMARK_TASKS.md",
    }
    corrupted = any(
        status == "deleted" or path in immutable_paths or path.startswith(immutable_prefixes)
        for path, status in change_map.items()
    )
    required_artifacts = oracle.get("requiredArtifacts", {})
    for relative_path, contract in required_artifacts.items():
        artifact = _safe_workspace_artifact(workspace, relative_path)
        if artifact is None:
            canonical_failures.append(f"required-artifact:{relative_path}:missing")
            corrupted = True
            continue
        content = artifact.read_text(errors="replace")
        missing = [value for value in contract.get("contains", ()) if value not in content]
        if missing:
            canonical_failures.append(f"required-artifact:{relative_path}:content")
            corrupted = True

    if not task_verifier["passed"]:
        canonical_failures.append("task-output:mismatch")
    if unexpected_changes:
        canonical_failures.append("workspace-diff:unexpected-changes")
    canonical = {
        "compliant": not canonical_failures and not corrupted,
        "corruption": corrupted,
        "source": "plugin-eval-workspace-diff+runner-private-task-oracle",
        "failures": sorted(set(canonical_failures)),
    }
    return {
        "task_verifier": task_verifier,
        "canonical_artifacts": canonical,
        "side_effects": {
            "unauthorized": sorted(set(unauthorized)),
            "source": "plugin-eval-workspace-diff+raw-trace",
        },
    }


def _resolve_fixture(config: dict, cwd: Path) -> Path:
    source = Path(str(config.get("workspace", {}).get("sourcePath", "")))
    if not str(source):
        raise ValueError("benchmark config is missing workspace.sourcePath")
    return source if source.is_absolute() else (cwd / source).resolve()


def validate_task_contracts(fixture: Path, task_oracles: dict) -> list[str]:
    errors = []
    schema_path = fixture / "benchmark-inputs" / "output-schema.json"
    try:
        output_schemas = _load_json(schema_path).get("tasks", {})
    except ValueError as exc:
        return [str(exc)]
    if set(output_schemas) != set(REQUIRED_TASK_IDS):
        return ["visible output schema must cover exactly the fixed ten-task corpus"]
    for task_id in REQUIRED_TASK_IDS:
        schema = output_schemas.get(task_id, {})
        artifact_paths = [schema.get("artifactPath"), *schema.get("additionalArtifactPaths", ())]
        if not all(isinstance(path, str) and path for path in artifact_paths):
            errors.append(f"task {task_id} has an invalid visible canonical artifact path")
            continue
        for path in artifact_paths:
            if path == ".planning/STATE.md" or path.startswith(".planning/phases/"):
                errors.append(f"task {task_id} writes a GSD-owned path while roadmap provider is none")
            elif path.startswith(".planning/") and not path.startswith(".planning/devflow/"):
                errors.append(f"task {task_id} writes a non-namespaced DevFlow planning path")
        oracle = task_oracles.get(task_id, {})
        oracle_artifacts = set(oracle.get("requiredArtifacts", {}))
        if oracle_artifacts != set(artifact_paths):
            errors.append(f"task {task_id} private and visible canonical artifact sets differ")
        required_changes = set(oracle.get("requiredChanges", {}))
        allowed_changes = set(oracle.get("allowedChanges", ()))
        common_outputs = {
            ".benchmark/result.json",
            ".benchmark/route-evidence.json",
            ".benchmark/task-output.json",
        }
        expected_changes = common_outputs | set(artifact_paths)
        if required_changes != expected_changes or allowed_changes != expected_changes:
            errors.append(f"task {task_id} diff contract does not exactly cover its declared outputs")
    compatibility_paths = {
        "openspec/changes/config-key-compatibility/proposal.md",
        "openspec/changes/config-key-compatibility/design.md",
        "openspec/changes/config-key-compatibility/specs/config-key-compatibility/spec.md",
        "openspec/changes/config-key-compatibility/tasks.md",
    }
    compatibility = output_schemas.get("compatibility-plan", {})
    declared = {
        compatibility.get("artifactPath"),
        *compatibility.get("additionalArtifactPaths", ()),
    }
    if declared != compatibility_paths:
        errors.append("compatibility-plan must declare the complete Full OpenSpec artifact set")
    return errors


def _validate_one(
    config: dict,
    expected_profile: str,
    cwd: Path,
    config_path: Path,
) -> tuple[dict, list[str]]:
    errors: list[str] = []
    benchmark = config.get("devflowBenchmark", {})
    if config.get("kind") != "plugin-eval-benchmark" or config.get("schemaVersion") != 2:
        errors.append("config must use Plugin Eval benchmark schema version 2")
    if config.get("runner", {}).get("type") != "codex-cli":
        errors.append("runner.type must be codex-cli")
    if benchmark.get("profile") != expected_profile:
        errors.append(f"expected profile {expected_profile}")
    if benchmark.get("roadmapProvider") != "none":
        errors.append("provider outcome benchmark must isolate roadmapProvider=none")
    if config.get("workspace", {}).get("setupMode") != "copy":
        errors.append("workspace.setupMode must be copy")
    if config.get("workspace", {}).get("preserve") != "never":
        errors.append("workspace.preserve must be never")
    if config.get("targetProvisioning", {}).get("mode") != "workspace-plugin-marketplace":
        errors.append("targetProvisioning.mode must be workspace-plugin-marketplace")
    if config.get("verifiers", {}).get("commands") != ["python3 .benchmark/verify.py"]:
        errors.append("benchmark must use the isolated machine verifier")

    scenarios = config.get("scenarios")
    if not isinstance(scenarios, list):
        scenarios = []
        errors.append("scenarios must be a list")
    task_ids = [item.get("id") for item in scenarios if isinstance(item, dict)]
    if task_ids != list(REQUIRED_TASK_IDS):
        errors.append("scenario IDs must match the fixed ten-task corpus in canonical order")
    high_risk = {
        item.get("id")
        for item in scenarios
        if isinstance(item, dict) and item.get("highRisk") is True
    }
    if high_risk != HIGH_RISK_TASK_IDS:
        errors.append("high-risk task classification does not match the benchmark contract")
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            continue
        prompt = scenario.get("userInput")
        if not isinstance(prompt, str) or not prompt.strip():
            errors.append(f"scenario {scenario.get('id')} has no neutral prompt")
            continue
        if expected_profile in prompt or "Superpowers" in prompt or "Matt" in prompt:
            errors.append(f"scenario {scenario.get('id')} prompt names a compared provider")
        if scenario.get("promptSha256") != _prompt_sha256(prompt):
            errors.append(f"scenario {scenario.get('id')} prompt hash mismatch")
        capability = scenario.get("expectedCapability")
        mapped_skills = CAPABILITY_SKILLS[expected_profile].get(capability)
        if not mapped_skills or not set(mapped_skills).issubset(PROFILE_SKILLS[expected_profile]):
            errors.append(f"scenario {scenario.get('id')} has no valid capability-to-skill route")

    fixture = _resolve_fixture(config, cwd)
    task_oracle_path = config_path.parent / "task-oracles.json"
    try:
        task_oracles = _load_task_oracles(task_oracle_path)
        task_oracle_sha = _sha256_file(task_oracle_path)
    except ValueError as exc:
        errors.append(str(exc))
        task_oracles = {}
        task_oracle_sha = ""
    if (fixture / ".benchmark" / "task-oracles.json").exists():
        errors.append("private task oracle must not be copied into the model-visible fixture")
    if task_oracles:
        errors.extend(validate_task_contracts(fixture, task_oracles))
    allowlist = tuple(benchmark.get("fixtureParity", {}).get("allowlistedPaths", ()))
    if allowlist != PARITY_ALLOWLIST:
        errors.append("fixture parity allowlist differs from the provider-only contract")
    try:
        base_sha = tree_sha256(fixture, allowlist)
    except ValueError as exc:
        errors.append(str(exc))
        base_sha = ""
    if benchmark.get("fixtureParity", {}).get("baseWorkspaceSha256") != base_sha:
        errors.append("recorded base workspace hash does not match the fixture")

    skill_root = fixture / ".agents" / "skills"
    try:
        skill_sha = tree_sha256(skill_root)
    except ValueError as exc:
        errors.append(str(exc))
        skill_sha = ""
    route_skill_hashes = {}
    installed_skill_names = (
        sorted(
            path.name
            for path in skill_root.iterdir()
            if path.is_dir() and (path / "SKILL.md").is_file()
        )
        if skill_root.is_dir()
        else []
    )
    if installed_skill_names != sorted(PROFILE_SKILLS[expected_profile]):
        errors.append("fixture skill set does not match the pinned profile capability set")
    for skill_name in PROFILE_SKILLS[expected_profile]:
        skill_path = skill_root / skill_name / "SKILL.md"
        if skill_path.is_file():
            route_skill_hashes[skill_name] = _sha256_file(skill_path)
        else:
            errors.append(f"pinned skill is missing SKILL.md: {skill_name}")
    skill_hashes = {
        skill_name: route_skill_hashes[skill_name]
        for skill_name in LOCKED_PROFILE_SKILLS[expected_profile]
        if skill_name in route_skill_hashes
    }
    lock_path = fixture / ".planning" / "devflow" / "providers.lock.json"
    try:
        provider_lock = _load_json(lock_path)
    except ValueError as exc:
        errors.append(str(exc))
        provider_lock = {}
    provider_id = PROFILE_PROVIDER_IDS[expected_profile]
    locked_providers = provider_lock.get("providers", {}) if isinstance(provider_lock, dict) else {}
    if set(locked_providers) != {provider_id}:
        errors.append("provider lock must contain exactly the selected production provider")
    locked_provider = locked_providers.get(provider_id, {})
    provider_sha = _provider_sha256(locked_provider) if locked_provider else ""
    integrity = benchmark.get("integrity", {})
    lock_skills = locked_provider.get("skillHashes", {})
    if provider_lock.get("schemaVersion") != 1:
        errors.append("provider lock schemaVersion must be 1")
    if integrity.get("providerSha256") != provider_sha:
        errors.append("provider source hash mismatch")
    if lock_skills != skill_hashes:
        errors.append("provider lock skill hashes do not match the pinned fixture skills")
    if integrity.get("skillSha256") != skill_hashes:
        errors.append("config skill hashes do not match the pinned fixture skills")
    if integrity.get("routeSkillSha256") != route_skill_hashes:
        errors.append("config route skill hashes do not match every routed fixture skill")
    prompt_set_sha = _prompt_set_sha256(scenarios)
    if integrity.get("promptSetSha256") != prompt_set_sha:
        errors.append("prompt set hash mismatch")
    if integrity.get("taskOracleSha256") != task_oracle_sha:
        errors.append("private task oracle hash mismatch")
    provider_ref = locked_provider.get("ref") or locked_provider.get("version")
    if integrity.get("providerRef") != provider_ref:
        errors.append("provider ref mismatch")
    if integrity.get("providerCommit") != locked_provider.get("commit"):
        errors.append("provider commit mismatch")
    source_root_value = locked_provider.get("sourceRoot")
    source_root = (fixture / str(source_root_value)).resolve() if source_root_value else None
    expected_source_root = (
        fixture / ".agents" / "skills"
        if expected_profile == "lean-matt"
        else fixture
        / "codex-home"
        / "plugins"
        / "cache"
        / "openai-curated-remote"
        / "superpowers"
        / "6.1.1"
    )
    if source_root != expected_source_root.resolve():
        errors.append("provider lock sourceRoot does not resolve to the isolated fixture provider root")
    if expected_profile == "strict-superpowers":
        manifest = expected_source_root / ".codex-plugin" / "plugin.json"
        if _sha256_file(manifest) != locked_provider.get("manifestDigest"):
            errors.append("strict provider manifest digest mismatch")
    if benchmark.get("routeEvidence", {}).get("required") is not True:
        errors.append("actual route evidence must be required")
    if benchmark.get("routeEvidence", {}).get("installedOnlyIsInvalid") is not True:
        errors.append("installed-only provider evidence must be invalid")
    if benchmark.get("canonicalEvidence", {}).get("required") is not True:
        errors.append("canonical artifact evidence must be required")
    if not (fixture / "codex-home" / "config.toml").is_file():
        errors.append("fixture must provide an isolated minimal Codex config")

    return (
        {
            "config": config,
            "profile": expected_profile,
            "fixture": fixture,
            "baseSha256": base_sha,
            "promptSetSha256": prompt_set_sha,
            "taskOracleSha256": task_oracle_sha,
            "providerSha256": provider_sha,
            "skillSha256": skill_sha,
            "skillHashes": skill_hashes,
            "routeSkillHashes": route_skill_hashes,
            "scenarios": scenarios,
        },
        errors,
    )


def validate_benchmark_configs(
    strict_path: Path | str,
    lean_path: Path | str,
    *,
    repetitions: int = 3,
    cwd: Path | str | None = None,
) -> dict:
    """Validate controlled inputs without creating temp files or output."""
    cwd_path = Path(cwd or Path.cwd()).resolve()
    strict_path = Path(strict_path).resolve()
    lean_path = Path(lean_path).resolve()
    errors: list[str] = []
    if repetitions != 3:
        errors.append("default-switch evidence requires exactly three repetitions")
    try:
        strict_config = _load_json(strict_path)
        lean_config = _load_json(lean_path)
    except ValueError as exc:
        return {"ok": False, "errors": [str(exc)]}
    strict, strict_errors = _validate_one(strict_config, PROFILES[0], cwd_path, strict_path)
    lean, lean_errors = _validate_one(lean_config, PROFILES[1], cwd_path, lean_path)
    errors.extend(f"strict: {item}" for item in strict_errors)
    errors.extend(f"lean: {item}" for item in lean_errors)

    comparable_fields = (
        ("runner", strict_config.get("runner"), lean_config.get("runner")),
        ("targetProvisioning", strict_config.get("targetProvisioning"), lean_config.get("targetProvisioning")),
        ("verifiers", strict_config.get("verifiers"), lean_config.get("verifiers")),
        (
            "resourceControls",
            strict_config.get("devflowBenchmark", {}).get("resourceControls"),
            lean_config.get("devflowBenchmark", {}).get("resourceControls"),
        ),
        (
            "randomization",
            strict_config.get("devflowBenchmark", {}).get("randomization"),
            lean_config.get("devflowBenchmark", {}).get("randomization"),
        ),
        ("scenarios", strict_config.get("scenarios"), lean_config.get("scenarios")),
    )
    for label, strict_value, lean_value in comparable_fields:
        if strict_value != lean_value:
            errors.append(f"strict and lean {label} must be identical")
    if strict["baseSha256"] != lean["baseSha256"]:
        errors.append("fixture base workspace hashes differ outside provider-only paths")
    if strict["promptSetSha256"] != lean["promptSetSha256"]:
        errors.append("strict and lean neutral prompt hashes differ")
    if strict["taskOracleSha256"] != lean["taskOracleSha256"]:
        errors.append("strict and lean private task oracle hashes differ")

    runner = strict_config.get("runner", {})
    benchmark = strict_config.get("devflowBenchmark", {})
    return {
        "ok": not errors,
        "errors": errors,
        "taskIds": list(REQUIRED_TASK_IDS),
        "highRiskTaskIds": sorted(HIGH_RISK_TASK_IDS),
        "repetitions": repetitions,
        "validRunsPerProfile": len(REQUIRED_TASK_IDS) * repetitions,
        "strictBaseWorkspaceSha256": strict["baseSha256"],
        "leanBaseWorkspaceSha256": lean["baseSha256"],
        "strictPromptSetSha256": strict["promptSetSha256"],
        "leanPromptSetSha256": lean["promptSetSha256"],
        "taskOracleSha256": strict["taskOracleSha256"],
        "providerSha256": {
            PROFILES[0]: strict["providerSha256"],
            PROFILES[1]: lean["providerSha256"],
        },
        "skillSha256": {
            PROFILES[0]: strict["skillHashes"],
            PROFILES[1]: lean["skillHashes"],
        },
        "routeSkillSha256": {
            PROFILES[0]: strict["routeSkillHashes"],
            PROFILES[1]: lean["routeSkillHashes"],
        },
        "fixturePaths": {
            PROFILES[0]: str(strict["fixture"]),
            PROFILES[1]: str(lean["fixture"]),
        },
        "controls": {
            "model": runner.get("model"),
            "sandbox": runner.get("sandbox"),
            "approvalPolicy": runner.get("approvalPolicy"),
            "resourceControls": benchmark.get("resourceControls"),
            "randomization": benchmark.get("randomization"),
        },
        "actualRouteEvidenceRequired": bool(benchmark.get("routeEvidence", {}).get("required")),
    }


def _git_commit(cwd: Path) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(cwd), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _codex_binary_identity(command: str) -> dict:
    if "/" in command:
        candidates = [Path(command).expanduser().resolve()]
    else:
        candidates = []
        for directory in os.environ.get("PATH", "").split(os.pathsep):
            candidate = (Path(directory or ".") / command).resolve()
            if candidate.is_file() and candidate not in candidates:
                candidates.append(candidate)
    if not candidates:
        raise ValueError(f"Codex executable cannot be resolved: {command}")
    failures = []
    for candidate in candidates:
        version_result = subprocess.run(
            [str(candidate), "--version"],
            text=True,
            capture_output=True,
            check=False,
        )
        version = (version_result.stdout or version_result.stderr).strip().splitlines()
        if version_result.returncode == 0 and version:
            return {
                "path": str(candidate),
                "sha256": _sha256_file(candidate),
                "version": version[-1],
            }
        failures.append(str(candidate))
    raise ValueError(f"Codex executable version probe failed for all PATH candidates: {failures}")


class BenchmarkInputDriftError(ValueError):
    """Raised when a live benchmark no longer matches its validated dry-run inputs."""


def _benchmark_input_hashes(
    plugin_root: Path,
    config_paths: dict[str, Path],
    validation: dict,
    codex_command: str,
) -> dict:
    task_oracle_paths = {path.parent / "task-oracles.json" for path in config_paths.values()}
    if len(task_oracle_paths) != 1:
        raise ValueError("strict and lean configs must share one runner-private task oracle")
    task_oracle_path = task_oracle_paths.pop().resolve()
    fixtures = {
        profile: Path(validation["fixturePaths"][profile]).resolve()
        for profile in PROFILES
    }
    return {
        "plugin": {
            "path": str(plugin_root),
            "sha256": tree_sha256(
                plugin_root,
                ("**/.plugin-eval/**", "**/__pycache__/**"),
            ),
        },
        "configs": {
            profile: {
                "path": str(config_paths[profile]),
                "sha256": _sha256_file(config_paths[profile]),
            }
            for profile in PROFILES
        },
        "fixtures": {
            profile: {
                "path": str(fixtures[profile]),
                "sha256": tree_sha256(fixtures[profile]),
            }
            for profile in PROFILES
        },
        "taskOracle": {
            "path": str(task_oracle_path),
            "sha256": _sha256_file(task_oracle_path),
        },
        "codexBinary": _codex_binary_identity(codex_command),
    }


def _assert_benchmark_inputs_unchanged(
    args: argparse.Namespace,
    plan: dict,
) -> None:
    expected = plan.get("inputHashes")
    if not isinstance(expected, dict):
        raise BenchmarkInputDriftError("benchmark input drift: plan has no frozen input hashes")
    configs = {
        PROFILES[0]: Path(args.strict_config).resolve(),
        PROFILES[1]: Path(args.lean_config).resolve(),
    }
    codex = expected.get("codexBinary", {})
    codex_path = codex.get("path") if isinstance(codex, dict) else None
    if not isinstance(codex_path, str) or not codex_path:
        raise BenchmarkInputDriftError("benchmark input drift: plan has no frozen Codex binary")
    try:
        actual = _benchmark_input_hashes(
            Path(args.plugin_root).resolve(),
            configs,
            plan["validation"],
            codex_path,
        )
    except (OSError, ValueError, KeyError) as exc:
        raise BenchmarkInputDriftError(f"benchmark input drift: {exc}") from exc
    if actual != expected:
        changed = sorted(
            key
            for key in set(expected) | set(actual)
            if expected.get(key) != actual.get(key)
        )
        raise BenchmarkInputDriftError(
            f"benchmark input drift: changed input groups {changed}"
        )


def _schedule(repetitions: int, seed: str) -> list[dict]:
    entries = [
        {"profile": profile, "task_id": task_id, "repetition": repetition}
        for profile in PROFILES
        for task_id in REQUIRED_TASK_IDS
        for repetition in range(1, repetitions + 1)
    ]
    seed_value = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    random.Random(seed_value).shuffle(entries)
    for index, entry in enumerate(entries, 1):
        entry["order"] = index
    return entries


def build_dry_run_plan(
    plugin_root: Path | str,
    strict_config: Path | str,
    lean_config: Path | str,
    *,
    repetitions: int,
    output_root: Path | str,
    cwd: Path | str | None = None,
    plugin_eval_command: str = "plugin-eval",
    codex_executable: str = "codex",
) -> dict:
    cwd_path = Path(cwd or Path.cwd()).resolve()
    plugin_root = Path(plugin_root).resolve()
    strict_config = Path(strict_config).resolve()
    lean_config = Path(lean_config).resolve()
    validation = validate_benchmark_configs(
        strict_config,
        lean_config,
        repetitions=repetitions,
        cwd=cwd_path,
    )
    if not validation.get("ok"):
        raise ValueError("; ".join(validation.get("errors", [])))
    if not plugin_root.is_dir():
        raise ValueError(f"plugin root does not exist: {plugin_root}")
    seed = validation["controls"]["randomization"]["seed"]
    base_command = shlex.split(plugin_eval_command)
    codex_identity = _codex_binary_identity(codex_executable)
    config_paths = {PROFILES[0]: strict_config, PROFILES[1]: lean_config}
    input_hashes = _benchmark_input_hashes(
        plugin_root,
        config_paths,
        validation,
        codex_identity["path"],
    )
    if input_hashes["codexBinary"] != codex_identity:
        raise ValueError("Codex executable changed while the benchmark plan was being built")
    commands = {}
    for profile in PROFILES:
        fixture_home = Path(validation["fixturePaths"][profile]) / "codex-home"
        environment = (
            f"PLUGIN_EVAL_CODEX_HOME_SOURCE={shlex.quote(str(fixture_home))} "
            f"PLUGIN_EVAL_CODEX_EXECUTABLE={shlex.quote(codex_identity['path'])}"
        )
        plugin_command = shlex.join(
            base_command
            + ["benchmark", str(plugin_root), "--config", str(config_paths[profile]), "--format", "json"]
        )
        commands[profile] = f"{environment} {plugin_command}"
    return {
        "kind": "devflow-provider-benchmark-plan",
        "schemaVersion": 1,
        "dryRun": True,
        "writesPerformed": False,
        "externalModelRunsPerformed": False,
        "outputRoot": str(Path(output_root).resolve()),
        "devflowCommit": _git_commit(cwd_path),
        "codexBinary": codex_identity,
        "pluginSha256": input_hashes["plugin"]["sha256"],
        "inputHashes": input_hashes,
        "validation": validation,
        "pluginEvalCommands": commands,
        "schedule": _schedule(repetitions, seed),
    }


def _write_json(path: Path, payload: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _json_bytes(payload)
    path.write_bytes(data)
    return _sha256_bytes(data)


def write_raw_evidence_manifest(
    raw_root: Path,
    run_root: Path,
    *,
    profile: str,
    task_id: str,
    repetition: int,
    semantic: dict,
    additional_artifacts: dict[str, str],
    required_artifacts: dict[str, dict[str, str]] | None = None,
) -> dict:
    """Write the immutable category manifest consumed by the aggregator."""
    missing_categories = set(EVIDENCE_CATEGORIES) - set(semantic)
    if missing_categories:
        raise ValueError(f"raw semantic evidence is missing categories: {sorted(missing_categories)}")
    raw_root.mkdir(parents=True, exist_ok=True)
    raw_root = raw_root.resolve()
    run_root = run_root.resolve()
    seen_paths: set[Path] = set()
    for relative_path, expected_sha in additional_artifacts.items():
        if not isinstance(relative_path, str) or not relative_path or Path(relative_path).is_absolute():
            raise ValueError("raw additional artifact path must be relative")
        artifact_path = (run_root / relative_path).resolve()
        try:
            artifact_path.relative_to(run_root)
        except ValueError as exc:
            raise ValueError("raw additional artifact path escapes run root") from exc
        if artifact_path in seen_paths:
            raise ValueError("raw additional artifact paths must resolve uniquely")
        seen_paths.add(artifact_path)
        if (
            not artifact_path.is_file()
            or not isinstance(expected_sha, str)
            or len(expected_sha) != 64
            or _sha256_file(artifact_path) != expected_sha
        ):
            raise ValueError(f"raw additional artifact is missing or hash-invalid: {relative_path}")
    evidence_path = raw_root / "semantic-evidence.json"
    evidence_sha = _write_json(evidence_path, semantic)
    relative_evidence = evidence_path.relative_to(run_root).as_posix()
    manifest = {
        "kind": "devflow-provider-benchmark-raw-manifest",
        "schema_version": 1,
        "profile": profile,
        "task_id": task_id,
        "repetition": repetition,
        "artifacts": {
            category: {"path": relative_evidence, "sha256": evidence_sha}
            for category in EVIDENCE_CATEGORIES
        },
        "additionalArtifacts": dict(sorted(additional_artifacts.items())),
        "requiredArtifacts": dict(sorted((required_artifacts or {}).items())),
    }
    manifest_path = raw_root / "manifest.json"
    manifest_sha = _write_json(manifest_path, manifest)
    return {
        "path": manifest_path.relative_to(run_root).as_posix(),
        "sha256": manifest_sha,
    }


def _read_json_if_present(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _safe_existing_descendant(value: object, allowed_root: Path) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    candidate = Path(value).resolve()
    try:
        relative_candidate = candidate.relative_to(allowed_root.resolve())
    except ValueError:
        return None
    if not relative_candidate.parts or not candidate.is_file():
        return None
    return candidate


def _trace_invoked_skills(
    trace_path: Path | None,
    expected_skills: set[str],
) -> tuple[list[str], str | None, int]:
    if trace_path is None:
        return [], None, 0
    invoked = set()
    event_count = 0
    for line in trace_path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        event_count += 1
        item = event.get("item") if isinstance(event.get("item"), dict) else {}
        # Codex exec --json exposes shell tools as completed command_execution items.
        if event.get("type") != "item.completed" or item.get("type") != "command_execution":
            continue
        if item.get("status") != "completed" or item.get("exit_code") != 0:
            continue
        command = str(item.get("command") or "").replace("\\", "/")
        if re.search(r"(?:^|[;&|()\s])(?:cat|sed|head|tail|awk|rg|grep|bat)\s", command) is None:
            continue
        for skill_name in expected_skills:
            if f"/{skill_name}/SKILL.md" in command:
                invoked.add(skill_name)
    return sorted(invoked), _sha256_file(trace_path), event_count


def extract_execution_evidence(
    result_path: Path,
    raw_root: Path,
    *,
    allowed_temp_root: Path,
    allowed_trace_root: Path,
    expected_route: dict,
) -> tuple[dict, dict, Path | None]:
    plugin_result = _read_json_if_present(result_path) or {}
    scenario = next(iter(plugin_result.get("scenarios", [])), {})
    workspace_value = scenario.get("workspacePath") if isinstance(scenario, dict) else None
    workspace = None
    if workspace_value:
        candidate = Path(workspace_value).resolve()
        allowed_root = allowed_temp_root.resolve()
        try:
            relative_candidate = candidate.relative_to(allowed_root)
        except ValueError:
            relative_candidate = None
        if relative_candidate is not None and relative_candidate.parts and candidate.is_dir():
            workspace = candidate
    result_evidence = None
    task_output = None
    agent_route_claim = None
    if workspace is not None and workspace.is_dir():
        result_evidence = _read_json_if_present(workspace / ".benchmark" / "result.json")
        task_output = _read_json_if_present(workspace / ".benchmark" / "task-output.json")
        agent_route_claim = _read_json_if_present(workspace / ".benchmark" / "route-evidence.json")
        if result_evidence is not None:
            _write_json(raw_root / "workspace-result.json", result_evidence)
        if task_output is not None:
            _write_json(raw_root / "workspace-task-output.json", task_output)
        if agent_route_claim is not None:
            _write_json(raw_root / "workspace-route-evidence.json", agent_route_claim)
    result_evidence = result_evidence or {}
    telemetry_source = scenario.get("telemetry", {}) if isinstance(scenario, dict) else {}
    usage = scenario.get("usage") if isinstance(scenario, dict) else None
    telemetry = None
    if isinstance(usage, dict):
        telemetry = {
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "tool_calls": telemetry_source.get("toolCallCount"),
            "elapsed_seconds": (
                float(scenario.get("durationMs")) / 1000.0
                if isinstance(scenario.get("durationMs"), (int, float))
                else None
            ),
        }
    canonical = {
        "compliant": None,
        "corruption": None,
        "source": "awaiting-plugin-eval-workspace-diff",
    }
    side_effects = {
        "unauthorized": None,
        "source": "awaiting-plugin-eval-workspace-diff+raw-trace",
    }
    trace_value = scenario.get("rawEventLogPath") if isinstance(scenario, dict) else None
    trace_path = _safe_existing_descendant(trace_value, allowed_trace_root)
    expected_skill_hashes = expected_route.get("skill_sha256", {})
    invoked_skills, trace_sha, trace_event_count = _trace_invoked_skills(
        trace_path,
        set(expected_skill_hashes),
    )
    required_skills = set(expected_route.get("required_skills", ()))
    matched_required_skills = sorted(set(invoked_skills) & required_skills)
    route_evidence = {
        "selected_profile": expected_route.get("selected_profile"),
        "provider_installed": True,
        "provider_invoked": bool(matched_required_skills),
        "capability": expected_route.get("capability"),
        "provider_sha256": expected_route.get("provider_sha256"),
        "invoked_skills": invoked_skills,
        "required_skills": sorted(required_skills),
        "matched_required_skills": matched_required_skills,
        "skill_sha256": {
            skill_name: expected_skill_hashes[skill_name]
            for skill_name in invoked_skills
        },
        "trace_sha256": trace_sha,
        "trace_event_count": trace_event_count,
        "agent_claim": agent_route_claim,
    }
    verifier_results = scenario.get("verifierResults") if isinstance(scenario, dict) else None
    machine_passed = (
        scenario.get("status") == "completed"
        and isinstance(verifier_results, list)
        and bool(verifier_results)
        and all(result.get("status") == "passed" for result in verifier_results if isinstance(result, dict))
        and all(isinstance(result, dict) for result in verifier_results)
    )
    semantic = {
        "telemetry": telemetry,
        "route": route_evidence,
        "canonical": canonical,
        "side_effects": side_effects,
        "task": {"evidence": task_output},
    }
    normalized = {
        "machine_verifier": {
            "passed": machine_passed,
            "source": "plugin-eval-verifier-results",
        },
        "canonical_artifacts": canonical,
        "side_effects": side_effects,
        "route_evidence": route_evidence,
        "telemetry": telemetry,
        "task_evidence": task_output,
    }
    return semantic, normalized, workspace


def _copy_plugin(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(".plugin-eval", "__pycache__", "*.pyc"),
    )


def _resource_control_violations(telemetry: dict | None, controls: dict) -> list[str]:
    if not isinstance(telemetry, dict):
        return []
    checks = (
        ("total_tokens", "maxTotalTokens"),
        ("tool_calls", "maxToolCalls"),
        ("elapsed_seconds", "maxElapsedSeconds"),
    )
    violations = []
    for telemetry_key, control_key in checks:
        value = telemetry.get(telemetry_key)
        limit = controls.get(control_key)
        if isinstance(value, (int, float)) and isinstance(limit, (int, float)) and value > limit:
            violations.append(f"{telemetry_key}_exceeded")
    return violations


def normalize_run_id(value: str) -> str:
    if not value or value in {".", ".."} or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value) is None:
        raise ValueError("run ID must be a single safe path segment of at most 128 characters")
    return value


def execute_plan(
    args: argparse.Namespace,
    plan: dict,
    *,
    process_runner=subprocess.run,
) -> dict:
    configs = {
        PROFILES[0]: Path(args.strict_config).resolve(),
        PROFILES[1]: Path(args.lean_config).resolve(),
    }
    plugin_root = Path(args.plugin_root).resolve()
    _assert_benchmark_inputs_unchanged(args, plan)
    task_oracle_paths = {path.parent / "task-oracles.json" for path in configs.values()}
    if len(task_oracle_paths) != 1:
        raise ValueError("strict and lean configs must share one runner-private task oracle")
    task_oracles = _load_task_oracles(task_oracle_paths.pop())
    _assert_benchmark_inputs_unchanged(args, plan)

    output_root = Path(args.output_root).resolve()
    output_root_existed = output_root.exists()
    run_id = normalize_run_id(args.run_id or dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    run_root = output_root / run_id
    if run_root.exists():
        raise ValueError(f"benchmark run output already exists: {run_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    run_root.mkdir(parents=True)

    def assert_live_inputs() -> None:
        try:
            _assert_benchmark_inputs_unchanged(args, plan)
        except BenchmarkInputDriftError:
            shutil.rmtree(run_root, ignore_errors=True)
            if not output_root_existed:
                try:
                    output_root.rmdir()
                except OSError:
                    pass
            raise

    command_prefix = shlex.split(args.plugin_eval_command)
    executed = []
    with tempfile.TemporaryDirectory(prefix="devflow-provider-benchmark-") as temp:
        temp_root = Path(temp)
        for scheduled in plan["schedule"]:
            assert_live_inputs()
            profile = scheduled["profile"]
            task_id = scheduled["task_id"]
            repetition = scheduled["repetition"]
            slug = f"{scheduled['order']:03d}-{profile}-{task_id}-r{repetition}"
            raw_root = run_root / "raw" / slug
            item_temp = temp_root / slug
            plugin_eval_temp_root = item_temp / "plugin-eval-temp"
            plugin_eval_temp_root.mkdir(parents=True)
            target_root = item_temp / "dev-flow"
            _copy_plugin(plugin_root, target_root)
            fixture_source = Path(plan["validation"]["fixturePaths"][profile]).resolve()
            fixture_snapshot = item_temp / "fixture"
            shutil.copytree(fixture_source, fixture_snapshot)
            config = _load_json(configs[profile])
            scenario = next(item for item in config["scenarios"] if item["id"] == task_id)
            config["scenarios"] = [scenario]
            fixture_path = fixture_snapshot
            config["workspace"]["sourcePath"] = str(fixture_path)
            config["workspace"]["preserve"] = "always"
            runtime_config = item_temp / "benchmark.json"
            _write_json(runtime_config, config)
            assert_live_inputs()
            raw_root.mkdir(parents=True)
            result_path = raw_root / "plugin-eval-result.json"
            usage_path = raw_root / "usage.jsonl"
            rendered_path = raw_root / "plugin-eval-output.json"
            command = command_prefix + [
                "benchmark",
                str(target_root),
                "--config",
                str(runtime_config),
                "--format",
                "json",
                "--output",
                str(rendered_path),
                "--result-out",
                str(result_path),
                "--usage-out",
                str(usage_path),
            ]
            env = dict(os.environ)
            env["PLUGIN_EVAL_CODEX_HOME_SOURCE"] = str(fixture_path / "codex-home")
            env["PLUGIN_EVAL_CODEX_EXECUTABLE"] = plan["codexBinary"]["path"]
            env["TMPDIR"] = str(plugin_eval_temp_root)
            controls = config["devflowBenchmark"]["resourceControls"]
            timed_out = False
            try:
                completed = process_runner(
                    command,
                    cwd=Path.cwd(),
                    env=env,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=int(controls["maxElapsedSeconds"]) + 60,
                )
            except subprocess.TimeoutExpired as exc:
                timed_out = True

                def timeout_text(value: object) -> str:
                    if isinstance(value, bytes):
                        return value.decode(errors="replace")
                    return value if isinstance(value, str) else ""

                completed = subprocess.CompletedProcess(
                    command,
                    124,
                    timeout_text(exc.output),
                    timeout_text(exc.stderr) or "Plugin Eval scenario timed out",
                )
            assert_live_inputs()
            (raw_root / "stdout.log").write_text(completed.stdout or "")
            (raw_root / "stderr.log").write_text(completed.stderr or "")
            plugin_runs = target_root / ".plugin-eval" / "runs"
            if plugin_runs.is_dir():
                shutil.copytree(plugin_runs, raw_root / "plugin-eval-runs")
            semantic, normalized, workspace = extract_execution_evidence(
                result_path,
                raw_root,
                allowed_temp_root=plugin_eval_temp_root,
                allowed_trace_root=target_root,
                expected_route={
                    "selected_profile": profile,
                    "capability": scenario.get("expectedCapability"),
                    "provider_sha256": plan["validation"]["providerSha256"][profile],
                    "skill_sha256": plan["validation"]["routeSkillSha256"][profile],
                    "required_skills": CAPABILITY_SKILLS[profile][scenario.get("expectedCapability")],
                },
            )
            plugin_result = _read_json_if_present(result_path) or {}
            plugin_scenario = next(iter(plugin_result.get("scenarios", [])), {})
            trace_path = _safe_existing_descendant(
                plugin_scenario.get("rawEventLogPath") if isinstance(plugin_scenario, dict) else None,
                target_root,
            )
            private_evidence = verify_task_artifacts(
                task_id,
                workspace,
                plugin_scenario.get("workspaceChanges") if isinstance(plugin_scenario, dict) else None,
                trace_path,
                task_oracles,
            )
            verifier_path = raw_root / "private-verifier.json"
            _write_json(verifier_path, private_evidence)
            trace_evidence_path = raw_root / "trace.jsonl"
            if trace_path is not None:
                shutil.copy2(trace_path, trace_evidence_path)
            normalized.update(private_evidence)
            semantic["task"]["verifier"] = private_evidence["task_verifier"]
            semantic["canonical"] = private_evidence["canonical_artifacts"]
            semantic["side_effects"] = private_evidence["side_effects"]
            resource_violations = _resource_control_violations(normalized.get("telemetry"), controls)
            normalized["resource_control_violations"] = resource_violations
            normalized["machine_verifier"]["passed"] = (
                normalized["machine_verifier"]["passed"]
                and private_evidence["task_verifier"]["passed"]
                and private_evidence["canonical_artifacts"]["compliant"]
                and not private_evidence["canonical_artifacts"]["corruption"]
                and private_evidence["side_effects"]["unauthorized"] == []
                and normalized["route_evidence"]["provider_invoked"]
                and completed.returncode == 0
                and not resource_violations
            )
            normalized["machine_verifier"]["source"] = (
                "plugin-eval-verifier+private-task-oracle+workspace-diff+raw-trace"
            )
            if workspace is not None:
                for relative_path in task_oracles[task_id].get("requiredArtifacts", {}):
                    artifact = _safe_workspace_artifact(workspace, relative_path)
                    if artifact is not None:
                        destination = raw_root / "workspace-artifacts" / relative_path
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(artifact, destination)
            base_hash_key = (
                "leanBaseWorkspaceSha256"
                if profile == "lean-matt"
                else "strictBaseWorkspaceSha256"
            )
            source_hashes = {
                "repository_sha256": plan["validation"][base_hash_key],
                "prompt_sha256": scenario["promptSha256"],
                "provider_sha256": plan["validation"]["providerSha256"][profile],
                "skill_sha256": plan["validation"]["routeSkillSha256"][profile],
            }
            semantic["source"] = {
                "profile": profile,
                "task_id": task_id,
                "task_class": task_id,
                "repetition": repetition,
                "high_risk": task_id in HIGH_RISK_TASK_IDS,
                "hashes": source_hashes,
            }
            additional_artifacts = {}
            for path in sorted(raw_root.rglob("*")):
                if path.is_file() and path.name not in {"manifest.json", "semantic-evidence.json"}:
                    relative = path.relative_to(run_root).as_posix()
                    additional_artifacts[relative] = _sha256_file(path)
            required_artifact_paths = {
                "plugin_eval_result": result_path,
                "usage": usage_path,
                "verifier": verifier_path,
                "trace": trace_evidence_path,
            }
            required_artifacts = {}
            for category, path in required_artifact_paths.items():
                if not path.is_file():
                    continue
                relative = path.relative_to(run_root).as_posix()
                required_artifacts[category] = {
                    "path": relative,
                    "sha256": additional_artifacts[relative],
                }
            raw_manifest = write_raw_evidence_manifest(
                raw_root,
                run_root,
                profile=profile,
                task_id=task_id,
                repetition=repetition,
                semantic=semantic,
                additional_artifacts=additional_artifacts,
                required_artifacts=required_artifacts,
            )
            normalized_run = {
                "profile": profile,
                "task_id": task_id,
                "task_class": task_id,
                "repetition": repetition,
                "high_risk": task_id in HIGH_RISK_TASK_IDS,
                **normalized,
                "blind_review": None,
                "hashes": source_hashes,
                "raw_manifest": raw_manifest,
            }
            executed.append(
                {
                    **scheduled,
                    "exit_code": completed.returncode,
                    "timed_out": timed_out,
                    "raw_manifest": raw_manifest,
                    "normalized_run_draft": normalized_run,
                }
            )
            shutil.rmtree(plugin_eval_temp_root, ignore_errors=True)
    assert_live_inputs()
    if len(executed) != len(plan["schedule"]):
        status = "execution_interrupted"
    elif any(item["exit_code"] != 0 for item in executed):
        status = "execution_completed_with_failures"
    else:
        status = "awaiting_normalization_and_blind_review"
    result = {
        **plan,
        "dryRun": False,
        "writesPerformed": True,
        "externalModelRunsPerformed": True,
        "runId": run_id,
        "runRoot": str(run_root),
        "status": status,
        "executed": executed,
    }
    _write_json(run_root / "execution-manifest.json", result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate or explicitly execute the controlled DevFlow provider benchmark.",
    )
    parser.add_argument("--plugin-root", required=True)
    parser.add_argument("--strict-config", required=True)
    parser.add_argument("--lean-config", required=True)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--plugin-eval-command", default="plugin-eval")
    parser.add_argument("--codex-executable", default="codex")
    parser.add_argument("--run-id")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--execute-authorized",
        action="store_true",
        help="Required for live Plugin Eval/Codex runs after separate user authorization.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        plan = build_dry_run_plan(
            args.plugin_root,
            args.strict_config,
            args.lean_config,
            repetitions=args.repetitions,
            output_root=args.output_root,
            plugin_eval_command=args.plugin_eval_command,
            codex_executable=args.codex_executable,
        )
        if args.dry_run:
            print(json.dumps(plan, indent=2, sort_keys=True))
            return 0
        if not args.execute_authorized:
            raise ValueError("live benchmark execution requires --execute-authorized after separate user approval")
        result = execute_plan(args, plan)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "awaiting_normalization_and_blind_review" else 1
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
