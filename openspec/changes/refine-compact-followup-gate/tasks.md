# Tasks: Refine compact follow-up gate

## Target State

DevFlow compact gates are continuation-aware. A checkpoint at a major boundary only blocks on `/compact` when there is a clear next action for the current thread. Completed or stopping-point checkpoints update state immediately with `compact_status: not_needed` and do not wait for PostCompact.

## Completion Contract

- [x] Continuation-required checkpoints still set `compact_status: pending`.
- [x] Review/archive, done, complete, none, and handoff-like checkpoints set `compact_status: not_needed`.
- [x] New checkpoint state resets stale compact result metadata.
- [x] Guidance and templates describe optional compact for stopping points.
- [x] Dev/release tests, OpenSpec, preflight, and installed-cache checks pass.
- [x] Workflow state is updated.

## Capability Slices

### Slice 1: Continuation-aware compact policy

**Status:** done

**Goal**
- Implement and test blocking versus non-blocking compact decisions.

**Files / Modules**
- `dev/plugins/dev-flow/scripts/workflow_compact_policy.py`
- `dev/plugins/dev-flow/scripts/workflow_checkpoint_create.py`
- `dev/plugins/dev-flow/scripts/create_checkpoint.py`
- `dev/plugins/dev-flow/scripts/compact_recommendation.py`
- `dev/plugins/dev-flow/tests/test_project_orchestrator.py`

**Implementation**
- [x] Add continuation inference and explicit CLI overrides.
- [x] Apply continuation policy in checkpoint creation and compact recommendation.
- [x] Reset compact metadata when writing a new checkpoint.

**Tests**
- [x] Add focused tests for continuation-required and stopping-point checkpoints.

**Validation Commands**
```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py -k compact
```

**Done When**
- [x] Focused compact tests pass.

**Risks / Rollback**
- Revert or repair if existing continuation checkpoints stop blocking incorrectly.

### Slice 2: Guidance and release sync

**Status:** done

**Goal**
- Update guidance and release copies.

**Files / Modules**
- `dev/plugins/dev-flow/skills/checkpoint-compact/SKILL.md`
- `dev/plugins/dev-flow/skills/checkpoint-compact/references/boundary-rules.md`
- `dev/plugins/dev-flow/skills/checkpoint-compact/references/compact-policy.md`
- `dev/plugins/dev-flow/assets/templates/CHECKPOINT.md.template`
- `dev/plugins/dev-flow/assets/templates/COMPACT_POLICY.md.template`
- release copies under `plugins/dev-flow/`

**Implementation**
- [x] Explain blocking compact only for continuation-required checkpoints.
- [x] Replace fixed checkpoint compact instruction with generated instruction text.
- [x] Mirror changed files to `plugins/dev-flow`.

**Tests**
- [x] Extend tests for generated checkpoint instruction text.

**Validation Commands**
```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py -k compact
```

**Done When**
- [x] Focused verification passes and release copies match.

**Risks / Rollback**
- Keep guidance conservative if behavior is ambiguous.

### Slice 3: Broader verification and state update

**Status:** done

**Goal**
- Prove the change is complete, durable, and installed locally.

**Files / Modules**
- `.planning/STATE.md`
- `.planning/verification/`
- `openspec/changes/refine-compact-followup-gate/tasks.md`

**Implementation**
- [x] Run broader project verification.
- [x] Refresh installed DevFlow plugin cache and verify changed file hashes.
- [x] Record verification evidence.
- [x] Update workflow state and this ledger.

**Tests**
- [x] Run focused, dev, release, OpenSpec, preflight, and cache checks.

**Validation Commands**
```bash
python3 -m unittest discover -s dev/plugins/dev-flow/tests
python3 -m unittest discover -s plugins/dev-flow/tests
openspec validate --all --strict
python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root dev/plugins/dev-flow --marketplace .agents/plugins/marketplace.dev.json --repo . --json
python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root plugins/dev-flow --marketplace .agents/plugins/marketplace.json --repo . --json
```

**Done When**
- [x] Verification evidence exists, cache is synchronized, and the Completion Contract is checked.

**Risks / Rollback**
- Keep archive blocked until verification evidence is recorded.

## Execution Ledger

| Slice | Status | Evidence |
|---|---|---|
| Continuation-aware compact policy | done | `python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py -k compact`: pass |
| Guidance and release sync | done | Dev/release/cache SHA256 matched for compact policy, checkpoint scripts, templates, skill docs, and README. |
| Broader verification and state update | done | Full dev/release tests, OpenSpec strict validation, preflight, plugin install, and cache hash checks passed. |

## Acceptance Criteria

- [x] Continuation-required checkpoint still blocks on compact.
- [x] Stopping-point checkpoint does not block on compact.
- [x] New checkpoint state does not retain stale compact result metadata.
- [x] Guidance matches the new policy.
- [x] Dev/release/plugin-cache copies are synchronized.

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
