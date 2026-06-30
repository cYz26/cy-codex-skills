from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from agent_kb_source_common import already_imported, file_sha256, source_record_id, source_slug
from workflow_paths import repo_path


SUPPORTED_URL_SCHEMES = {"http", "https"}
FEISHU_HOST_MARKERS = ("feishu.cn", "larksuite.com", "larkoffice.com")


def plan_sources(vault: Path, source: str, max_bytes: int):
    parsed = urlparse(source)
    if parsed.scheme and parsed.scheme not in SUPPORTED_URL_SCHEMES:
        return {"planned": [], "warnings": [warning("blocked-url-scheme", source)]}
    if parsed.scheme and is_feishu_host(parsed.netloc):
        return {"planned": [plan_feishu(source)], "warnings": []}
    if parsed.scheme:
        return {"planned": [plan_url(source)], "warnings": []}
    return plan_local(vault, repo_path(source), max_bytes=max_bytes)


def plan_local(vault: Path, path: Path, max_bytes: int):
    if not path.exists():
        return {"planned": [], "warnings": [warning("missing-source", str(path))]}
    paths = local_paths(path)
    planned = [plan_local_file(vault, item, max_bytes) for item in paths]
    warnings = [item["warning"] for item in planned if "warning" in item]
    return {"planned": [item for item in planned if "warning" not in item], "warnings": warnings}


def local_paths(path: Path):
    return sorted(item for item in path.rglob("*") if item.is_file()) if path.is_dir() else [path]


def plan_local_file(vault: Path, path: Path, max_bytes: int):
    size = path.stat().st_size
    if size > max_bytes:
        return {"warning": warning("source-too-large", str(path))}
    content_hash = file_sha256(path)
    source_id = source_record_id("local-file", str(path))
    return {
        "kind": "local-file",
        "path": str(path),
        "title": path.stem,
        "source_id": source_id,
        "content_hash": content_hash,
        "duplicate": already_imported(vault, source_id, content_hash),
        "extension": path.suffix.lower(),
        "size": size,
    }


def plan_url(source: str):
    return {
        "kind": "url",
        "url": source,
        "source_id": source_record_id("url", source),
        "title": source_slug(source),
        "fetch": "crawl4ai-optional",
    }


def plan_feishu(source: str):
    return {
        "kind": "feishu-doc",
        "url": source,
        "source_id": source_record_id("feishu-doc", source),
        "title": source_slug(source),
        "commands": [
            ["lark-cli", "drive", "+inspect", "--url", source, "--format", "json"],
            [
                "lark-cli",
                "docs",
                "+fetch",
                "--api-version",
                "v2",
                "--doc",
                source,
                "--doc-format",
                "markdown",
                "--format",
                "json",
            ],
        ],
    }


def is_feishu_host(host: str):
    return any(marker in host for marker in FEISHU_HOST_MARKERS)


def warning(rule: str, value: str):
    return {"rule": rule, "value": value, "severity": "warning"}
