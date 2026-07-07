# Design: Optimize DevFlow AGENTS Drift Review

## Target State

When DevFlow refresh runs for a project, AGENTS drift review is part of the
refresh gate. The agent must compare durable workflow guidance from DevFlow core
flow and AGENTS templates against the active project `AGENTS.md`, use
`scaffold_workflow.py --dry-run` output as a candidate when available, and report
the AGENTS status as `unchanged`, `merged`, `generated-deferred`, or `conflict`.

`validate_workflow_state.py` remains a gate, not the only drift signal. It
detects missing durable guidance markers so stale `AGENTS.md` files are not
silently considered current. The actual merge decision stays review-based and
does not overwrite active project guidance automatically.

## Completion Contract

- The `dev-flow-refresh` skill says AGENTS drift review is a required project
  refresh gate.
- Development and release AGENTS templates include the DevFlow refresh workflow.
- Workflow validation reports missing durable AGENTS sections that represent
  current DevFlow core flow and template guidance.
- Tests cover development and release packaging and validator behavior.
- Focused unit tests, workflow validation, OpenSpec validation, and diff checks
  pass.

## Capability Slices

1. Contract and tests
   - Add OpenSpec requirements and failing tests for the AGENTS template and
     validator contract.
   - Validate that failures identify the missing drift mechanism.

2. Mechanism implementation
   - Update AGENTS templates and active repo guidance with DevFlow refresh
     workflow rules.
   - Update `missing_agents_guidance()` with durable section markers.
   - Keep generated AGENTS handling as a manual merge boundary.

3. Release and verification
   - Sync release assets or update mirrored release files consistently.
   - Run focused tests, validation, and OpenSpec checks.
   - Record verification evidence and update workflow state.

## Acceptance Criteria

- A project `AGENTS.md` that lacks `Goal Workflow`, `Workflow Mode Routing`,
  `Plugin Eval Gate`, `Local Reference Update Reminder`, or
  `DevFlow Refresh Workflow` is reported by validation as missing DevFlow
  workflow guidance.
- The canonical AGENTS template contains `DevFlow Refresh Workflow` and the
  merge boundary for `AGENTS.md.generated`.
- The refresh skill final report includes AGENTS status and evidence.

## Risks / Rollback

- **Risk: validation becomes too strict for older partially migrated projects.**
  Mitigation: missing guidance remains a warning unless an active
  `AGENTS.md.generated` candidate exists beside active `AGENTS.md`, matching
  existing behavior.
- **Rollback:** remove the additional required markers and AGENTS template
  section, then rerun focused tests and OpenSpec validation.
