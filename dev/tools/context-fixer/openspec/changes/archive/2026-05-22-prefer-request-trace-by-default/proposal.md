## Why

Context Fixer now supports richer Codex request trace analysis, but the default
CLI still silently falls back to session logs when no trace is supplied. Users
should get the more complete request trace path by default and only use
session-log-only analysis after explicitly choosing that lower-confidence mode.

## What Changes

- Make CLI execution trace-first: `--trace` remains the complete analysis path.
- Add `--session-only` as the explicit opt-in for session logs without request
  trace evidence.
- When neither `--trace` nor `--session-only` is supplied, print setup guidance
  for Codex claude-tap capture and exit without rendering a normal audit report.
- Keep the `analyze_context()` API unchanged for programmatic callers.
- Preserve non-interactive automation by allowing CI and scripts to pass
  `--session-only` explicitly.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `current-system`: CLI request trace attribution becomes the preferred default,
  and session-log-only analysis requires explicit user confirmation via
  `--session-only`.

## Impact

- Affected code: CLI argument handling, onboarding guidance, README, tests.
- Behavior change: `context-fixer --repo <repo>` exits with guidance instead of
  immediately producing a session-only report.
- Backward compatibility: existing scripts must add `--session-only` or pass
  `--trace`.
- Dependencies: no production dependency on claude-tap; no automatic install.
