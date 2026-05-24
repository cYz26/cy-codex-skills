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

## Boundaries

Do not expand scope, add dependencies, introduce migrations, or break public APIs without updating OpenSpec and getting approval. Do not mark a capability slice done before its validation command passes.
