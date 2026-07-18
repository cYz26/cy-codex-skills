---
name: verify-and-archive
description: Use when verifying completed work, preparing a completion claim, or gating OpenSpec archive.
---

# Verify and Archive

Fresh evidence precedes every completion, commit, PR, release, or archive
claim.

## Capability Routing

Resolve `change-review` and `completion-proof` from
`scripts/workflow_methodology.py`. Matt review output supplements but never
replaces canonical OpenSpec and DevFlow evidence.

Diagnose the exact completion route before claiming readiness:

```bash
python3 scripts/check_dependencies.py --repo <repo> \
  --capability change-review --capability completion-proof --json
```

## Verification

Check Target State, Completion Contract, Capability Slices, Execution Ledger,
Acceptance Criteria, exact Validation Commands, changed files, scope, risks,
and rollback. Record results below `.planning/devflow/verification/`.
Methodology notes count only after promotion into canonical artifacts.
Use `openspec status --change <id> --json` and relevant `openspec instructions
<artifact> --change <id> --json`; honor returned `artifactPaths` and
`actionContext`.

## Archive Gate

Run `scripts/archive_status.py --repo <repo> --change <change> --json`.
Archive requires complete tasks, synchronized specs, passing gates, explicit
archive intent, and no unresolved worktree or compatibility risk. Run
`openspec-sync-specs` before `openspec-archive-change` when delta specs exist,
then bind the current delta and main-spec hashes into durable evidence:

```bash
python3 scripts/record_spec_sync.py --repo <repo> --change <change> \
  --command openspec-sync-specs --result pass --json
```

Set `gates.archive_allowed: true` only after the user explicitly authorizes the
archive. That durable authorization does not approve dirty-worktree or
compatibility risks; obtain a separate confirmation for those risks.
Any non-zero OpenSpec validate, sync, or archive result is a blocking failure;
record it and leave the change active rather than bypassing the gate.

If the status reports risk, present it and obtain confirmation. Archive and
release are separate approvals. After verification or archive, checkpoint under
`.planning/devflow/checkpoints/`.

Completion is proven only by commands run in the current worktree and recorded
results; old claims are not evidence.

## Incidental Findings

Before a completion or archive claim, reconcile the tracked Finding Register:

- A `DEFER_AND_CONTINUE` record must show why it does not block the active
  Completion Contract, name current mitigation, and disclose the recommended
  follow-up.
- Any unresolved `BLOCKED_AWAITING_HUMAN` finding blocks continuation,
  completion, verification readiness, release readiness, and archive.
- The completion claim lists residual findings in recommended order and asks
  the human to accept, reject, or defer each follow-up.

Follow-up work must not start from the register or completion message. It needs
normal intake and the applicable approved OpenSpec change or ledger item. A
pending response to optional follow-up does not invalidate an otherwise proven
current completion; it leaves the Human Disposition pending.

Before release promotion, run the checked-in complete source-only suite. It
executes every development module except exactly `test_packaged_runtime.py` and
`test_release_smoke.py`, which require promoted generated assets, and it rejects
skips as well as failures:

```bash
PYTHONDONTWRITEBYTECODE=1 python3.12 dev/scripts/run_devflow_prepromotion_tests.py
```

Then record one current source-bound receipt containing that exact command,
strict repository-wide OpenSpec validation, and `git diff --check`:

```bash
python3 scripts/record_release_verification.py --repo <repo> \
  --target dev-flow --change <change> \
  --development-command 'PYTHONDONTWRITEBYTECODE=1 python3.12 dev/scripts/run_devflow_prepromotion_tests.py' \
  --development-result pass \
  --openspec-command 'openspec validate --all --strict' --openspec-result pass \
  --diff-command 'git diff --check' --diff-result pass --json
```

Release apply additionally requires `gates.release_allowed: true`, set only
after explicit user authorization. A focused pass, stale receipt, incomplete
implementation gate, unverified current change, or command-line `--apply`
alone cannot authorize promotion.

After authorized promotion, run the full development discovery including both
release-dependent modules, plus packaged/runtime checks. The pre-promotion
receipt never substitutes for final full-suite evidence.
