---
name: change-plan
description: Use when an OpenSpec change needs proposal, design, specs, or executable tasks.
---

# Change Plan

Complete the active OpenSpec change before production implementation.

## Capability Routing

Resolve `decision-resolution`, `implementation-planning`, and when needed
`architecture-guidance` from `scripts/workflow_methodology.py`. Add
`domain-language-modeling` only when domain concepts or invariants are in
scope. Use only the triggered Matt primitives; DevFlow planning remains
authoritative and OpenSpec is canonical.

## Procedure

1. Inspect the current system and existing specs. For an existing change, run
   `openspec status --change <id> --json` and `openspec instructions
   <artifact> --change <id> --json`; follow returned `artifactPaths` and
   `actionContext` rather than assuming schema/store paths.
2. Use `capability-research` for Capability Evidence when current or external
   capability, runtime, cache, CLI, hook, API, or platform assumptions are
   unstable.
3. Resolve design tradeoffs and Open Questions; keep unresolved artifacts
   draft.
4. Ensure `proposal.md`, `design.md` when needed, delta `specs/`, and `tasks.md`
   cover Target State, Completion Contract, Capability Slices, Execution
   Ledger, Acceptance Criteria, Validation Commands, risks, rollback, Critical
   Path, Incidental Finding Budget, Escalation Triggers, default continuation
   policy, and genuine Human Gates.
   For DevFlow changes, include Project Refresh Impact as `changed`,
   `verified-unchanged`, or `not-applicable`, with the inspected surfaces,
   project-schema decision, refresh-contract revision/digest, migration and
   fixture coverage, packaged CLI/Skill consequences, and parity commands.
   When the project selects an external implementation provider, also bind an
   explicit `ImplementationReadinessRequirement v1` to the approved active
   change and semantic plan, then record
   `implementation_readiness.required: true` in DevFlow state at approval.
   Retain `false` when no external provider is selected. Planning may expose Required/NotReady remediation,
   but it must not claim executable status or infer selection from chat,
   advisory direction, repository presence, or a producer's internal files.
5. Route unclear behavior to `openspec-explore`, new ready intent to
   `openspec-propose`, existing-change planning revision to
   `openspec-update-change`, and plan structure to `ai-native-tech-plan`.
6. Run `scripts/validate_workflow_state.py --repo <repo> --json` and OpenSpec
   validation.

For repair, record the systemic solution first and explain any smaller approved
execution path. Methodology notes must be promoted into the active change
before they can satisfy a gate.

## Incidental Finding Lifecycle

Keep required behavior on the Critical Path. A bounded in-scope guard may be
`CONTINUE_WITH_MINIMAL_GUARD`; optional non-blocking work may be
`DEFER_AND_CONTINUE`; severe, ambiguous, scope-expanding, or authority-expanding
work is `BLOCKED_AWAITING_HUMAN`. Record every deferred or blocked finding in
the tracked `TASK_LEDGER.md` Incidental Finding Register. The register does not
authorize work, so accepted follow-up still needs normal intake and the
applicable approved OpenSpec or ledger route.

Planning is complete when every scenario has a task and validator, no required
decision is open, the next executable ledger item is explicit, and ordinary
item/change boundaries route back to the `auto-until-terminal` orchestrator
loop. A DevFlow plan is not final with missing Project Refresh Impact evidence.
Do not edit production code in this skill.
