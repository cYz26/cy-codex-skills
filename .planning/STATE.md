---
workflow_version: 0.3.0
project_mode: brownfield
current_stage: review_or_archive

current_phase:
  id: 01-foundation
  status: verification_passed

current_change:
  id: add-release-promotion-gate
  status: verified

gates:
  workflow_initialized: true
  spec_approved: true
  plan_written: true
  tests_baseline_known: true
  implementation_done: true
  verification_passed: true
  state_updated: true
  archive_allowed: false

context_management:
  compact_policy: checkpoint_boundary
  last_checkpoint_id: 2026-06-02-verification_passed-add-release-promotion-gate
  last_checkpoint_file: .planning/checkpoints/2026-06-02-verification_passed-add-release-promotion-gate.md
  compact_recommended: false
  compact_status: not_needed
  last_compact_result_file: none
  compact_source: checkpoint
  compact_updated_at: 2026-06-02T12:10:17+08:00
  compact_skip_reason: none
  compact_error: none
  compact_after:
    - project_setup_completed
    - codebase_mapping_completed
    - design_saved
    - openspec_change_planned
    - phase_plan_saved
    - verification_passed
    - change_archived
    - phase_shipped
  skip_compact_for:
    - small_task_update
    - typo_fix
    - docs_only_micro_change
  require_before_compact:
    - state_updated
    - durable_context_written
    - next_action_recorded
    - risks_recorded
    - validation_recorded_if_applicable

context_health:
  last_report: none
  last_risk: medium
  last_confidence: high
  last_decision: release_promotion_gate_verified
  last_goal_status: verified
  goal_summary: DevFlow release promotion gate is implemented and verified
---

# Workflow State

## Current Status

DevFlow release promotion gate work is implemented and verified.

Completed scope:

- `workflow_release_sync.py` discovers dev plugin and standalone skill release
  counterparts, detects allowlisted drift, applies runtime sync, runs configured
  build commands, tracks managed outputs, and resolves release-first Plugin Eval
  targets.
- `sync_release_assets.py` provides explicit dry-run/apply and eval-target
  resolution.
- `release_promotion_gate.py` runs from the DevFlow Stop hook after
  verification has been recorded and before checkpoint policy.
- DevFlow release metadata excludes raw `scripts/**` copying and regenerates
  the packaged `devflow_runtime.pyz` release runtime.
- Release-isolation docs, development README files, and the AGENTS template now
  document the verified-boundary sync point and release-first Plugin Eval
  policy.
- Dev and release DevFlow plugin copies are synchronized for this change.

Verification evidence is recorded in
`.planning/verification/20260602121017-add-release-promotion-gate.md`.
Release runtime packaging preparation evidence is recorded in
`.planning/verification/20260602114103-devflow-release-runtime-packaging.md`.

Checkpoint
`.planning/checkpoints/2026-06-02-verification_passed-add-release-promotion-gate.md`
captures the current handoff state.

Plugin Eval on the release package reports 91/100, grade B, medium risk.
Remaining token-budget warnings are deferred to a dedicated budget-reduction
follow-up.

## Next Action

Review and commit the combined release runtime packaging plus release promotion
gate work. OpenSpec archive remains a separate post-commit step.
