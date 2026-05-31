# Design: Refine compact follow-up gate

## Target State

DevFlow checkpointing is continuation-aware. Major boundaries still create durable checkpoints, but compact becomes blocking only when the checkpoint is preparing to continue into a concrete next stage in the current thread. If the task has reached a stopping point, review/archive boundary, completion boundary, or handoff-only state, the checkpoint records `compact_status: not_needed`, updates `.planning/STATE.md` immediately, and does not require a future `PostCompact` event.

## Scope / Non-Goals

- In scope: compact recommendation policy, checkpoint creation, checkpoint templates, compact policy docs, checkpoint skill guidance, tests, release sync, and installed-cache verification.
- Non-goals: removing checkpoint files, removing compact recovery hooks, changing the `/compact` command, or changing public plugin ids.

## Architecture Decisions

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| Infer continuation intent from `next_stage` by default | Existing callers already pass next stage, so this preserves compatibility while making review/archive and completion boundaries non-blocking. | Require every caller to pass a new flag; too disruptive. |
| Add explicit CLI overrides | Ambiguous stages need a way to force blocking or non-blocking compact behavior. | Hard-code all possible stages; brittle. |
| Keep existing compact result statuses | Avoids schema churn and hook changes. Stopping points use `not_needed`. | Add `optional`; would require broad status validation changes. |
| Reset compact result metadata on new checkpoint | Prevents stale `last_compact_result_file` from being attached to a different checkpoint. | Leave old metadata; misleading after skipped/completed previous gates. |

## Completion Contract

- [x] `create_checkpoint.py` supports explicit `--continuation-required` and `--no-continuation-required` flags.
- [x] Major boundary with `next_stage=feature_intake` remains `pending`.
- [x] Major boundary with `next_stage=review_or_archive`, `done`, `complete`, `none`, or handoff-like stages becomes `not_needed`.
- [x] `compact_recommendation.py` returns an optional/non-blocking instruction for no-continuation checkpoints.
- [x] Templates and skills no longer imply that every completed checkpoint must compact before status can be final.

## Capability Slices

### Slice 1: Continuation-aware compact policy

**Goal**
- Add policy helpers and tests for blocking versus non-blocking compact decisions.

**Files / Modules**
- `dev/plugins/dev-flow/scripts/workflow_compact_policy.py`
- `dev/plugins/dev-flow/scripts/workflow_checkpoint_create.py`
- `dev/plugins/dev-flow/scripts/compact_recommendation.py`
- `dev/plugins/dev-flow/scripts/create_checkpoint.py`
- `dev/plugins/dev-flow/tests/test_project_orchestrator.py`

**Implementation**
- [x] Add continuation inference and explicit CLI flags.
- [x] Use continuation intent to decide checkpoint `compact_recommended` and `compact_status`.
- [x] Reset compact metadata when a new checkpoint is created.

**Tests**
- [x] Add red/green tests for feature intake continuation and review/archive stopping point.

**Validation Commands**
```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py -k compact
```

**Done When**
- [x] Focused compact policy tests pass.

**Risks / Rollback**
- Revert the policy helper and CLI flags if existing continuation checkpoints stop blocking incorrectly.

### Slice 2: Guidance and release sync

**Goal**
- Update user-facing DevFlow guidance and release package copies.

**Files / Modules**
- `dev/plugins/dev-flow/skills/checkpoint-compact/SKILL.md`
- `dev/plugins/dev-flow/skills/checkpoint-compact/references/*.md`
- `dev/plugins/dev-flow/assets/templates/CHECKPOINT.md.template`
- `dev/plugins/dev-flow/assets/templates/COMPACT_POLICY.md.template`
- release copies under `plugins/dev-flow/`

**Implementation**
- [x] Explain that compact blocks only when continuing the current thread.
- [x] Make checkpoint compact instruction use generated text rather than a fixed "run /compact" sentence.
- [x] Mirror changed files to release plugin root.

**Tests**
- [x] Extend release smoke or project tests for template/guidance behavior.

**Validation Commands**
```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py -k compact
python3 -m unittest discover -s plugins/dev-flow/tests
```

**Done When**
- [x] Dev and release guidance match.

**Risks / Rollback**
- Keep documentation conservative if the code path is ambiguous.

### Slice 3: Verification and installed cache

**Goal**
- Prove the behavior is packaged and loaded locally.

**Files / Modules**
- `.planning/verification/`
- `.planning/STATE.md`
- `openspec/changes/refine-compact-followup-gate/tasks.md`

**Implementation**
- [x] Run focused, full dev, release, OpenSpec, preflight, and cache checks.
- [x] Record verification evidence.
- [x] Refresh installed DevFlow plugin cache and verify changed file hashes.

**Validation Commands**
```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py -k compact
python3 -m unittest discover -s dev/plugins/dev-flow/tests
python3 -m unittest discover -s plugins/dev-flow/tests
openspec validate --all --strict
python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root dev/plugins/dev-flow --marketplace .agents/plugins/marketplace.dev.json --repo . --json
python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root plugins/dev-flow --marketplace .agents/plugins/marketplace.json --repo . --json
```

**Done When**
- [x] Verification evidence exists and installed cache matches changed packaged files.

## Execution Ledger

Track slice status in `tasks.md`, `.planning/STATE.md`, or a repo-specific ledger file. Mark a slice done only after its validation command passes or a blocker is recorded.

## Capability Evidence

- authoritative/current: local DevFlow workflow behavior; no external capability lookup required.
- local scan: existing compact policy, checkpoint creation, checkpoint templates, hook gates, compact recovery, and tests were inspected.
- comparison: Existing behavior made all major boundaries blocking; selected behavior keeps blocking only for explicit continuation and uses `not_needed` for stopping points.
- assumptions: `review_or_archive`, done/complete/none, and handoff-like stages are stopping points unless an explicit CLI flag says continuation is required.
- contract: OpenSpec scenarios and focused compact tests prove both branches.

## Approach

Implement the smallest compatible policy change: continuation intent is resolved in the compact policy layer, checkpoint creation consumes it, and templates receive pre-rendered instruction text. Existing hooks remain unchanged because they only matter when a checkpoint actually has `compact_status: pending`.

## Data Flow

`create_checkpoint.py` receives `boundary`, `next_stage`, and optional continuation flags. `workflow_compact_policy` determines whether compact is blocking. `workflow_checkpoint_create` writes checkpoint metadata and updates `.planning/STATE.md` with fresh compact metadata. If compact is blocking and `/compact` runs, existing `PostCompact` recovery records completion. If compact is not blocking, no compact result is required.

## Compatibility

Existing continuation checkpoints with concrete next stages still produce `compact_status: pending`. Existing compact recovery, compact result writing, validation, and hooks continue to accept the same statuses. The new flags are additive.

## Testing

Use focused unit tests in `test_project_orchestrator.py` for checkpoint creation, compact recommendation, and template text. Run full dev/release suites and preflight after implementation.

## Acceptance Criteria

- [x] Clear continuation still prompts `/compact` before continuing.
- [x] Stopping-point/review/archive completion does not block state update on compact.
- [x] Checkpoint text tells users compact is optional when no continuation is required.
- [x] New checkpoint state does not retain stale compact result metadata.
- [x] Release and installed cache contain the same behavior.

## Validation Commands

```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py -k compact
python3 -m unittest discover -s dev/plugins/dev-flow/tests
python3 -m unittest discover -s plugins/dev-flow/tests
openspec validate --all --strict
```

## Final Verification

- [x] Focused tests pass.
- [x] Broader tests, lint, typecheck, or build pass where applicable.
- [x] Verification evidence is recorded.
