from __future__ import annotations

from pathlib import Path
from typing import Any


CHECK_PHRASES = {
    "global_constraints_preserved": "Global Constraints",
    "interfaces_preserved": "Interfaces",
    "validation_commands_preserved": "Validation Commands",
}


def validate_promotion_record(repo: Path, record: dict[str, Any]) -> dict[str, Any]:
    repo = Path(repo).expanduser().resolve()
    errors: list[str] = []
    source = record.get("source")
    target = record.get("target")
    if not source:
        errors.append("missing source")
    if not target:
        errors.append("missing target")
    source_path = repo / str(source) if source else None
    target_path = repo / str(target) if target else None
    if source_path is not None and not source_path.exists():
        errors.append("source does not exist")
    if target_path is not None and not target_path.exists():
        errors.append("target does not exist")
    target_text = target_path.read_text() if target_path is not None and target_path.exists() else ""
    for check in record.get("requiredChecks", []):
        phrase = CHECK_PHRASES.get(str(check))
        if phrase and phrase not in target_text:
            errors.append(f"{check} failed")
        if check == "no_placeholders" and any(token in target_text for token in ["TBD", "TODO", "implement later"]):
            errors.append("no_placeholders failed")
    return {
        "ok": not errors,
        "errors": errors,
        "source": source,
        "target": target,
        "promotionType": record.get("promotionType"),
        "requiredChecks": list(record.get("requiredChecks", [])),
    }
