---
name: verify-and-archive
description: Use when verifying completed work, preparing a completion claim, or gating OpenSpec archive.
---

# Verify and Archive

Fresh evidence precedes every completion, commit, PR, release, or archive
claim.

## Capability Routing

Resolve `change-review` and `completion-proof` from
`docs/provider_profiles.json`. If an active roadmap binding exists, also
resolve `roadmap-lifecycle`. Provider output supplements but never replaces
canonical OpenSpec and DevFlow evidence.

Diagnose the exact completion route before claiming readiness:

```bash
python3 scripts/check_dependencies.py --repo <repo> \
  --capability change-review --capability completion-proof --json
```

Add `--capability roadmap-lifecycle` only when the resolved roadmap provider or
an active binding requires it.

## Verification

Check Target State, Completion Contract, Capability Slices, Execution Ledger,
Acceptance Criteria, exact Validation Commands, changed files, scope, risks,
and rollback. Record results below `.planning/devflow/verification/`. Provider
drafts and review notes count only after promotion into canonical artifacts.
Use `openspec status --change <id> --json` and relevant `openspec instructions
<artifact> --change <id> --json`; honor returned `artifactPaths` and
`actionContext`.

## Archive Gate

Run `scripts/archive_status.py --repo <repo> --change <change> --json`.
Archive requires complete tasks, synchronized specs, passing gates, explicit
archive intent, and no unresolved worktree or compatibility risk. Run
`openspec-sync-specs` before `openspec-archive-change` when delta specs exist.
Any non-zero OpenSpec validate, sync, or archive result is a blocking failure;
record it and leave the change active rather than bypassing the gate.

## Roadmap Binding

An active roadmap binding is archived only after both OpenSpec and its bound
roadmap gates pass. When `roadmap-lifecycle` resolves to a selected binding,
read `references/roadmap-archive.md` before recording or changing it. The
reference defines canonical UAT ingestion, read-only preview, and the separate
explicit binding-archive authorization. Caller-provided result claims are not
roadmap evidence.

If the status reports risk, present it and obtain confirmation. Archive and
release are separate approvals. After verification or archive, checkpoint under
`.planning/devflow/checkpoints/`.

Completion is proven only by commands run in the current worktree and recorded
results; old or provider-authored claims are not evidence.
