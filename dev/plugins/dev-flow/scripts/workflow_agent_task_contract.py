from __future__ import annotations

import re
from pathlib import Path
from typing import Any


REQUIRED_SECTIONS = [
    "Goal",
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


def validate_agent_task_contract_text(text: str) -> dict[str, Any]:
    sections = parse_agent_task_contract(text)
    missing = [section for section in REQUIRED_SECTIONS if section not in sections]
    errors: list[str] = []
    for section in missing:
        errors.append(f"Missing required section: {section}.")
    for section in REQUIRED_SECTIONS:
        if section in sections and placeholder_content(sections[section]):
            errors.append(f"{section} contains placeholder content.")

    if "Scope" in sections and not placeholder_content(sections["Scope"]):
        scope_errors = validate_scope(sections["Scope"])
        errors.extend(scope_errors)
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
