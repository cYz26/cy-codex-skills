from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
from typing import Any, Iterable


MATT_SKILL_HASHES = {
    "grilling": "5a35925d03a391bcfa46940868b649b72dba89ec9c19525e785bbb6bd3a7f478",
    "tdd": "5363bb2775679fe9311fbb67947f95359169c6e7f1fac77c0f25e190bca6cf2f",
    "diagnosing-bugs": "7a0779480f323a66d109404646bcc1a14bf0232b45b3e3ea93b652a035718acb",
    "code-review": "6a65cc61114f96db07ec41e3920e67c9c5bf70dd6e0901eb9460ebcb2bdc209f",
    "codebase-design": "a8d50abac5a4018f60e1d911d4b6f4e36454ca14d6c390c0695a578c7de65dad",
    "domain-modeling": "152e2c97239affb12a60c5f4a7e74ab546a49ae169688c81f4e2ccc42dafa579",
}

MATT_LICENSE_FILENAME = "UPSTREAM_LICENSE.txt"

MATT_FILE_HASHES = {
    "UPSTREAM_LICENSE.txt": "0e7ac423bf2c6e223b7c5b156f8cf72da49d748e56a1641402c31f22ad07dbb5",
    "code-review/SKILL.md": "6a65cc61114f96db07ec41e3920e67c9c5bf70dd6e0901eb9460ebcb2bdc209f",
    "codebase-design/DEEPENING.md": "125e6b77413ad2bc7cf7a772bc74336d580a50f9e797db2178ed133d62333d06",
    "codebase-design/DESIGN-IT-TWICE.md": "21c3264953bd30ee87b181a3ccaf0e70649f461e5ffd7dc654acee4ba1788b31",
    "codebase-design/SKILL.md": "a8d50abac5a4018f60e1d911d4b6f4e36454ca14d6c390c0695a578c7de65dad",
    "diagnosing-bugs/SKILL.md": "7a0779480f323a66d109404646bcc1a14bf0232b45b3e3ea93b652a035718acb",
    "diagnosing-bugs/scripts/hitl-loop.template.sh": "b2932630950e5210075bcd6f850e5accf30c101c5367b29eac3a29b4dd8084c8",
    "domain-modeling/ADR-FORMAT.md": "f1f36cd3f8d3b6474ddd5855da4e233bfc4ae1a1c5024909ccf11871819a41b2",
    "domain-modeling/CONTEXT-FORMAT.md": "b8cc318f2a4285b530e908b6bc43901c3c5cd11100362636bbc4216639bef597",
    "domain-modeling/SKILL.md": "152e2c97239affb12a60c5f4a7e74ab546a49ae169688c81f4e2ccc42dafa579",
    "grilling/SKILL.md": "5a35925d03a391bcfa46940868b649b72dba89ec9c19525e785bbb6bd3a7f478",
    "tdd/SKILL.md": "5363bb2775679fe9311fbb67947f95359169c6e7f1fac77c0f25e190bca6cf2f",
    "tdd/mocking.md": "3ceb807fdf4a47d6a93d4d9a891e5ba6d362a6247bd08adc451feebfc17361ef",
    "tdd/tests.md": "859f9e592c188fda4fc7277dd180e4ce9c7a2e13f6efe1f6f29eccc9d28c106a",
}

MATT_PROJECT_FILE_HASHES = {
    **MATT_FILE_HASHES,
    "code-review/SKILL.md": "91a53d4f185d2610c0bb5284348ef71d00519d9d070ccf3929b09ea37b6df222",
    "diagnosing-bugs/SKILL.md": "f2216bf842d37d79b7d503887e5e4d9196f1a42bd94b9de2d174bd5909af2b6a",
}

MATT_ADAPTATIONS = {
    "code-review/SKILL.md": {
        "original": (
            "The issue tracker should have been provided to you — run "
            "`/setup-matt-pocock-skills` if `docs/agents/issue-tracker.md` is missing."
        ),
        "replacement": (
            "The issue or spec source must come from checked-in repository artifacts or the user. "
            "If it is missing, report that boundary; do not invoke setup or issue-tracker bootstrap skills."
        ),
        "reason": "DevFlow/OpenSpec owns intake and tracker boundaries.",
    },
    "diagnosing-bugs/SKILL.md": {
        "original": (
            "**Then ask: what would have prevented this bug?** If the answer involves architectural "
            "change (no good test seam, tangled callers, hidden coupling) hand off to the "
            "`/improve-codebase-architecture` skill with the specifics. Make the recommendation "
            "**after** the fix is in, not before — you have more information now than when you started."
        ),
        "replacement": (
            "**Then ask: what would have prevented this bug?** If the answer involves architectural "
            "change (no good test seam, tangled callers, hidden coupling), record the specifics and "
            "route them through DevFlow's `architecture-guidance` capability after the fix. Do not "
            "hand off to a separate workflow-owning skill."
        ),
        "reason": "DevFlow retains orchestration and architecture-routing ownership.",
    },
}

MATT_SKILLS = tuple(MATT_SKILL_HASHES)

EXCLUDED_MATT_SKILLS = frozenset(
    {
        "ask-matt",
        "setup-matt-pocock-skills",
        "grill-with-docs",
        "to-spec",
        "to-tickets",
        "triage",
        "wayfinder",
        "implement",
        "improve-codebase-architecture",
        "research",
    }
)

CAPABILITY_ROUTES: dict[str, dict[str, Any]] = {
    "decision-resolution": {
        "owner": "openspec",
        "skills": ["grilling"],
        "evidence": "resolved_decisions",
    },
    "implementation-planning": {
        "owner": "openspec",
        "skills": ["change-plan", "ai-native-tech-plan"],
        "evidence": "canonical_plan",
    },
    "test-first-execution": {
        "owner": "devflow",
        "skills": ["tdd"],
        "evidence": "red_green_or_exception",
    },
    "root-cause-diagnosis": {
        "owner": "devflow",
        "skills": ["diagnosing-bugs"],
        "evidence": "root_cause_and_regression_validator",
    },
    "change-review": {
        "owner": "devflow",
        "skills": ["code-review"],
        "evidence": "review_findings_disposition",
    },
    "completion-proof": {
        "owner": "devflow",
        "skills": ["verify-and-archive"],
        "evidence": "fresh_completion_evidence",
    },
    "execution-orchestration": {
        "owner": "devflow",
        "skills": ["execute-task"],
        "evidence": "agent_task_contract",
    },
    "architecture-guidance": {
        "owner": "openspec",
        "skills": ["codebase-design"],
        "evidence": "canonical_design_decisions",
    },
    "domain-language-modeling": {
        "owner": "openspec",
        "skills": ["domain-modeling"],
        "evidence": "canonical_domain_language",
    },
    "goal-definition": {
        "owner": "devflow",
        "skills": ["define-goal"],
        "evidence": "goal_quality_contract",
        "onDemand": True,
    },
}

CAPABILITY_IDS = tuple(CAPABILITY_ROUTES)


def methodology_manifest() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "controlPlane": "devflow-openspec",
        "source": {
            "repository": "mattpocock/skills",
            "ref": "v1.1.0",
            "commit": "d574778f94cf620fcc8ce741584093bc650a61d3",
            "skillHashes": dict(MATT_SKILL_HASHES),
            "fileHashes": dict(MATT_FILE_HASHES),
            "projectSkillHashes": {
                skill: MATT_PROJECT_FILE_HASHES[f"{skill}/SKILL.md"]
                for skill in MATT_SKILLS
            },
            "projectFileHashes": dict(MATT_PROJECT_FILE_HASHES),
            "projectSkillFiles": {
                skill: expected_project_skill_files(skill)
                for skill in MATT_SKILLS
            },
            "adaptations": [
                {"path": path, "reason": adaptation["reason"]}
                for path, adaptation in MATT_ADAPTATIONS.items()
            ],
        },
        "capabilities": deepcopy(CAPABILITY_ROUTES),
    }


def route_capability(capability: str) -> dict[str, Any]:
    try:
        return deepcopy(CAPABILITY_ROUTES[capability])
    except KeyError as error:
        raise ValueError(f"unsupported DevFlow capability: {capability}") from error


def required_matt_skills(capabilities: Iterable[str]) -> list[str]:
    required: set[str] = set()
    requested = set(capabilities)
    unknown = requested.difference(CAPABILITY_ROUTES)
    if unknown:
        raise ValueError(
            "unsupported DevFlow capability: " + ", ".join(sorted(unknown))
        )
    for capability in requested:
        required.update(
            skill
            for skill in CAPABILITY_ROUTES[capability]["skills"]
            if skill in MATT_SKILL_HASHES
        )
    return [skill for skill in MATT_SKILLS if skill in required]


def matt_skill_source_root(plugin_root: Path) -> Path:
    return Path(plugin_root).expanduser().absolute() / "vendor" / "mattpocock-skills"


def diagnose_methodology(
    repo: Path,
    capabilities: Iterable[str],
    plugin_root: Path,
    *,
    codex_home: Path | None = None,
) -> dict[str, Any]:
    repo = Path(repo).resolve()
    required = required_matt_skills(capabilities)
    project_root = repo / ".agents" / "skills"
    global_root = Path(codex_home or Path.home() / ".codex").resolve() / "skills"
    missing: list[str] = []
    nonlocal_skills: list[str] = []
    drifted_files: list[str] = []
    unexpected_files: list[str] = []
    skill_status: dict[str, dict[str, Any]] = {}
    source_verification = verify_matt_vendor(plugin_root, required)
    project_route_nonlocal = any(
        path.is_symlink() for path in (repo / ".agents", project_root)
    )

    for skill in required:
        skill_root = project_root / skill
        expected = expected_project_skill_files(skill)
        if project_route_nonlocal:
            nonlocal_skills.append(skill)
            skill_status[skill] = {"ready": False, "status": "nonlocal"}
            continue
        if not skill_root.is_dir():
            missing.append(skill)
            skill_status[skill] = {"ready": False, "status": "missing"}
            continue
        if skill_root.is_symlink() or not path_is_within(skill_root, project_root):
            nonlocal_skills.append(skill)
            skill_status[skill] = {"ready": False, "status": "nonlocal"}
            continue
        actual_files: dict[str, Path] = {}
        unsafe_entries: list[str] = []
        try:
            paths = list(skill_root.rglob("*"))
        except OSError:
            paths = []
            unsafe_entries.append(f"{skill}/<unreadable-tree>")
        for path in paths:
            relative = path.relative_to(skill_root).as_posix()
            if path.is_symlink():
                unsafe_entries.append(f"{skill}/{relative}")
            elif path.is_file():
                actual_files[relative] = path
            elif not path.is_dir():
                unsafe_entries.append(f"{skill}/{relative}")
        skill_drift: list[str] = []
        for relative, digest in expected.items():
            path = actual_files.get(relative)
            display = f"{skill}/{relative}"
            if path is None or path.is_symlink() or file_digest(path) != digest:
                skill_drift.append(display)
        extras = sorted(set(actual_files).difference(expected))
        drifted_files.extend(skill_drift)
        skill_unexpected = [
            *(f"{skill}/{relative}" for relative in extras),
            *unsafe_entries,
        ]
        unexpected_files.extend(skill_unexpected)
        ready = not skill_drift and not skill_unexpected
        skill_status[skill] = {
            "ready": ready,
            "status": "ready" if ready else "source_drift",
        }

    if not source_verification["ready"]:
        status = "vendor_source_drift"
    elif missing:
        status = "missing_project_skills"
    elif nonlocal_skills:
        status = "nonlocal_project_skills"
    elif drifted_files or unexpected_files:
        status = "source_drift"
    else:
        status = "ready"
    return {
        "ready": status == "ready",
        "status": status,
        "requiredSkills": required,
        "skills": skill_status,
        "missingSkills": missing,
        "nonLocalSkills": nonlocal_skills,
        "driftedFiles": sorted(drifted_files),
        "unexpectedFiles": sorted(unexpected_files),
        "projectRoot": str(project_root),
        "globalRoot": str(global_root),
        "globalSkills": {
            skill: (global_root / skill / "SKILL.md").is_file()
            for skill in required
        },
        "source": methodology_manifest()["source"],
        "sourceVerification": source_verification,
    }


def verify_matt_vendor(
    plugin_root: Path,
    skills: Iterable[str] | None = None,
) -> dict[str, Any]:
    requested = set(MATT_SKILLS if skills is None else skills)
    unknown = requested.difference(MATT_SKILLS)
    if unknown:
        raise ValueError("unsupported Matt skill: " + ", ".join(sorted(unknown)))
    root = matt_skill_source_root(plugin_root)
    plugin_root = Path(plugin_root).expanduser().absolute()
    source_parents = (plugin_root, plugin_root / "vendor", root)
    untrusted_parents = [str(path) for path in source_parents if path.is_symlink()]
    expected = {
        relative: digest
        for relative, digest in MATT_FILE_HASHES.items()
        if relative == MATT_LICENSE_FILENAME
        or relative.split("/", 1)[0] in requested
    }
    if not requested:
        expected = {}
    missing: list[str] = []
    drifted: list[str] = []
    unexpected: list[str] = []
    actual: dict[str, Path] = {}
    license_path = root / MATT_LICENSE_FILENAME
    if requested and not untrusted_parents:
        if license_path.is_symlink() or not license_path.is_file():
            missing.append(MATT_LICENSE_FILENAME)
        else:
            actual[MATT_LICENSE_FILENAME] = license_path
    for skill in MATT_SKILLS:
        if skill not in requested:
            continue
        skill_root = root / skill
        if untrusted_parents or skill_root.is_symlink() or not skill_root.is_dir():
            missing.extend(
                relative for relative in expected if relative.startswith(f"{skill}/")
            )
            continue
        for path in skill_root.rglob("*"):
            if path.is_symlink():
                drifted.append(path.relative_to(root).as_posix())
            elif path.is_file():
                actual[path.relative_to(root).as_posix()] = path
            elif not path.is_dir():
                drifted.append(path.relative_to(root).as_posix())
    for relative, digest in expected.items():
        path = actual.get(relative)
        if path is None:
            missing.append(relative)
        elif file_digest(path) != digest:
            drifted.append(relative)
        elif file_digest_bytes(
            adapt_matt_file_bytes(relative, path.read_bytes())
        ) != MATT_PROJECT_FILE_HASHES[relative]:
            drifted.append(relative)
    unexpected.extend(sorted(set(actual).difference(expected)))
    ready = not missing and not drifted and not unexpected
    return {
        "ready": ready,
        "status": "ready" if ready else "source_drift",
        "root": str(root),
        "skills": [skill for skill in MATT_SKILLS if skill in requested],
        "missingFiles": sorted(set(missing)),
        "driftedFiles": sorted(set(drifted)),
        "unexpectedFiles": sorted(set(unexpected)),
        "untrustedParents": untrusted_parents,
    }


def adapt_matt_file_bytes(relative: str, payload: bytes) -> bytes:
    adaptation = MATT_ADAPTATIONS.get(relative)
    if adaptation is None:
        return payload
    text = payload.decode("utf-8")
    original = str(adaptation["original"])
    if text.count(original) != 1:
        raise ValueError(f"Matt adaptation source contract drifted: {relative}")
    return text.replace(original, str(adaptation["replacement"])).encode("utf-8")


def expected_project_skill_files(skill: str) -> dict[str, str]:
    if skill not in MATT_SKILL_HASHES:
        raise ValueError(f"unsupported Matt skill: {skill}")
    expected = {
        relative.removeprefix(f"{skill}/"): digest
        for relative, digest in MATT_PROJECT_FILE_HASHES.items()
        if relative.startswith(f"{skill}/")
    }
    expected[MATT_LICENSE_FILENAME] = MATT_FILE_HASHES[MATT_LICENSE_FILENAME]
    return expected


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_digest_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def path_is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False
