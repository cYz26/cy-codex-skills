# Engineering Policy

## Purpose

This file records durable engineering rules used by DevFlow for contract-first
execution, testing, evidence, dependency, review, and release decisions.

## Contract-First Execution

- Define the Goal Contract before long-running, migration/release, broad,
  delegation-backed, or cross-context work.
- Keep required behavior in OpenSpec and execution state in `TASK_LEDGER.md`
  plus `.planning/devflow/**`.
- Matt skills provide engineering primitives only; their notes are drafts until
  promoted into an approved canonical artifact.
- Hooks remain read-only with respect to installers, dependency activation,
  project migration, release sync apply, archive, and Git operations.
- Unknown capability IDs, stale required resources, ambiguous ownership, and
  retired workflow keys fail closed.

## Testing and Evidence

- Use TDD for features, bugs, refactors, business logic, and risky behavior.
- Record the observed RED failure and final GREEN result, or document why TDD
  does not apply.
- Prefer public-seam tests and characterization coverage before risky
  brownfield edits.
- Run fresh focused and broad validation before completion claims.
- Store DevFlow verification evidence below
  `.planning/devflow/verification/` and link it from the active ledger item.

## Severe Finding Human Stop

- Classify a finding as `BLOCKED_AWAITING_HUMAN` before further mutation when
  continuing could cause data loss or corruption, a security bypass or
  authority bypass, an irreversible or destructive effect, a public-contract or required-
  behavior change, a production dependency/schema/migration/external effect,
  ambiguous ownership, or an unresolved product tradeoff.
- Finish only safe read-only diagnosis, preserve the current work, and record
  evidence, impact, safe options, and a recommended decision in
  `TASK_LEDGER.md`.
- Ask the human one concrete decision. Promote the answer into OpenSpec or the
  active ledger before resuming; do not speculate, auto-resume, or perform an
  unapproved fix.
- Unknown or ambiguous severity fails closed. An unresolved severe finding
  blocks continuation, completion claims, verification readiness, and archive.

## Bounded Subagents

- Validate an Agent Task Contract before delegating implementation.
- Assign unique workers disjoint write sets; exact and parent/child overlaps are
  invalid.
- Reserve shared control-plane, OpenSpec, DevFlow state, release metadata,
  generated release, integration, and final proof for the main agent.
- Workers report commands, test logs, changed files, unverified areas, and
  residual risks, then wait for integration review.
- A worker must stop before scope expansion, dependency changes, ambiguous
  cleanup, public-contract changes, or unapproved external effects.

## Dependencies and Source Integrity

- Record repository, immutable commit, release ref, license, and file hashes for
  vendored methodology resources.
- Install or update dependencies only after explicit authorization.
- Do not let global installations satisfy project-local readiness.
- Treat secret-bearing configuration as data to inspect safely; never echo
  tokens or credentials in reports.

## Release

- Develop managed plugin and skill sources under `dev/`; generate release
  counterparts through the release promotion gate.
- Run release runtime verification, source/release parity checks, packaged
  tests, and release-target Plugin Eval before readiness.
- Release apply, installed-cache refresh, project migration, archive, commit,
  push, and PR creation remain distinct authorization boundaries.

## Review and Completion

- Review correctness, compatibility, scope, evidence, generated artifacts,
  dependency changes, and remaining risks.
- Do not weaken or delete a current test only to hide a regression; remove a
  test when its production contract is explicitly retired and replace any
  still-relevant coverage.
- Mark a ledger item done only after its required evidence passes.
- A completion claim names exact commands/results and any residual risk.
