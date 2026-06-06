---
workflow_version: 0.3.0
project_mode: brownfield
current_stage: verification

current_phase:
  id: 01-foundation
  status: in_progress

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
  compact_updated_at: 2026-06-02T19:53:40+08:00
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
  last_report: .planning/verification/20260604211027-publish-local-changes.md
  last_risk: medium
  last_confidence: high
  last_decision: workflow_state_migration_repaired
  last_goal_status: verified
  goal_summary: Workflow state and migration drift repaired; remote branch needs repair commit before merge
---

# Workflow State

## Current Status

The `codex/lark-feishu-ops-progress-contract` branch is pushed to origin and
under merge-readiness verification.

The active OpenSpec state points at the existing verified
`add-release-promotion-gate` change. Additional branch work for AgentKB source
intake and problem capture, AgentKB optional extractor regression handling,
DevFlow Stop hook JSON output, Lark Feishu Ops daily update sync, and DevFlow
project migration cleanup is covered by publish verification evidence.

## Next Action

Confirm workflow validation, DevFlow doctor status, GitHub PR/check status, and
merge readiness against `origin/main`.

Archive `add-release-promotion-gate` remains a separate post-merge workflow
action when the archive gate is otherwise clear.

## Publish Verification

Evidence:

- `.planning/verification/20260604211027-publish-local-changes.md`

## Recent Verification

DevFlow release promotion gate is implemented and verified. The change adds the
release sync engine, explicit sync CLI, Stop-hook promotion gate, DevFlow
packaging metadata, release-first Plugin Eval target resolution, and updated
guidance.

Evidence:

- `.planning/verification/20260602121017-add-release-promotion-gate.md`
- `openspec/changes/add-release-promotion-gate/tasks.md`

## Side Conversation Verification

AgentKB and Lark Feishu Ops branch work was verified in side conversations
without becoming the active main-thread `current_change`.

Evidence:

- `.planning/verification/20260604211027-publish-local-changes.md`
