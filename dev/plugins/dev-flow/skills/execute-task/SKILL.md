---
name: execute-task
description: Use when executing one approved OpenSpec task.
---

# Execute Task

Use only after the active change has proposal, specs, design when needed, and tasks.

## Procedure

1. Read `AGENTS.md`, `.planning/STATE.md`, the active OpenSpec change, and relevant source files.
2. Use `openspec-apply-change` when executing approved OpenSpec tasks.
3. Use `superpowers:test-driven-development` before implementation for features, bug fixes, and risky behavior changes.
4. Read the Target State, Completion Contract, Capability Slices, Execution Ledger, Acceptance Criteria, and Validation Commands.
5. Pick the next unfinished ledger item or capability slice from `tasks.md` or the repo-specific ledger.
6. Write or update the failing test first, implement minimally, then run focused and broader checks.
7. Update `tasks.md`, `.planning/STATE.md`, the Execution Ledger, and verification evidence only after validation passes or a blocker is recorded.

Use `gsd-execute-phase` only for an approved phase plan.

## Workflow Modes

Full OpenSpec tasks require ready proposal, design, specs, and tasks before
implementation. If workflow routing reports a mandatory Full OpenSpec blocker,
stop and use `openspec-propose` or `openspec-apply-change` as directed.

Lightweight Ledger execution is allowed only for configured low-risk work. Keep
the ledger complete with Target State, Scope / Non-Goals, Validation Commands,
Execution Log, and Completion Claim, and do not claim completion until evidence
exists.

Prototype Mode output is non-production. Keep cleanup or promotion criteria in
the task record, and promote through Full OpenSpec before production behavior,
API, data, integration, migration, permission, error-handling, or compatibility
changes.

## Delegated Execution

Use subAgents only when the user or active workflow explicitly authorized
delegated parallel work and the approved task can be split into disjoint write
sets. The shared files remain serialized through the main agent.

For authorized execution, prefer the existing execution skills:

- `gsd-execute-phase` for approved GSD phase waves.
- `subagent-driven-development` for task-by-task implementation with review.
- `dispatching-parallel-agents` for independent investigation or review.
- `executing-plans` when subAgents are unavailable or the work is tightly coupled.

Before dispatch, assign each worker concrete file ownership or read-only scope.
Keep OpenSpec artifacts, `.planning/STATE.md`, verification evidence, shared
README/docs, and final integration under main-agent ownership unless the plan
serializes those edits.

Each delegated result must report status (`DONE`, `DONE_WITH_CONCERNS`,
`NEEDS_CONTEXT`, or `BLOCKED`), files changed or inspected, commands or tests
run, residual risks, and review needs. Review those results before updating the
Execution Ledger.

## Boundaries

Do not expand scope, add dependencies, introduce migrations, or break public APIs without updating OpenSpec and getting approval. Do not mark a capability slice done before its validation command passes.
