---
name: workflow-doctor
description: Use when workflow state, specs, tasks, or evidence drift.
---

# Workflow Doctor

Use when artifacts conflict, tasks lack evidence, implementation lacks specs, state is stale, or hooks/scripts break.

## Repair Solution Discipline

Workflow repair starts with diagnosis, not a minimal fix. After investigation,
describe the systemic and thorough solution first: root cause, broken contracts,
durable prevention, required tests, documentation updates, and verification.
Then decide whether to execute that solution, a minimal fix, a staged repair, or
a deferred follow-up, and record why the selected path fits the current state.

## Procedure

1. Run `scripts/validate_workflow_state.py --repo <repo> --json`.
2. Run `scripts/doctor_workflow.py --repo <repo> --write-report --json`.
3. Use `gsd-progress` when phase progress or roadmap state is unclear.
4. Use `openspec-explore` when spec intent, compatibility, or acceptance criteria need clarification before repair.
5. Inspect `workflow-diagnosis.md` and `repair-plan.md`.
6. Repair workflow files before continuing implementation.

## Output

Report diagnosis, repair steps, and blockers. Do not archive or edit production code during workflow repair.
