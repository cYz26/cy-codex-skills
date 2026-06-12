---
name: spec-workflow
description: Use when Codex should drive non-trivial features, refactors, integrations, or bug fixes through a reusable spec workflow with staged clarification, implementation planning, and tracked execution artifacts.
---

# Spec Workflow

Use this skill for complex engineering work that should be shaped before broad implementation.

Default posture: inspect the repository first, clarify only the decisions that materially affect scope or design, then drive the work through reusable spec artifacts.

## When to use

Use this skill when at least one of these is true:
1. The request is likely to touch multiple files, modules, or systems.
2. Product behavior, API shape, data contracts, migration, rollout, or regression risk matters.
3. The user asks for a spec, design, plan, task breakdown, roadmap, or careful phased execution.
4. The work will likely span more than one implementation turn.

Do not use this skill for:
1. Tiny edits with obvious scope.
2. Straightforward single-function fixes with no meaningful design tradeoff.
3. Pure Q&A or explanation requests.

## Default operating model

Follow a hybrid Spec Kit flow adapted for Codex:
1. Ground in repo reality first.
2. Choose a mode: `requirements-first`, `design-first`, or `bugfix`.
3. Produce the core artifacts before broad implementation:
   - `spec.md`
   - `plan.md`
   - `tasks.md`
4. Add optional artifacts only when the work needs them:
   - `research.md`
   - `data-model.md`
   - `contracts/`
   - `quickstart.md`
5. Keep execution state in `tasks.md`. Do not create `progress.md`.

Treat repository `AGENTS.md` as the Spec Kit `constitution` equivalent. Reuse repo conventions instead of inventing parallel rules.

## Mode selection

Choose exactly one mode up front:
1. `requirements-first`: default when desired behavior is clearer than implementation.
2. `design-first`: use when the technical approach or architectural boundary is already constrained.
3. `bugfix`: use when the primary job is correcting broken behavior and proving regression safety.

See `references/playbook.md` for the detailed decision rules and per-mode workflow.

## Artifact location

Prefer continuing an existing matching spec folder.

If the repo has no stronger convention, use:
1. `specs/<NNN>-<slug>/`
2. Start numbering at `001`.
3. Reuse the numbering style already present in `specs/` if one exists.

## Checkpoint-style interaction

This skill is not a strict stop-after-every-phase workflow.

Proceed autonomously by default, but stop for user confirmation when:
1. A high-impact product ambiguity changes acceptance criteria or scope.
2. Multiple materially different designs are plausible and the tradeoff is user-facing or expensive.
3. A migration, external dependency, rollout risk, or destructive change lacks clear direction.
4. The user explicitly asks to approve each phase.

Otherwise:
1. Record assumptions directly in the artifacts.
2. Keep moving.
3. Surface open questions in concise chat updates.

## Execution rules

Before implementation:
1. Read `AGENTS.md`, relevant manifests, existing specs, and nearby tests.
2. Pull in domain skills only when the task area clearly needs them.
3. Keep requirements focused on behavior and constraints, not code structure.
4. Keep plan content focused on implementation approach, contracts, and validation.

During implementation:
1. Work from `tasks.md` in order unless dependency discovery requires a change.
2. Update the status block, decisions, blockers, and validation log inside `tasks.md`.
3. If the plan changes materially, update the artifact first, then the code.
4. Reuse repository commands and validation gates instead of inventing new ones.

## Chat output pattern

When using this skill, keep chat summaries compact:
1. Mode
2. Assumptions or decisions locked this turn
3. Artifacts created or updated
4. Current or next task
5. Validation status
6. Open risks, if any

Durable detail belongs in the artifact files, not repeated in chat.

## Naming and replacement

This skill intentionally keeps the canonical name `$spec-workflow`.

If an older `spec-workflow/` skill exists in an installation target, replace it with this one instead of creating a parallel variant. Icons and brand metadata only help humans distinguish UI entries; they do not resolve skill-name collisions.

## Resource map

1. `references/playbook.md`: detailed workflow, decision gates, and artifact policy.
2. `assets/templates/spec-template.md`: core specification template.
3. `assets/templates/plan-template.md`: implementation plan template.
4. `assets/templates/tasks-template.md`: execution and status template.
5. `assets/templates/research-template.md`: discovery and option analysis template.
6. `assets/templates/data-model-template.md`: schema and migration template.
7. `assets/templates/quickstart-template.md`: manual validation template.
8. `assets/templates/agents-snippet.md`: optional repository rule snippet.
