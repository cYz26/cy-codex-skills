# Hook Contract

DevFlow hooks are packaged plugin hooks. Commands use `PLUGIN_ROOT` and
`PLUGIN_DATA` semantics supplied by Codex instead of hard-coded versioned cache
paths.

## Rules

- Use `$PLUGIN_ROOT` on Unix-like systems.
- Use `%PLUGIN_ROOT%` through `commandWindows` on Windows.
- Keep Stop hook behavior read-only by default.
- Keep release promotion apply explicit.
- Use event-specific response helpers for advisory, PreToolUse deny, Stop
  continue/block, and permission-request deny payloads.

## Stop Hook

`devflow_stop_hook.py` aggregates:

- context health
- verification evidence
- checkpoint/compact state
- provider-neutral ledger completion status
- release promotion dry-run status

It does not write release assets, planning state, verification evidence, or
archive files by default.
