from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from .onboarding import cache_root

SCHEMA_VERSION = "1"


def default_store_path() -> Path:
    return cache_root() / "history.sqlite3"


def resolve_store_path(path: str | Path | None) -> Path:
    return Path(path).expanduser().resolve() if path else default_store_path()


def init_store(path: str | Path | None = None) -> Path:
    store_path = resolve_store_path(path)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(store_path) as connection:
        connection.execute("create table if not exists metadata (key text primary key, value text not null)")
        connection.execute(
            """
            create table if not exists snapshots (
                id text primary key,
                generated_at text,
                repo text,
                severity text,
                policy_status text,
                source_of_truth text,
                max_input_tokens integer,
                max_context_pct real,
                report_json text not null
            )
            """
        )
        connection.execute("insert or replace into metadata(key, value) values('schema_version', ?)", (SCHEMA_VERSION,))
        connection.execute("create index if not exists snapshots_repo_generated_at on snapshots(repo, generated_at desc)")
    return store_path


def save_report(report: dict[str, Any], path: str | Path | None = None) -> str:
    store_path = init_store(path)
    snapshot_id = str(report.get("snapshot_id") or uuid.uuid4())
    report["snapshot_id"] = snapshot_id
    diagnosis = report.get("diagnosis") or {}
    policy = report.get("context_policy") or {}
    with sqlite3.connect(store_path) as connection:
        connection.execute(
            """
            insert or replace into snapshots(
                id, generated_at, repo, severity, policy_status, source_of_truth,
                max_input_tokens, max_context_pct, report_json
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                report.get("generated_at"),
                report.get("repo"),
                diagnosis.get("severity"),
                policy.get("status"),
                diagnosis.get("source_of_truth"),
                int(diagnosis.get("max_input_tokens") or 0),
                float(diagnosis.get("max_context_pct") or 0.0),
                json.dumps(report, ensure_ascii=False, sort_keys=True),
            ),
        )
    return snapshot_id


def list_snapshots(path: str | Path | None = None, repo: str | Path | None = None, limit: int = 20) -> list[dict[str, Any]]:
    store_path = init_store(path)
    repo_text = str(Path(repo).expanduser().resolve()) if repo else None
    query = (
        "select id, generated_at, repo, severity, policy_status, source_of_truth, "
        "max_input_tokens, max_context_pct, report_json from snapshots"
    )
    params: list[Any] = []
    if repo_text:
        query += " where repo = ?"
        params.append(repo_text)
    query += " order by generated_at desc limit ?"
    params.append(int(limit))
    with sqlite3.connect(store_path) as connection:
        rows = connection.execute(query, params).fetchall()
    return [snapshot_row(row) for row in rows]


def load_snapshot(snapshot_id: str, path: str | Path | None = None) -> dict[str, Any] | None:
    store_path = init_store(path)
    with sqlite3.connect(store_path) as connection:
        row = connection.execute("select report_json from snapshots where id = ?", (snapshot_id,)).fetchone()
    if not row:
        return None
    report = json.loads(row[0])
    report.setdefault("snapshot_id", snapshot_id)
    return report


def snapshot_row(row: tuple[Any, ...]) -> dict[str, Any]:
    report = json.loads(row[8])
    top = ((report.get("budget") or {}).get("top_offenders") or [{}])[0]
    return {
        "id": row[0],
        "generated_at": row[1],
        "repo": row[2],
        "severity": row[3],
        "policy_status": row[4],
        "source_of_truth": row[5],
        "max_input_tokens": int(row[6] or 0),
        "max_context_pct": float(row[7] or 0.0),
        "top_offender": {
            "label": top.get("label"),
            "category": top.get("category"),
            "estimated_tokens": int(top.get("estimated_tokens") or 0),
        },
    }
