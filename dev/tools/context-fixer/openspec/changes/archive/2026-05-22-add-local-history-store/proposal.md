## Why

The complete Context Fixer product needs history, trends, and cross-session
comparisons. Re-reading sensitive source artifacts for every dashboard view is
unnecessary and risky, so sanitized audit snapshots should be stored locally.

## What Changes

- Add a SQLite-backed local store for sanitized audit snapshots.
- Add `--save` and `--store` options to audit/collect flows.
- Add `history` CLI commands to list and load saved snapshots.
- Store only sanitized report objects and summary indexes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `current-system`: add local sanitized history persistence and history query
  behavior.

## Impact

- Affected code: `src/context_fixer/store.py`,
  `src/context_fixer/cli.py`, `src/context_fixer/analyzer.py`, dashboard code,
  and tests.
- Public CLI: additive `--save`, `--store`, and `history`.
- Dependencies: Python standard-library `sqlite3`.
- Privacy: prompt, message, argument, output, file, and trace bodies are not
  stored.
