from __future__ import annotations

import shutil
from pathlib import Path

from agent_kb_extractors import extract_markdown, extractor_capabilities
from agent_kb_scaffold import sanitize_project
from agent_kb_source_common import (
    already_imported,
    append_registry,
    ensure_intake_dirs,
    file_sha256,
    intake_dirs,
    now_stamp,
    source_record_id,
    source_slug,
)
from agent_kb_source_plan import plan_sources
from workflow_paths import rel, repo_path


def import_sources(
    vault: Path,
    project: str,
    source: str,
    apply: bool = False,
    kind: str = "auto",
    max_bytes: int = 10 * 1024 * 1024,
):
    vault = repo_path(vault)
    project = sanitize_project(project)
    plan = plan_sources(vault, source, max_bytes=max_bytes)
    result = intake_result(vault, project, source, apply, plan)
    result["kind"] = kind
    result["max_bytes"] = max_bytes
    if should_apply(apply, result):
        apply_planned_items(vault, project, result)
    return result


def should_apply(apply: bool, result: dict):
    return all([apply, result["ok"]])


def intake_result(vault: Path, project: str, source: str, apply: bool, plan: dict):
    warnings = plan["warnings"]
    return {
        "ok": not warnings,
        "dry_run": not apply,
        "project": project,
        "vault": str(vault),
        "source": source,
        "extractor_capabilities": extractor_capabilities(),
        "planned": plan["planned"],
        "warnings": warnings,
        "imported": [],
        "skipped": [],
    }


def apply_planned_items(vault: Path, project: str, result: dict):
    ensure_intake_dirs(vault)
    for item in result["planned"]:
        if item["kind"] != "local-file":
            result["skipped"].append({"source_id": item["source_id"], "reason": "remote-apply-deferred"})
        elif item["duplicate"]:
            result["skipped"].append({"source_id": item["source_id"], "reason": "duplicate"})
        else:
            result["imported"].append(import_local_file(vault, project, item))


def import_local_file(vault: Path, project: str, item: dict):
    path = Path(item["path"])
    slug = source_slug(path.name)
    raw_path = raw_destination(vault, slug, item["content_hash"], path.suffix)
    shutil.copy2(path, raw_path)
    extracted = write_extracted(vault, slug, item, path)
    summary = write_summary(vault, project, slug, item, raw_path, extracted)
    receipt = write_receipt(vault, slug, item, raw_path, extracted, summary)
    record = registry_record(vault, item, raw_path, extracted, summary, receipt)
    append_registry(vault, record)
    append_log(vault, item, summary)
    return record


def raw_destination(vault: Path, slug: str, content_hash: str, suffix: str):
    target = vault / "raw" / "source-documents" / f"{slug}-{content_hash[:12]}{suffix}"
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def write_extracted(vault: Path, slug: str, item: dict, path: Path):
    extraction = extract_markdown(path)
    target = intake_dirs(vault)["extracted"] / f"{slug}-{item['content_hash'][:12]}.md"
    header = f"---\nextractor: {extraction['extractor']}\nsource_id: {item['source_id']}\n---\n\n"
    target.write_text(header + extraction.get("text", ""), encoding="utf-8")
    item["extractor"] = extraction["extractor"]
    item["extraction_ok"] = extraction["ok"]
    item["needs_review"] = True
    return target


def write_summary(vault: Path, project: str, slug: str, item: dict, raw_path: Path, extracted_path: Path):
    target = vault / "projects" / project / "candidates" / f"{slug}-source-summary.md"
    body = summary_body(project, item, raw_path, extracted_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    return target


def summary_body(project: str, item: dict, raw_path: Path, extracted_path: Path):
    return (
        "---\n"
        f"id: source-{item['source_id']}\n"
        "type: source-summary\n"
        f"project: {project}\n"
        "status: active\n"
        "confidence: medium\n"
        "agent_readable: true\n"
        "agent_writable: true\n"
        f"source_raw: {raw_path.as_posix()}\n"
        f"needs_review: {str(item['needs_review']).lower()}\n"
        "---\n\n"
        f"# {item['title']} Source Summary\n\n"
        f"- Source ID: `{item['source_id']}`\n"
        f"- Raw source: `{raw_path.as_posix()}`\n"
        f"- Extracted Markdown: `{extracted_path.as_posix()}`\n"
        f"- Extractor: `{item['extractor']}`\n\n"
        "Hand this source summary and extracted Markdown to `kb-ingest`.\n"
    )


def write_receipt(vault: Path, slug: str, item: dict, raw_path: Path, extracted_path: Path, summary_path: Path):
    target = intake_dirs(vault)["receipts"] / f"{now_stamp()}-{slug}.md"
    target.write_text(receipt_body(item, raw_path, extracted_path, summary_path), encoding="utf-8")
    return target


def receipt_body(item: dict, raw_path: Path, extracted_path: Path, summary_path: Path):
    return (
        f"# Source Intake Receipt: {item['title']}\n\n"
        f"- source_id: `{item['source_id']}`\n"
        f"- status: imported\n"
        f"- raw_path: `{raw_path.as_posix()}`\n"
        f"- extracted_path: `{extracted_path.as_posix()}`\n"
        f"- summary_path: `{summary_path.as_posix()}`\n"
        f"- extractor: `{item['extractor']}`\n"
    )


def registry_record(
    vault: Path,
    item: dict,
    raw_path: Path,
    extracted_path: Path,
    summary_path: Path,
    receipt_path: Path,
):
    return {
        "source_id": item["source_id"],
        "kind": item["kind"],
        "title": item["title"],
        "status": "imported",
        "content_hash": item["content_hash"],
        "extractor": item["extractor"],
        "needs_review": item["needs_review"],
        "raw_path": rel(vault, raw_path),
        "extracted_path": rel(vault, extracted_path),
        "summary_path": rel(vault, summary_path),
        "receipt_path": rel(vault, receipt_path),
    }


def append_log(vault: Path, item: dict, summary_path: Path):
    log = vault / "knowledge" / "log.md"
    with log.open("a", encoding="utf-8") as handle:
        handle.write(f"- Imported source `{item['source_id']}` into `{rel(vault, summary_path)}`.\n")
