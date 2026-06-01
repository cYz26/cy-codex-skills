---
workflow_version: 0.3.0
project_mode: brownfield
current_stage: review_or_archive

current_phase:
  id: 01-foundation
  status: verification_passed

current_change:
  id: harden-claude-delegate-execution-contract
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
  last_checkpoint_id: 2026-06-01-verification_passed-harden-claude-delegate-execution-contract
  last_checkpoint_file: .planning/checkpoints/2026-06-01-verification_passed-harden-claude-delegate-execution-contract.md
  compact_recommended: false
  compact_status: not_needed
  last_compact_result_file: none
  compact_source: checkpoint
  compact_updated_at: 2026-06-01T08:50:05+08:00
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
  last_risk: unknown
  last_confidence: unknown
  last_decision: none
  last_goal_status: unknown
  goal_summary: none
---

# Workflow State

## Current Status

Change `harden-claude-delegate-execution-contract` is implemented and verified.
The `claude-code-delegate` wrapper now prepends a mode-specific contract before
invoking Claude Code. Plan mode tells Claude Code to complete the full
non-editing deliverable. Apply mode tells Claude Code to complete all in-scope
execution inside the Claude Code run, including Git operations only when the
delegated task explicitly asks for them.

The skill and README now define Codex as the supervisor/verifier: Codex scopes
the task, invokes Claude Code, then verifies process evidence, diffs, tests, Git
state, workflow records, and blockers. Codex should re-delegate or report a
blocker when Claude leaves delegated execution unfinished instead of silently
finishing the delegated work itself.

Verification passed for RED/GREEN focused tests, dev/release DevFlow tests,
OpenSpec strict validation, Claude Code capability check, dev/release plugin
preflight, installed-cache refresh verification, workflow-state validation, and
Plugin Eval. Plugin Eval remains 77/100 grade C with high risk due to existing
full-plugin token budget and Python complexity findings. Those findings are
deferred because they require broad packaging and helper-script refactors
outside this contract change.

## Next Action

Review and archive `harden-claude-delegate-execution-contract` if the deferred
full-plugin packaging and complexity risks are accepted as follow-up work.
