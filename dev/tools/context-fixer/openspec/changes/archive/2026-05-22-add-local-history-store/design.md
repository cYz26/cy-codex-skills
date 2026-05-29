## Context

Reports are already sanitized before rendering. The local store persists those
sanitized reports and selected indexed fields so the dashboard can show
historical trends without retaining raw trace/session payload bodies.

## Goals / Non-Goals

Goals:

- Persist sanitized reports in SQLite.
- Query recent snapshots by repository.
- Load a snapshot by id for dashboard display.
- Support explicit store path and a safe default cache path.

Non-goals:

- Do not persist raw session JSONL, raw trace JSONL, raw command output, or raw
  tool arguments.
- Do not run a background database service.
- Do not implement cross-machine sync.

## Decisions

1. **SQLite via stdlib.** No new production dependency is needed.
2. **Sanitized JSON blob plus indexes.** Store the sanitized report as JSON and
   index common dashboard fields.
3. **Schema versioning.** Include a metadata table and schema migration path.
4. **Explicit save.** Audits do not persist unless `--save` or a managed
   profile requests persistence.

## Schema

- `metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL)`.
- `snapshots(id TEXT PRIMARY KEY, generated_at TEXT, repo TEXT, severity TEXT,
  policy_status TEXT, source_of_truth TEXT, max_input_tokens INTEGER,
  max_context_pct REAL, report_json TEXT NOT NULL)`.

## Risks / Trade-offs

- Sanitized report schema may evolve. Mitigation: schema version metadata and
  tolerant loading.
- JSON blobs duplicate some indexed fields. Mitigation: keep first version
  simple and local.

## Migration Plan

1. Add tests for save/list/load.
2. Implement store module.
3. Add CLI integration.
4. Verify privacy and docs.
