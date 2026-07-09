# Tasks: Relax Compact Pending Stop Gate

## Target State

Pending compact is an advisory continuation signal, not a default human
interruption gate. DevFlow continues to block invalid, failed, blocked, or
missing checkpoint states.

## Completion Contract

- [x] RED tests demonstrate current pending compact Stop behavior is too strict.
- [x] Pending compact is advisory in direct Stop policy.
- [x] Pending compact is acceptable in aggregate DevFlow Stop checks.
- [x] Failed/blocked/invalid compact states still require action.
- [x] Dev and release guidance are synchronized.
- [x] Focused, full, OpenSpec, and diff checks pass.

## Capability Slices

### Slice 1: RED tests

**Status:** done

**Files / Modules**

- `dev/plugins/dev-flow/tests/test_checkpoint_compact_contract.py`

**Steps**

- [x] Add failing tests for direct Stop policy and aggregate Stop check.
- [x] Run the focused test and confirm it fails for the current blocking
  behavior.

**Validation Command**

```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_checkpoint_compact_contract.py -v
```

### Slice 2: Stop behavior

**Status:** done

**Files / Modules**

- `dev/plugins/dev-flow/scripts/stop_checkpoint_policy.py`
- `dev/plugins/dev-flow/scripts/devflow_stop_hook.py`
- release equivalents under `plugins/dev-flow/scripts/`

**Steps**

- [x] Make direct Stop policy exit 0 for pending compact.
- [x] Make aggregate Stop check treat pending compact as `ok: true` with an
  advisory detail.
- [x] Keep `failed`, `blocked`, and unsupported statuses blocking.

**Validation Command**

```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_checkpoint_compact_contract.py -v
```

### Slice 3: Guidance sync

**Status:** done

**Files / Modules**

- `dev/plugins/dev-flow/skills/checkpoint-compact/SKILL.md`
- `plugins/dev-flow/skills/checkpoint-compact/SKILL.md`

**Steps**

- [x] Update wording so compact recommendation does not imply long-running
  work must stop for human `/compact`.
- [x] Keep stable-boundary prompting and invalid-checkpoint blocking guidance.

**Validation Command**

```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py -k compact
```

### Slice 4: Verification

**Status:** done

**Steps**

- [x] Run focused compact tests.
- [x] Run full dev and release DevFlow tests.
- [x] Run OpenSpec validation.
- [x] Run diff whitespace check.

**Validation Commands**

```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_checkpoint_compact_contract.py -v
python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py -k compact
python3 -m unittest discover -s dev/plugins/dev-flow/tests
python3 -m unittest discover -s plugins/dev-flow/tests
openspec validate relax-compact-pending-stop-gate --strict
openspec validate --all --strict
git diff --check
```

## Execution Ledger

| Slice | Status | Evidence |
|---|---|---|
| RED tests | done | `python3 -m unittest dev/plugins/dev-flow/tests/test_checkpoint_compact_contract.py -v` failed with pending compact still emitting Stop block output and aggregate check returning `ok: false`. |
| Stop behavior | done | Focused test passed after `stop_checkpoint_policy.py` and `devflow_stop_hook.py` changes. |
| Guidance sync | done | Dev guidance changed and release sync reported `status: current` after apply. |
| Verification | done | Evidence recorded under `.planning/verification/20260709035031-*`, `20260709035041-*`, and `20260709035042-*`. |

## Final Verification

- [x] Focused tests pass.
- [x] Full tests pass.
- [x] OpenSpec strict validation passes.
- [x] Diff check passes.

## Verification Evidence

- RED: `python3 -m unittest dev/plugins/dev-flow/tests/test_checkpoint_compact_contract.py -v`
  failed before implementation because pending compact still emitted Stop block
  output and aggregate Stop check returned `ok: false`.
- GREEN focused:
  `python3 -m unittest dev/plugins/dev-flow/tests/test_checkpoint_compact_contract.py -v`
  passed, 5 tests.
- Compact policy focused:
  `python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py -k compact`
  passed, 4 tests.
- Full development tests:
  `python3 -m unittest discover -s dev/plugins/dev-flow/tests -v` passed, 218
  tests.
- Release tests:
  `python3 -m unittest discover -s plugins/dev-flow/tests -v` passed, 9 tests.
- `openspec validate relax-compact-pending-stop-gate --strict` passed.
- `openspec validate --all --strict` passed, 46 items.
- `python3 plugins/dev-flow/scripts/verify_release_runtime.py --plugin-root plugins/dev-flow --repo /Users/cY/dev/skills/cy-codex-skills --json`
  passed with status `verified`.
- `git diff --check` passed.
- Plugin Eval release target `plugins/dev-flow`: score 86/100, grade B,
  0 fail, 3 existing token-budget warnings.
- Local reference dry-run with `/opt/homebrew/bin/python3.12
  dev/scripts/codex_auto_update_plugins_skills.py --repo
  /Users/cY/dev/skills/cy-codex-skills --json` passed and reported installed
  `dev-flow@cy-codex-skills` cache differs from source.

## Deferred Findings

- Plugin Eval token-budget warnings are pre-existing plugin-wide budget work and
  remain outside this compact gate behavior repair.
- Installed Codex cache was not refreshed in this side conversation. Apply a
  local plugin refresh before relying on the new behavior in active Codex
  sessions.
