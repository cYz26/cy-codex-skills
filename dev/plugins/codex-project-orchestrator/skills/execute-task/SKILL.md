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
4. Pick one task from `tasks.md`.
5. Write or update the failing test first, implement minimally, then run focused and broader checks.
6. Update `tasks.md`, `.planning/STATE.md`, and verification evidence.

Use `gsd-execute-phase` only for an approved phase plan.

## Boundaries

Do not expand scope, add dependencies, introduce migrations, or break public APIs without updating OpenSpec and getting approval.
