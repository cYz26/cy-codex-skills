---
name: change-plan
description: Use when an OpenSpec change needs proposal, design, specs, or tasks.
---

# Change Plan

Use when an active change lacks complete OpenSpec artifacts or needs implementation planning.

## Artifacts

Ensure `openspec/changes/<change-id>/` has proposal, design, tasks, and requirement scenarios.

## Routes

- Use `openspec-explore` if design tradeoffs, compatibility, or acceptance criteria remain unclear.
- Use `openspec-propose` when intent is ready for canonical proposal, design, specs, and tasks.
- Use `superpowers:brainstorming` while solution shape is open.
- Use `superpowers:writing-plans` before committing to `tasks.md`, `design.md`, or a GSD phase plan.

## Rules

Do not write production code. If design tradeoffs remain unresolved, return to intake or brainstorming. Before execution, run `scripts/validate_workflow_state.py --repo <repo> --json`.
