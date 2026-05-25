# Planning Principles

## Target State

Describe the complete final behavior and internal shape after the task is done. Include user-visible behavior, system boundaries, required tests, and explicit non-goals.

## Completion Contract

List the concrete evidence required before the work can be called complete:

- required behavior
- tests and validation commands
- screenshots or manual checks when needed
- docs or generated artifacts when relevant
- capabilities that must not be skipped

## Capability Slices

Break work by dependency order, not by human delivery dates. Each slice must be independently verifiable and production-complete for its scope.

Each slice includes:

- goal
- files/modules
- implementation checklist
- test checklist
- validation command
- done criteria
- risks/rollback

## Execution Ledger

The ledger is the durable source of truth after interruption, compaction, or session restart. Valid statuses:

- todo
- in_progress
- blocked
- done
- skipped_with_reason

Only use `skipped_with_reason` when the item is outside the Target State or has a recorded blocker.

## Validation Surface

Use the smallest reliable evidence set for the task: unit tests, integration tests, lint, typecheck, build, smoke test, benchmark, manual QA, generated docs, CLI output, or screenshots.
