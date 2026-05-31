---
name: change-plan
description: Use when an OpenSpec change needs proposal, design, specs, or tasks.
---

# Change Plan

Use when an active change lacks complete OpenSpec artifacts or needs implementation planning.

## Artifacts

Ensure `openspec/changes/<change-id>/` has proposal, design, tasks, requirement scenarios, Target State, Completion Contract, Capability Slices, Execution Ledger, Acceptance Criteria, and Validation Commands.

When the design depends on current, external, platform, plugin, API, hook, CLI, installed-cache, or local-vs-platform capability, add Capability Evidence before implementation. Use `capability-research` to confirm authoritative/current behavior, run the local scan, compare options, and turn the result into OpenSpec scenarios and validation commands.

## Routes

- Use `ai-native-tech-plan` when plan structure, execution ledger, completion contract, or anti-partial-delivery guidance is needed.
- Use `capability-research` before finalizing design when capability evidence is incomplete or assumptions are unstable.
- Use `openspec-explore` if design tradeoffs, compatibility, or acceptance criteria remain unclear.
- Use `openspec-propose` when intent is ready for canonical proposal, design, specs, and tasks.
- Use `superpowers:brainstorming` while solution shape is open.
- Use `superpowers:writing-plans` before committing to `tasks.md`, `design.md`, or a GSD phase plan.

## Superpowers Artifact Mapping

Superpowers artifacts are inputs to this change, not peer canonical files. Fold `docs/superpowers/specs/...` into `proposal.md`, `design.md`, or `specs/`. Fold `docs/superpowers/plans/...` into `tasks.md` with Capability Slices, Execution Ledger, Acceptance Criteria, and Validation Commands. If the OpenSpec artifacts and Superpowers notes conflict, update the canonical OpenSpec files and retire the stale notes.

## Rules

Do not write production code. If design tradeoffs remain unresolved, return to intake or brainstorming. Before execution, run `scripts/validate_workflow_state.py --repo <repo> --json`.
