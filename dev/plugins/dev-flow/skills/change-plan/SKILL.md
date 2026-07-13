---
name: change-plan
description: Use when an OpenSpec change needs proposal, design, specs, or executable tasks.
---

# Change Plan

Complete the active OpenSpec change before production implementation.

## Capability Routing

Resolve `decision-resolution`, `implementation-planning`, and when needed
`architecture-guidance` from `docs/provider_profiles.json`. Provider notes are
inputs; OpenSpec is canonical. Mapping details live in
`docs/provider-profile-migration.md`.

## Procedure

1. Inspect the current system and existing specs.
2. Use `capability-research` for Capability Evidence when current or external
   capability, runtime, cache, CLI, hook, API, or platform assumptions are
   unstable.
3. Resolve design tradeoffs and Open Questions; keep unresolved artifacts
   draft.
4. Ensure `proposal.md`, `design.md` when needed, delta `specs/`, and `tasks.md`
   cover Target State, Completion Contract, Capability Slices, Execution
   Ledger, Acceptance Criteria, Validation Commands, risks, and rollback.
5. Route unclear behavior to `openspec-explore`, ready intent to
   `openspec-propose`, and plan structure to `ai-native-tech-plan`.
6. Run `scripts/validate_workflow_state.py --repo <repo> --json` and OpenSpec
   validation.

For repair, record the systemic solution first and explain any smaller approved
execution path. Legacy `docs/superpowers/specs/` or
`docs/superpowers/plans/` content is promoted into the active change before it
can satisfy a gate.

Planning is complete when every scenario has a task and validator, no required
decision is open, and the next executable ledger item is explicit. Do not edit
production code in this skill.
