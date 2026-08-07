---
checkpoint_id: 2026-08-07-reopened-add-versioned-devflow-project-refresh
created_at: 2026-08-07T11:02:41+08:00
boundary: review-repair-authorized
project_mode: brownfield
change_id: add-versioned-devflow-project-refresh
compact_recommended: false
compact_status: not_needed
next_stage: executing
---

# Checkpoint: reopened add-versioned-devflow-project-refresh

## Current goal

Repair and deliver the existing Project Refresh change through public-seam
RED/GREEN proof, exact generated DevFlow release, direct `origin/main`
submission, and targeted `dev-flow@cy-codex-skills` cache refresh. Goal thread:
`019fda1b-d564-7c40-9d8a-e1fc47c2fe93`.

## Authorization and scope

- The user approved the systemic repair recommended by the pre-submit review.
- Authorized: existing OpenSpec reconciliation, DevFlow source/tests/evidence,
  generated `plugins/dev-flow/**` after source proof, exact direct-main commit
  and push, and only the named DevFlow plugin refresh/readback.
- Excluded: consumer-project migration, broad updater actions, Goal-lifecycle
  implementation, AGENTS candidate merge, legacy cleanup, dependencies,
  archive, PR, publication, force-push, and destructive work.

## Blocking review findings promoted into tasks 9.1-9.8

1. Future project schema heads and configuration targets must be derived from
   the manifest rather than assuming schema 1 or literal v1 bytes.
2. Trusted configuration/state schema disagreement must be
   `baseline_ambiguous` with no apply or state-sync action.
3. Manifest-only adapter changes must advance Project Refresh identity and
   evidence even when tracked-input file bytes do not change.
4. Verification receipts must independently bind the complete transaction
   evidence required by the public receipt contract.

## Confirmed TDD seams

- `plugin_project_migration.py plan/apply/verify` JSON and filesystem outcome;
- Project Refresh Impact and release-gate structured result;
- published project-refresh receipt JSON schema.

## Preserved unrelated work

`openspec/changes/separate-git-transport-from-github-auth/evidence/implementation.md`
remains outside the write/stage set at diff SHA-256
`156697b2fda831afd5ac23a2e5ce8ffc98d18836f345535915bded204d812ba6`.
The planned `repair-devflow-goal-gate-lifecycle` artifacts remain unchanged and
paused at their prior Human Gate.

## Baseline and next action

- Branch/HEAD: `main` at `187c81cb25a13cde58b9c972a9ed050311f82775`.
- Capability diagnosis: ready with recommendations for implementation planning,
  test-first execution, root-cause diagnosis, change review, and completion
  proof; no dependency action required.
- Previous fresh baseline: complete DevFlow 499/499, release group 79/79,
  strict OpenSpec 61/61, runtime verified, release sync current, Plugin Eval
  86/B with zero failures.
- Next: task 9.2, capture RED through the confirmed public seams.
