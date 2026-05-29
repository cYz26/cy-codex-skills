## Context

The technical solution positions abtop, Codex Trace, claude-tap, ccusage, RTK,
and OTel as companion tools. For a complete product, Context Fixer should own
the formal flow through managed profiles while still keeping sensitive capture
explicit and local.

## Goals / Non-Goals

Goals:

- Provide one-command collection profiles.
- Detect external tool availability and health.
- Start owned long-running collectors and stop them after the run.
- Invoke one-shot exporters into a run directory.
- Import produced artifacts into sanitized reports.
- Record per-tool status.

Non-goals:

- Do not install external tools automatically.
- Do not run unmanaged background collectors outside `collect`.
- Do not replace abtop or Codex Trace UIs.
- Do not upload data or enable remote telemetry.

## Decisions

1. **Profiles define behavior.**
   - `quick`: local static/session scan only.
   - `monitor`: lightweight pressure monitoring where available.
   - `trace`: request trace capture and import.
   - `full`: trace, ccusage, OTel, hook ingestion, SQLite save, dashboard data.
2. **Registry-first design.** `tools.py` defines `ManagedTool` records with
   executable candidates, profiles, required profiles, artifact kind, and
   sensitivity.
3. **Run directories.** Managed artifacts go under
   `.context-fixer/runs/<run-id>/`.
4. **Safe process capture.** The runner records stdout/stderr byte counts and
   hashes, not bodies.
5. **Manual imports stay.** Users can still import externally produced trace,
   ccusage, or OTel files for debugging.

## Data Model

`report["external_tools"]`:

```json
{
  "profile": "full",
  "run_id": "2026-05-21T12-00-00",
  "run_dir": ".context-fixer/runs/...",
  "tools": {
    "ccusage": {"status": "ok", "artifact": "ccusage.json"},
    "claude-tap": {"status": "missing", "required": false}
  },
  "artifacts": {}
}
```

## Risks / Trade-offs

- External CLIs change output formats. Mitigation: keep imports tolerant and
  report adapter findings.
- Sensitive trace capture can surprise users. Mitigation: trace capture only in
  trace-enabled profiles and all artifacts stay local.
- Long-running collectors may hang. Mitigation: profile timeout and owned
  process cleanup.

## Migration Plan

1. Add managed tool registry tests.
2. Add collect profile tests with mocked process runner.
3. Implement adapters and runner.
4. Add CLI commands and docs.
5. Run verification.
