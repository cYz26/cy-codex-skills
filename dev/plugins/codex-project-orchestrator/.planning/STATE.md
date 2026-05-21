---
workflow_version: 0.3.0
project_mode: brownfield
current_stage: planning

current_phase:
  id: 01-foundation
  status: planning

current_change:
  id: audit-context-tools
  status: planned

gates:
  workflow_initialized: true
  spec_approved: false
  plan_written: true
  tests_baseline_known: false
  implementation_done: false
  verification_passed: true
  state_updated: true
  archive_allowed: false

context_management:
  compact_policy: checkpoint_boundary
  last_checkpoint_id: none
  last_checkpoint_file: none
  compact_recommended: false
  compact_status: not_needed
  last_compact_result_file: none
  compact_source: none
  compact_updated_at: none
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
---

# Workflow State

## Current Status

Workflow state updated.

## Next Action

Continue with the active planned task.
