---
checkpoint_id: 2026-08-07-project-refresh-corrective-green
created_at: 2026-08-07T11:38:16+08:00
boundary: corrective-source-green
project_mode: brownfield
change_id: add-versioned-devflow-project-refresh
compact_recommended: false
compact_status: not_needed
next_stage: verifying
---

# Checkpoint: Project Refresh corrective source GREEN

## Completed correction

- Public plan/apply now executes supported v1-to-v2 and v0-to-v1-to-v2 paths
  atomically while preserving unrelated configuration.
- The production contract advances to project schema head 2 with immutable v2
  target, unique v1-to-v2 step, updated scaffold/inspector target, and complete
  supported fixture coverage.
- Config-sensitive drift can no longer bypass schema advance through a generic
  decision label.
- Apply and standalone verification receipts carry and runtime-validate a full
  evidence digest plus before/after state fingerprints.

## Fresh evidence

- Project Refresh tests: 42/42 GREEN.
- Project Refresh Impact tests: 10/10 GREEN.
- Real source-versus-release impact: `changed_covered`, schema decision
  `advanced`, head 2, revision 2, no errors.
- Tracked-input SHA-256:
  `ee6817cc798f64d1976c815accbad39cc2966e6244b1eeb019778ba8d9d597d1`.
- Unrelated Git-transport evidence diff remains excluded at SHA-256
  `156697b2fda831afd5ac23a2e5ce8ffc98d18836f345535915bded204d812ba6`.

## Next action

Run task 9.6 focused and complete source verification, strict OpenSpec and
workflow checks, then obtain renewed zero-write Standards and Spec review.
Release generation remains blocked until both axes have no blocking finding.
