from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workflow_paths import rel, sanitize_filename


def now_stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def source_slug(value: str):
    stem = Path(value).stem if not value.startswith(("http://", "https://")) else value.rsplit("/", 1)[-1]
    return sanitize_filename(stem or "source")


def file_sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_sha256(text: str):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def intake_dirs(vault: Path):
    base = vault / "_agent" / "source-intake"
    return {
        "base": base,
        "extracted": base / "extracted",
        "receipts": base / "receipts",
        "registry": base / "sources.jsonl",
    }


def ensure_intake_dirs(vault: Path):
    dirs = intake_dirs(vault)
    for key in ("base", "extracted", "receipts"):
        dirs[key].mkdir(parents=True, exist_ok=True)
    return dirs


def read_registry(vault: Path):
    registry = intake_dirs(vault)["registry"]
    if not registry.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in registry.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def append_registry(vault: Path, record: dict[str, Any]):
    registry = ensure_intake_dirs(vault)["registry"]
    with registry.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def source_record_id(kind: str, identity: str):
    digest = hashlib.sha256(f"{kind}:{identity}".encode("utf-8")).hexdigest()[:16]
    return f"{kind}-{digest}"


def already_imported(vault: Path, source_id: str, content_hash: str):
    return any(
        row.get("source_id") == source_id
        and row.get("content_hash") == content_hash
        and row.get("status") == "imported"
        for row in read_registry(vault)
    )


def write_json_text(path: Path, payload: dict[str, Any]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def relative_payload(vault: Path, payload: dict[str, Any]):
    return {key: rel(vault, value) if isinstance(value, Path) else value for key, value in payload.items()}
