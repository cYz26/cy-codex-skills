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
An active roadmap binding is archived only after both OpenSpec and its bound
phase gates pass. For a selected GSD binding, ingest the canonical UAT artifact
after `gsd-verify-work`:

```bash
python3 dev/plugins/dev-flow/scripts/record_verification.py \
  --repo <repo> --gsd-change <change> --gsd-phase <phase> --json
```

This command resolves `.planning/phases/<phase-dir>/<phase-num>-UAT.md` through
the pinned read-only GSD adapter, verifies complete/pass/no-gap state, and
records its hash. Caller-provided command text or result claims are not GSD
evidence. After OpenSpec is verified and actually archived, preview then
explicitly persist the roadmap-binding lifecycle transition:

```bash
python3 dev/plugins/dev-flow/scripts/archive_roadmap_binding.py \
  --repo <repo> --change <change> --json
python3 dev/plugins/dev-flow/scripts/archive_roadmap_binding.py \
  --repo <repo> --change <change> --apply \
  --authorize-archive-binding --json
```

The first command is always read-only. The second requires canonical-write and
archive authorization and re-checks OpenSpec archive, DevFlow state, and the
current UAT hash before atomically updating `.dev-flow.json`.

If the status reports risk, present it and obtain confirmation. Archive and
release are separate approvals. After verification or archive, checkpoint under
`.planning/devflow/checkpoints/`.

Completion is proven only by commands run in the current worktree and recorded
results; old or provider-authored claims are not evidence.
