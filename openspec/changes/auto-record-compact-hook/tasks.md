# Tasks: Auto-record compact hook

## Target State

DevFlow automatically records completed compact status after Codex emits a manual `PostCompact` event, using the existing compact result writer. The flow is idempotent, privacy-preserving, and packaged in both development and release plugin roots.

## Completion Contract

- [x] Manual `PostCompact` events complete compact result recording when workflow compact status is pending.
- [x] Automatic `PostCompact` events no-op by default.
- [x] Recovery uses the existing compact result writer and updates `.planning/STATE.md`.
- [x] Non-pending state and missing checkpoint files are safe no-ops.
- [x] Dev and release hooks package the new recovery hook.
- [x] OpenSpec validation and focused test suites pass.

## Capability Slices

### Slice 1: Hook recovery test surface

**Status:** done

**Implementation**
- [x] Add failing tests for manual `PostCompact` recovery.
- [x] Add failing tests for automatic `PostCompact` no-op behavior.
- [x] Add failing tests for non-pending state and missing checkpoint no-op behavior.
- [x] Add release smoke assertions for packaged hook entries and importability.

**Validation Commands**
```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_compact_recovery.py
python3 -m unittest plugins/dev-flow/tests/test_release_smoke.py
```

### Slice 2: Compact recovery implementation

**Status:** done

**Implementation**
- [x] Add `workflow_compact_recovery.py` with manual `PostCompact` recovery functions.
- [x] Add `compact_recovery_hook.py` as the stdin JSON hook entry point.
- [x] Wire `PostCompact` hook entries in development and release `hooks.json`.
- [x] Mirror runtime files from `dev/plugins/dev-flow` to `plugins/dev-flow`.

**Validation Commands**
```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_compact_recovery.py
```

### Slice 3: Verification and state update

**Status:** done

**Implementation**
- [x] Run focused and broader DevFlow tests.
- [x] Run `openspec validate --all --strict`.
- [x] Update this task ledger with validation evidence.
- [x] Update `.planning/STATE.md` to reflect this active implementation status without archiving `extract-agent-kb-plugin`.

**Validation Commands**
```bash
python3 -m unittest discover -s dev/plugins/dev-flow/tests
python3 -m unittest discover -s plugins/dev-flow/tests
openspec validate --all --strict
```

## Execution Ledger

| Slice | Status | Evidence |
|---|---|---|
| Hook recovery test surface | done | `python3 -m unittest dev/plugins/dev-flow/tests/test_compact_recovery.py` passed after expected red failure for missing `PostCompact` support |
| Compact recovery implementation | done | `python3 -m unittest plugins/dev-flow/tests/test_release_smoke.py` passed |
| Verification and state update | done | dev/release unittest discovery, plugin preflight, and `openspec validate --all --strict` passed |

## Acceptance Criteria

- [x] Manual `PostCompact` completes the pending compact result.
- [x] Automatic `PostCompact` does not complete a manual checkpoint gate by default.
- [x] Completion is checkpoint-validated and idempotent.
- [x] Hook behavior does not parse prompt bodies or transcript files.
- [x] Release package smoke tests cover the new hook surface.

## Validation Commands

```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_compact_recovery.py
python3 -m unittest discover -s dev/plugins/dev-flow/tests
python3 -m unittest discover -s plugins/dev-flow/tests
openspec validate --all --strict
```
