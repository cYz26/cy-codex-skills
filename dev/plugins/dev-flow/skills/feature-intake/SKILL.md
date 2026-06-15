---
name: feature-intake
description: Use when triaging features, bugs, refactors, or workflow requests.
---

# Feature Intake

Classify new requirements, bugs, behavior/API changes, refactors, migrations, tooling, docs, tests, or workflow repair.

## Classification

Kinds: `new-feature`, `bug-fix`, `behavior-change`, `api-change`, `data-model-change`, `migration`, `refactor`, `test-only`, `docs-only`, `tooling`, `workflow-repair`.

## Repair Intake

For `bug-fix` and `workflow-repair`, do not treat a minimal fix as the default
solution. After investigation, require the intake to state the systemic and thorough solution first,
then compare whether execution should be systemic, minimal, staged, or deferred
based on current state, risk, approval, and validation cost.

## Routes

- Before execution, route the request through DevFlow workflow modes:
  `Full OpenSpec`, `Lightweight Ledger`, or `Prototype Mode`.
- Use `ai-native-tech-plan` for technical plans, implementation plans, architecture plans, Codex execution plans, workflow plans, or requests to avoid partial delivery.
- Use `capability-research` when the requirement depends on a current or external capability, platform behavior, plugin/runtime behavior, hook/API support, CLI support, installed-cache state, or local-vs-platform ambiguity.
- Use `superpowers:brainstorming` for open goals, constraints, tradeoffs, or implementation shape.
- Use `openspec-explore` for unclear behavior, compatibility, requirements, or acceptance criteria.
- Use `openspec-propose` before behavior/API/data/integration changes.
- Use `gsd-discuss-phase` and `gsd-plan-phase` for stages, refactors, or milestones.
- Use `superpowers:writing-plans` before committing to a non-trivial plan.

## Workflow Mode Routing

`Full OpenSpec` is mandatory for behavior, public API, data model,
persistence, migration, integration, permission, error-handling, or
compatibility changes. Configuration cannot bypass this gate.

`Lightweight Ledger` may be used only when `.dev-flow.json` enables it and the
work is docs-only, test-only, internal maintenance, or a low-risk bugfix. The
ledger must include Target State, Scope / Non-Goals, Validation Commands,
Execution Log, and Completion Claim.

`Prototype Mode` requires an explicit user request for a spike, prototype,
proof of concept, or demo. Record that the output is non-production and include
cleanup or promotion criteria before any production use.

## Superpowers Artifact Mapping

When Superpowers produces `docs/superpowers/specs/...` or `docs/superpowers/plans/...`, treat those files as drafts or review notes. For behavior work, copy the approved design and task content into canonical OpenSpec artifacts under `openspec/changes/<change-id>/`. For phase or milestone work, copy the approved plan content into `.planning/phases/.../PLAN.md` or a DevFlow-approved ledger.

## Output

For behavior work, clarify Target State, Completion Contract, validation surface, and success criteria, then run `scripts/create_change.py --repo <repo> --change-id <id> --title <title> --type <kind> --json`.
