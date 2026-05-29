---
name: ai-native-tech-plan
description: Use when writing technical plans with Target State, Completion Contract, Execution Ledger.
---

# AI-native Technical Planning

Use this skill to make Codex plans executable, resumable, and complete for the requested target state.

## Default

Unless the user explicitly asks for a prototype, demo, POC, MVP, or partial target, assume the requested result is the complete Target State.

Avoid human delivery framing in technical plans:

- MVP as the default completion boundary
- Numbered delivery phases as completion boundaries
- Future Work sections for required behavior
- Calendar estimates, sprint estimates, person-day estimates, or staffing assumptions

Use instead:

- Target State
- Scope / Non-Goals
- Architecture Decisions
- Completion Contract
- Capability Slices
- Execution Ledger
- Acceptance Criteria
- Validation Commands
- Risks / Rollback
- Goal Mode Prompt
- Continue Prompt
- Review Checklist

## Workflow

1. Read project context: `AGENTS.md`, `.planning/STATE.md`, active OpenSpec change, and relevant source files.
2. If behavior, API, persistence, integration, compatibility, or error handling changes are involved, route through OpenSpec before implementation.
3. If goals or tradeoffs are still open, use `superpowers:brainstorming`.
4. Before committing to a non-trivial implementation plan, use `superpowers:writing-plans`.
5. For medium or large tasks, write the Execution Ledger to a repo file such as `.ai/tasks/<yyyy-mm-dd>-<task-name>.md`, or the repo's established planning location.
6. During implementation, use `superpowers:test-driven-development` where applicable and update ledger statuses only after validation.
7. Before completion, use `superpowers:verification-before-completion` and verify the Completion Contract.

## Superpowers, GSD, and OpenSpec Fit

- Superpowers provides brainstorming, writing-plans, test-driven-development, and verification-before-completion discipline.
- GSD phases are governance and sequencing containers, not technical completion boundaries.
- OpenSpec remains required for behavior-level proposal, design, specs, tasks, verification, sync, and archive.
- The AI-native plan adds execution contracts, ledgers, and validation surfaces so work can continue after interruption or compaction.

## Superpowers Artifact Mapping

Use Superpowers outputs as planning discipline, then persist the approved result in canonical workflow files. `docs/superpowers/specs/...` maps to OpenSpec proposal/design/specs for behavior work. `docs/superpowers/plans/...` maps to OpenSpec `tasks.md`, `.planning/phases/.../PLAN.md`, or a DevFlow-approved ledger. Do not keep Superpowers notes as a second source of truth after the canonical artifacts exist.

## Output Contract

When generating a plan, include:

1. Target State
2. Scope / Non-Goals
3. Architecture Decisions
4. Completion Contract
5. Capability Slices
6. Execution Ledger
7. Acceptance Criteria
8. Validation Commands
9. Risks / Rollback
10. Goal Mode Prompt
11. Continue Prompt
12. Review Checklist

For detailed templates, read only the relevant bundled file:

- Planning principles: `references/planning-principles.md`
- AGENTS.md snippet: `references/agents-md-snippet.md`
- Goal and continue prompts: `references/goal-prompt-template.md`
- Task ledger template: `assets/task-ledger-template.md`
- Review checklist: `assets/review-checklist.md`
