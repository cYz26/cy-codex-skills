# Engineering Policy

## Purpose

This file holds durable engineering rules that are too detailed for
`AGENTS.md`. `AGENTS.md` routes agents here when the current task needs
contract-first execution, testing, evidence, review, dependency, or release
policy.

## Contract-First Execution

- Define the Goal Contract before non-trivial execution.
- Keep required behavior in OpenSpec, GSD phase plans, or `TASK_LEDGER.md`.
- Treat Superpowers artifacts as drafts or method evidence until promoted.
- Do not run hidden installers, hook trust actions, release sync apply, or
  archive operations from hooks.

## Testing and Evidence

- Use TDD for feature, bug, refactor, and behavior changes.
- Record red/green evidence when TDD is required.
- Run fresh validation before completion claims.
- Store verification evidence under `.planning/verification/`.

## Dependencies and Release

- Record dependency provenance and source channels.
- Keep release assets synced from the managed dev source.
- Run release runtime verification before release readiness claims.
