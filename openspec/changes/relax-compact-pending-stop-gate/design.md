# Design: Relax compact pending stop gate

## Target State

DevFlow treats compact as a recoverability advisory unless the compact contract
is actually broken. `compact_status: pending` means compact is recommended and
recoverable; it should not stop a long-running task that can continue from
durable repository state or automatic PostCompact recovery. Stop hooks continue
to fail for invalid, failed, blocked, or missing checkpoint states.

## Scope / Non-Goals

- In scope: Stop hook result severity, direct checkpoint stop policy, compact
  skill wording, focused regression tests, release copy sync.
- Non-goals: status enum changes, new lifecycle events, automatic compact
  invocation, or installed-cache apply in this side conversation.

## Architecture Decisions

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| Keep `pending` as the state value | Existing checkpoint, validation, and PostCompact recovery already understand it. | Add `advisory`; rejected because it creates schema churn. |
| Downgrade Stop hook pending check | This is the layer that interrupts continuation. Context-health can still surface risk. | Change checkpoint creation to avoid pending; rejected because continuation checkpoints should still record compact recommendation. |
| Preserve hard failures for `failed` and `blocked` | Those states indicate compact did not complete cleanly or cannot proceed. | Treat all compact states as advisory; too permissive. |
| Update skill guidance with automatic compact language | Agents follow skill text; the current wording can cause human interruption even when code allows continuation. | Code-only fix; rejected because it leaves process drift. |

## Capability Slices

### Slice 1: RED tests for advisory pending

Add focused tests showing:

- `stop_checkpoint_policy.py` exits 0 for `compact_status: pending`.
- `devflow_stop_hook.checkpoint_stop_check()` returns `ok: true` with advisory
  detail for `pending`.
- `failed` and `blocked` remain `ok: false`.

### Slice 2: Implementation

Update the dev plugin scripts so pending compact is advisory in Stop behavior,
then mirror the same changes to the release plugin root.

### Slice 3: Guidance

Update `checkpoint-compact/SKILL.md` in dev and release roots so agents do not
interrupt otherwise-continuable work solely to prompt for `/compact`.

### Slice 4: Verification

Run focused compact tests, full dev/release DevFlow tests, OpenSpec strict
validation, and diff checks.

## Execution Ledger

| Slice | Status | Evidence |
|---|---|---|
| RED tests for advisory pending | done | `python3 -m unittest dev/plugins/dev-flow/tests/test_checkpoint_compact_contract.py -v` failed before implementation, then passed. |
| Implementation | done | Direct Stop policy and aggregate Stop check treat pending compact as advisory; failed/blocked still require action. |
| Guidance sync | done | `checkpoint-compact` skill and compact policy template now avoid human-interruption wording. |
| Verification | done | Full dev/release tests, OpenSpec all, release runtime verification, Plugin Eval, dry-run local reference check, and diff check passed. |

## Acceptance Criteria

- Pending compact produces an advisory detail, not a Stop-blocking response.
- Failed/blocked compact still fails Stop checks.
- Unsupported compact status remains invalid.
- Skill guidance matches the non-interrupting long-run policy.

## Validation Commands

```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_checkpoint_compact_contract.py -v
python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py -k compact
python3 -m unittest discover -s dev/plugins/dev-flow/tests
python3 -m unittest discover -s plugins/dev-flow/tests
openspec validate relax-compact-pending-stop-gate --strict
openspec validate --all --strict
git diff --check
```

## Risks / Rollback

Rollback is localized: restore pending compact as a blocking Stop hook state in
`stop_checkpoint_policy.py` and `devflow_stop_hook.py`, and restore the older
skill wording. No persistence migration is involved.
