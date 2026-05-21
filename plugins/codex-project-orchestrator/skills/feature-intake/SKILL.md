---
name: feature-intake
description: Use when triaging a new feature, bug, refactor, or workflow request.
---

# Feature Intake

Classify new requirements, bugs, behavior/API changes, refactors, migrations, tooling, docs, tests, or workflow repair.

## Classification

Kinds: `new-feature`, `bug-fix`, `behavior-change`, `api-change`, `data-model-change`, `migration`, `refactor`, `test-only`, `docs-only`, `tooling`, `workflow-repair`.

## Routes

- Use `superpowers:brainstorming` for open goals, constraints, tradeoffs, or implementation shape.
- Use `openspec-explore` for unclear behavior, compatibility, requirements, or acceptance criteria.
- Use `openspec-propose` before behavior/API/data/integration changes.
- Use `gsd-discuss-phase` and `gsd-plan-phase` for stages, refactors, or milestones.
- Use `superpowers:writing-plans` before committing to a non-trivial plan.

## Output

For behavior work, clarify goal and success criteria, then run `scripts/create_change.py --repo <repo> --change-id <id> --title <title> --type <kind> --json`.
