# Design: Auto-record compact hook

## Target State

When a DevFlow-managed repository reaches a checkpoint boundary with `compact_status: pending`, the user can run `/compact` manually. Codex emits a `PostCompact` lifecycle event after compaction completes. DevFlow handles the `PostCompact` event when `trigger` is `manual`, verifies the workflow state still needs compact completion, and records a completed compact result through the existing `record_compact_result` path.

The repository files remain the source of truth:

- `.planning/compact-results/<checkpoint-id>.json` stores the compact result.
- `.planning/STATE.md` stores the updated compact status.
- The Codex hook payload is used only as event evidence; transcript files are not parsed.

## Scope / Non-Goals

In scope:

- Handle `PostCompact` hook payloads with `trigger: manual`.
- Resolve the current checkpoint from `.planning/STATE.md`.
- Reuse existing compact result validation and state update logic.
- Make hook behavior idempotent and non-blocking.
- Package the behavior in both development and release DevFlow plugin roots.

Non-goals:

- Do not execute `/compact` from a script.
- Do not parse user prompt text or transcript files to infer compaction.
- Do not handle automatic compaction unless a future change explicitly expands the matcher to `manual|auto`.
- Do not modify unrelated archive state as part of compact recovery.

## Architecture Decisions

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| Use `PostCompact` with matcher `^manual$` | Codex exposes compact completion directly, and `manual` maps to explicit user compaction such as `/compact`. | Detect `/compact` in `UserPromptSubmit`; obsolete now that `PostCompact` is available. |
| Reuse `record_compact_result` | It already validates checkpoint paths, writes result JSON, and updates state consistently. | Duplicate state mutation logic in the hook; higher drift risk. |
| Ignore `auto` trigger by default | DevFlow checkpoint compact gates ask the user to compact intentionally before moving to the next stage. | Treat all compactions as completing the gate; too broad for current workflow policy. |
| Store only a concise raw result summary | Hook payloads may include convenience fields such as transcript path, but transcript format is not a stable protocol. | Parse transcript details; unnecessary and brittle. |

## Data Flow

1. Codex fires `PostCompact` after compact completes.
2. `hooks.json` matches `trigger` with `^manual$` and runs `compact_recovery_hook.py --event post_compact`.
3. The hook reads `.planning/STATE.md`.
4. If `compact_status` is `pending` and the current checkpoint file exists, it calls `record_compact_result(repo, {"status": "completed", "source": "cli", ...})`.
5. `record_compact_result` writes `.planning/compact-results/<checkpoint-id>.json` and updates `.planning/STATE.md`.

## Failure Handling

- Missing `.planning/STATE.md`, missing checkpoint, non-manual trigger, or non-pending compact state returns a no-op report and exits 0.
- If `record_compact_result` reports issues, the hook exits 0 and returns a diagnostic JSON report when invoked with `--json`; normal hook execution does not print noisy output.

## Completion Contract

- [x] Manual `PostCompact` records completed compact status when state is pending and checkpoint exists.
- [x] Automatic `PostCompact` no-ops by default.
- [x] Completed or non-pending state no-ops without writing another compact result.
- [x] Missing checkpoints are no-ops and preserve state.
- [x] Dev and release plugin hook configs include `PostCompact` recovery with matcher `^manual$`.
- [x] Focused dev tests, release smoke tests, and OpenSpec validation pass.

## Capability Slices

### Slice 1: Hook recovery tests

**Goal**
- Capture the expected `PostCompact` behavior before implementation.

**Files / Modules**
- `dev/plugins/dev-flow/tests/test_compact_recovery.py`
- `plugins/dev-flow/tests/test_release_smoke.py`

**Validation Commands**
```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_compact_recovery.py
python3 -m unittest plugins/dev-flow/tests/test_release_smoke.py
```

### Slice 2: Compact recovery implementation

**Goal**
- Implement conservative `PostCompact` recovery behavior and hook entry point.

**Files / Modules**
- `dev/plugins/dev-flow/scripts/workflow_compact_recovery.py`
- `dev/plugins/dev-flow/scripts/compact_recovery_hook.py`
- `dev/plugins/dev-flow/hooks.json`
- Matching release files under `plugins/dev-flow/`

**Validation Commands**
```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_compact_recovery.py
```

### Slice 3: Packaging and workflow verification

**Goal**
- Ensure release packaging, OpenSpec artifacts, and workflow checks remain valid.

**Files / Modules**
- `openspec/changes/auto-record-compact-hook/tasks.md`
- `.planning/STATE.md`
- `plugins/dev-flow/tests/test_release_smoke.py`

**Validation Commands**
```bash
python3 -m unittest discover -s dev/plugins/dev-flow/tests
python3 -m unittest discover -s plugins/dev-flow/tests
openspec validate --all --strict
```
