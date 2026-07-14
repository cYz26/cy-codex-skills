from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from typing import Any


REQUIRED_SECTIONS = [
    "Goal",
    "Worker ID",
    "Scope",
    "Constraints",
    "Verification",
    "Evidence",
    "Human Gate",
]

PLACEHOLDERS = {
    "",
    "pending",
    "tbd",
    "todo",
    "none",
    "n/a",
    "na",
    "not needed",
    "<pending>",
    "<placeholder>",
}

VAGUE_VERIFICATION = [
    "as needed",
    "run tests",
    "run relevant tests",
    "run appropriate tests",
    "if applicable",
]

WORKER_WRITE_SET_HEADING = re.compile(
    r"^\s*(?:[-*]\s*)?allowed write set for worker\s+`([^`]+)`(?:\s+only)?\s*:\s*(.*)$",
    re.IGNORECASE,
)
GENERIC_WRITE_SET_HEADING = re.compile(
    r"^\s*(?:[-*]\s*)?allowed(?:\s+write set)?\s*:\s*(.*)$",
    re.IGNORECASE,
)
SCOPE_BOUNDARY = re.compile(
    r"^\s*(?:[-*]\s*)?(?:allowed (?!write set for worker)|forbidden|read-only|primary-owned)\b",
    re.IGNORECASE,
)
INLINE_CODE = re.compile(r"`([^`]+)`")
WORKER_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")

PRIMARY_MANAGED_FILES = {
    ".dev-flow.json",
    "AGENTS.md",
    "AGENT_TASK_CONTRACT.md",
    "ENGINEERING_POLICY.md",
    "EVIDENCE_TEMPLATE.md",
    "REVIEW_CHECKLIST.md",
    "TASK_LEDGER.md",
}
PRIMARY_MANAGED_ROOTS = (
    ".codex-plugin",
    ".planning/devflow",
    "openspec",
    "plugins",
)
PRIMARY_MANAGED_COMPONENTS = {".codex-plugin"}


def parse_agent_task_contract(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in text.splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", raw_line)
        if heading:
            title = heading.group(1).strip()
            current = title
            sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(raw_line.rstrip())
    return {section: "\n".join(lines).strip() for section, lines in sections.items()}


def validate_agent_task_contract_file(path: Path) -> dict[str, Any]:
    path = Path(path).expanduser()
    if not path.exists():
        return {
            "ok": False,
            "path": str(path),
            "missingSections": REQUIRED_SECTIONS,
            "errors": [f"Contract file not found: {path}"],
            "sections": {},
        }
    report = validate_agent_task_contract_text(path.read_text())
    report["path"] = str(path)
    return report


def validate_agent_task_contract_files(paths: list[Path]) -> dict[str, Any]:
    reports = [validate_agent_task_contract_file(path) for path in paths]
    scopes: list[dict[str, str]] = []
    worker_contracts: dict[str, list[str]] = {}
    worker_display_names: dict[str, str] = {}
    for report in reports:
        worker = parse_worker_id(report.get("sections", {}).get("Worker ID", ""))
        if worker:
            worker_key = worker.casefold()
            worker_display_names.setdefault(worker_key, worker)
            worker_contracts.setdefault(worker_key, []).append(report["path"])
        scope = report.get("sections", {}).get("Scope", "")
        for write_owner, write_paths in extract_worker_write_sets(scope).items():
            for write_path in write_paths:
                scopes.append(
                    {
                        "contract": report["path"],
                        "worker": write_owner,
                        "path": write_path,
                    }
                )

    overlaps: dict[str, list[dict[str, str]]] = {}
    for index, scope in enumerate(scopes):
        for other in scopes[index + 1 :]:
            if scope["contract"] == other["contract"] and scope["worker"] == other["worker"]:
                continue
            overlap = overlapping_path(scope["path"], other["path"])
            if overlap is None:
                continue
            owners = overlaps.setdefault(overlap, [])
            for candidate in (scope, other):
                owner = {"contract": candidate["contract"], "worker": candidate["worker"]}
                if owner not in owners:
                    owners.append(owner)

    overlap_items = [
        {"path": path, "owners": owners}
        for path, owners in sorted(overlaps.items())
    ]
    duplicate_workers = {
        worker_display_names[worker]: contracts
        for worker, contracts in worker_contracts.items()
        if len(set(contracts)) > 1
    }
    errors = [error for report in reports for error in report["errors"]]
    errors.extend(
        f"Worker id `{worker}` is assigned by multiple contracts: "
        + ", ".join(sorted(set(contracts)))
        for worker, contracts in sorted(duplicate_workers.items())
    )
    errors.extend(
        f"Write path overlap across worker scopes: `{item['path']}`."
        for item in overlap_items
    )
    return {
        "ok": all(report["ok"] for report in reports) and not overlap_items and not duplicate_workers,
        "contracts": reports,
        "overlaps": overlap_items,
        "duplicateWorkers": duplicate_workers,
        "errors": errors,
    }


def validate_agent_task_contract_text(text: str) -> dict[str, Any]:
    sections = parse_agent_task_contract(text)
    missing = [section for section in REQUIRED_SECTIONS if section not in sections]
    errors: list[str] = []
    for section in missing:
        errors.append(f"Missing required section: {section}.")
    for section in REQUIRED_SECTIONS:
        if section in sections and placeholder_content(sections[section]):
            errors.append(f"{section} contains placeholder content.")

    worker_id = parse_worker_id(sections.get("Worker ID", ""))
    if "Worker ID" in sections and not placeholder_content(sections["Worker ID"]):
        if not worker_id or not WORKER_ID.fullmatch(worker_id):
            errors.append(f"Worker ID must match `{WORKER_ID.pattern}`.")

    if "Scope" in sections and not placeholder_content(sections["Scope"]):
        scope_errors = validate_scope(sections["Scope"])
        errors.extend(scope_errors)
        errors.extend(validate_worker_write_sets(sections["Scope"], worker_id=worker_id))
    if "Verification" in sections and not placeholder_content(sections["Verification"]):
        verification_errors = validate_verification(sections["Verification"])
        errors.extend(verification_errors)
    if "Evidence" in sections and not placeholder_content(sections["Evidence"]):
        evidence_errors = validate_evidence(sections["Evidence"])
        errors.extend(evidence_errors)
    if "Human Gate" in sections and not placeholder_content(sections["Human Gate"]):
        human_gate_errors = validate_human_gate(sections["Human Gate"])
        errors.extend(human_gate_errors)

    return {
        "ok": not errors and not missing,
        "missingSections": missing,
        "errors": errors,
        "sections": {section: sections.get(section, "") for section in REQUIRED_SECTIONS},
    }


def placeholder_content(value: str) -> bool:
    normalized = normalize(value)
    if normalized in PLACEHOLDERS:
        return True
    return bool(re.fullmatch(r"<[^>]+>", normalized))


def validate_scope(value: str) -> list[str]:
    normalized = normalize(value)
    errors: list[str] = []
    allowed_markers = ["allowed", "in scope", "write set", "read-only", "inspect", "modify"]
    forbidden_markers = ["forbidden", "out of scope", "do not", "must not", "not modify"]
    if not any(marker in normalized for marker in allowed_markers):
        errors.append("Scope must include allowed files, directories, or read-only areas.")
    if not any(marker in normalized for marker in forbidden_markers):
        errors.append("Scope must include forbidden boundaries.")
    return errors


def validate_worker_write_sets(value: str, *, worker_id: str | None) -> list[str]:
    write_sets = extract_worker_write_sets(value)
    errors: list[str] = []
    worker_ids = worker_write_set_ids(value)
    if generic_write_scope_present(value):
        errors.append(
            "Implementation scope must use a named `Allowed write set for worker <worker-id> only` block; "
            "generic write ownership is not allowed."
        )
    if write_scope_present(value) and not worker_ids:
        errors.append("Implementation scope must name a unique worker id for every write set.")
    if not worker_ids and not write_scope_present(value) and not globally_read_only_scope(value):
        errors.append(
            "A contract without a named write set must explicitly forbid all repository writes."
        )
    duplicates = sorted({worker for worker in worker_ids if worker_ids.count(worker) > 1})
    for worker in duplicates:
        errors.append(f"Worker id `{worker}` is declared more than once in one contract.")
    for owner, paths in write_sets.items():
        if not WORKER_ID.fullmatch(owner):
            errors.append(f"Worker id `{owner}` must match `{WORKER_ID.pattern}`.")
        if not paths:
            errors.append(f"Worker `{owner}` write set must contain at least one exact path.")
        for path in paths:
            if not is_safe_write_path(path):
                errors.append(
                    f"Worker `{owner}` write path must be a normalized "
                    f"repository-relative path: `{path}`."
                )
                continue
            if is_primary_managed_path(path):
                errors.append(f"Worker `{owner}` cannot own primary-managed path `{path}`.")
        if worker_id and owner.casefold() != worker_id.casefold():
            errors.append(
                f"Write set owner `{owner}` must match contract Worker ID `{worker_id}`."
            )
    owners = list(write_sets)
    for index, owner in enumerate(owners):
        for other_owner in owners[index + 1 :]:
            overlaps = {
                overlap
                for path in write_sets[owner]
                for other_path in write_sets[other_owner]
                if (overlap := overlapping_path(path, other_path)) is not None
            }
            for path in sorted(overlaps):
                errors.append(
                    f"Write path overlap: `{path}` is assigned to workers "
                    f"`{owner}` and `{other_owner}`."
                )
    return errors


def extract_worker_write_sets(value: str) -> dict[str, list[str]]:
    write_sets: dict[str, list[str]] = {}
    current_owner: str | None = None
    for line in value.splitlines():
        heading = WORKER_WRITE_SET_HEADING.match(line)
        if heading:
            current_owner = heading.group(1).strip()
            write_sets.setdefault(current_owner, [])
            write_sets[current_owner].extend(extract_paths(heading.group(2)))
            continue
        if current_owner and SCOPE_BOUNDARY.match(line):
            current_owner = None
            continue
        if current_owner:
            write_sets[current_owner].extend(extract_paths(line))
    return write_sets


def worker_write_set_ids(value: str) -> list[str]:
    return [
        match.group(1).strip()
        for line in value.splitlines()
        if (match := WORKER_WRITE_SET_HEADING.match(line))
    ]


def generic_write_scope_present(value: str) -> bool:
    return any(
        (match := GENERIC_WRITE_SET_HEADING.match(line))
        and any(term in match.group(1).lower() for term in ("modify", "write", "edit", "create", "delete"))
        for line in value.splitlines()
    )


def write_scope_present(value: str) -> bool:
    if worker_write_set_ids(value) or generic_write_scope_present(value):
        return True
    negative_continuation = False
    for line in value.splitlines():
        normalized = line.strip().lower()
        if not normalized:
            negative_continuation = False
            continue
        if negative_write_boundary(normalized):
            negative_continuation = True
            continue
        if negative_continuation and normalized.startswith(("and ", "or ")):
            continue
        negative_continuation = False
        if "read-only" in normalized:
            continue
        if positive_write_intent(normalized):
            return True
    return False


def negative_write_boundary(line: str) -> bool:
    normalized = line.lstrip("-* ")
    if normalized.startswith(("forbidden", "out of scope", "primary-owned")):
        return True
    return bool(
        re.search(
            r"\b(?:do not|must not|may not|cannot|can't|never|not allowed to)\b",
            normalized,
        )
    )


def positive_write_intent(line: str) -> bool:
    verbs = (
        r"(?:modify|write|edit|create|delete|change|update|add|remove|replace|"
        r"rename|move|alter|generate|copy|link|install|apply|mutate|touch)"
    )
    subject_permission = re.search(
        rf"\b(?:worker|agent|you)\s+"
        rf"(?:may|can|will|must|should|is allowed to)\s+(?:\w+\s+){{0,3}}{verbs}\b",
        line,
    )
    explicit_scope = line.startswith(("allowed", "- allowed", "in scope", "- in scope"))
    imperative = re.match(rf"^(?:[-*]\s*)?{verbs}\b", line)
    return bool(subject_permission or imperative or (explicit_scope and re.search(rf"\b{verbs}\b", line)))


def globally_read_only_scope(value: str) -> bool:
    normalized = normalize(value)
    if "read-only" not in normalized:
        return False
    global_prohibitions = (
        r"\b(?:no|zero)\s+(?:repository|file)\s+writes?\b",
        r"\ball\s+(?:repository|file)\s+writes?\b",
        r"\bdo not modify any repository path\b",
        r"\bmust not modify any repository path\b",
    )
    if "any other repository path" in normalized:
        return False
    return any(re.search(pattern, normalized) for pattern in global_prohibitions)


def extract_paths(value: str) -> list[str]:
    return [normalize_write_path(match) for match in INLINE_CODE.findall(value) if match.strip()]


def normalize_write_path(value: str) -> str:
    normalized = value.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.rstrip("/")


def is_primary_managed_path(path: str) -> bool:
    candidate = PurePosixPath(path)
    folded_path = path.casefold()
    folded_parts = {part.casefold() for part in candidate.parts}
    return (
        folded_path in {item.casefold() for item in PRIMARY_MANAGED_FILES}
        or any(
            folded_path == root.casefold()
            or folded_path.startswith(f"{root.casefold()}/")
            for root in PRIMARY_MANAGED_ROOTS
        )
        or bool(
            {item.casefold() for item in PRIMARY_MANAGED_COMPONENTS}.intersection(folded_parts)
        )
    )


def is_safe_write_path(path: str) -> bool:
    candidate = PurePosixPath(path)
    return (
        bool(path)
        and path != "."
        and not candidate.is_absolute()
        and ".." not in candidate.parts
        and not any(character in path for character in "*?[]")
        and candidate.as_posix() == path
    )


def overlapping_path(path: str, other_path: str) -> str | None:
    folded_path = path.casefold()
    folded_other = other_path.casefold()
    if folded_path == folded_other:
        return path
    if folded_path.startswith(f"{folded_other}/"):
        return other_path
    if folded_other.startswith(f"{folded_path}/"):
        return path
    return None


def parse_worker_id(value: str) -> str | None:
    candidate = value.strip()
    if candidate.startswith("`") and candidate.endswith("`") and len(candidate) > 2:
        candidate = candidate[1:-1].strip()
    return candidate or None


def validate_verification(value: str) -> list[str]:
    normalized = normalize(value)
    if any(vague == normalized or vague in normalized for vague in VAGUE_VERIFICATION):
        return ["Verification must list concrete commands or a read-only/not-applicable rationale."]
    if ("not applicable" in normalized or "read-only" in normalized) and (
        "report" in normalized or "inspected" in normalized or "residual risks" in normalized
    ):
        return []
    has_backtick_command = "`" in value and any(
        token in normalized
        for token in [
            "python",
            "pytest",
            "unittest",
            "npm",
            "pnpm",
            "yarn",
            "lint",
            "typecheck",
            "build",
            "test",
            "openspec",
        ]
    )
    command_pattern = r"(?m)^\s*(PYTHONDONTWRITEBYTECODE=1\s+)?"
    command_pattern += r"(python3|python|npm|pnpm|yarn|pytest|openspec)\b"
    has_shell_line = bool(re.search(command_pattern, value))
    if has_backtick_command or has_shell_line:
        return []
    return ["Verification must list concrete commands or a read-only/not-applicable rationale."]


def validate_evidence(value: str) -> list[str]:
    normalized = normalize(value)
    required = [
        ("changed files", ["changed files", "files changed"]),
        ("commands run", ["commands run", "commands or tests run", "commands"]),
        ("test logs or validation results", ["test logs", "validation results", "test results"]),
        ("unverified areas", ["unverified areas", "unverified"]),
        ("risk notes", ["risk notes", "residual risks", "risks"]),
    ]
    missing = [label for label, options in required if not any(option in normalized for option in options)]
    return [f"Evidence must require {label}." for label in missing]


def validate_human_gate(value: str) -> list[str]:
    normalized = normalize(value)
    vague = ["review if needed", "as needed", "not needed", "none"]
    if any(item == normalized or item in normalized for item in vague):
        return ["Human Gate must define concrete review triggers."]
    if "review" not in normalized and "wait" not in normalized and "human" not in normalized:
        return ["Human Gate must define concrete review triggers."]
    trigger_markers = [
        "scope",
        "forbidden",
        "public api",
        "compatibility",
        "destructive",
        "validation",
        "failing",
        "unverified",
        "risk",
        "permission",
    ]
    if not any(marker in normalized for marker in trigger_markers):
        return ["Human Gate must define concrete review triggers."]
    return []


def normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())
