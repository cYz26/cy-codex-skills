## Why

Context Fixer can record sanitized hook events, but audits cannot yet ingest
those records as first-class evidence. The complete workflow needs hook output
sizes to appear in session growth, activity, and recommendations when the user
or managed collection flow supplies the event file.

## What Changes

- Add parser support for sanitized Context Fixer hook event JSONL.
- Add explicit `--hook-events` analysis input and optional external-record
  inclusion control.
- Convert hook input/output sizes into sanitized contributors and activity
  records.
- Keep default cache records out of audits unless explicitly selected by the
  run profile or CLI input.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `current-system`: add explicit hook event ingestion as sanitized runtime
  evidence.

## Impact

- Affected code: `src/context_fixer/hook_events.py`,
  `src/context_fixer/analyzer.py`, `src/context_fixer/cli.py`, renderers, and
  tests.
- Public CLI: additive `--hook-events` and `--include-external-hook-events`.
- Dependencies: no new production dependency.
- Privacy: only sanitized event records are imported; raw hook payload bodies
  remain omitted.
