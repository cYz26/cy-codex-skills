# AGENTS.md

## Purpose

This repository uses a Codex-first development workflow with GSD-style planning, OpenSpec change management, engineering discipline, and plan-first gates.

Do not implement non-trivial changes directly from chat memory.

## Workflow Ownership

- GSD owns roadmap, milestones, phases, and phase verification.
- OpenSpec owns behavior-level proposal, specs, design, tasks, verification, sync, and archive.
- Engineering discipline governs clarification, brainstorming, planning, TDD, review, and finishing.
- Codex planning behavior is required before major design or implementation boundaries.

## GSD/OpenSpec Skills

GSD and OpenSpec are activated project-locally through `.codex/skills/`; do not enable them globally for this workflow.

- Use `openspec-explore` when requirements, compatibility, or behavior boundaries are unclear.
- Use `openspec-propose` before implementing user-visible behavior, public API, data model, permission, persistence, integration, migration, error handling, or compatibility changes.
- Use `openspec-apply-change` when executing approved OpenSpec tasks.
- Use `openspec-archive-change` only after verification evidence is recorded and the archive gate is clear.
- Use `gsd-discuss-phase` and `gsd-plan-phase` for multi-stage work, phase planning, broad refactors, or milestone planning.
- Use `gsd-execute-phase` only when executing an approved phase plan, and `gsd-verify-work` before marking a phase shipped.

## Brainstorm and Planning Flow

- Use `superpowers:brainstorming` before committing to a solution when goals, constraints, tradeoffs, or implementation shape are still open.
- Use `openspec-explore` during brainstorming when the uncertainty is about user-visible behavior, compatibility, requirements, or acceptance criteria.
- Use `gsd-discuss-phase` during brainstorming when the uncertainty is about milestones, sequencing, scope boundaries, or phase structure.
- Use `superpowers:writing-plans` before writing a non-trivial implementation plan, phase plan, migration plan, or refactor plan.
- Use `ai-native-tech-plan` when generating technical plans, implementation plans, architecture plans, Codex execution plans, workflow plans, or anti-partial-delivery plans.
- Use `openspec-propose` after brainstorming when behavior-level artifacts need to become proposal, design, specs, and tasks.
- Use `gsd-plan-phase` after brainstorming when the work should become an approved phase plan.
- Do not move from brainstorming/planning into implementation until the chosen plan, scope, verification approach, and open risks are recorded.

## AI Coding Planning Rules

This repository follows an AI-native execution model.

Do not produce human-style delivery plans such as:

- MVP or prototype as the default completion boundary.
- Numbered delivery phases as completion boundaries for required behavior.
- Future Work sections for required functionality.
- Calendar estimates, sprint estimates, or staffing assumptions.
- Partial implementation plans that stop after a simplified first slice.

Unless explicitly requested, assume the user wants the complete Target State.

When asked to design or implement a technical solution, use this structure:

1. Target State
   - Describe the complete final behavior after the task is done.
   - Include user-visible behavior, internal structure, boundaries, and non-goals.

2. Completion Contract
   - List concrete acceptance criteria.
   - Include tests, commands, screenshots, docs, or runtime checks where applicable.

3. Capability Slices
   - Break work into dependency-ordered, independently verifiable slices.
   - Each slice must be production-complete for its own scope.
   - Each slice must include implementation, validation, and cleanup.

4. Execution Ledger
   - Maintain a checklist in the plan or a repo file.
   - Mark each item done only after validation.
   - Resume from the ledger after interruption or context compaction.

5. Final Verification
   - Run the smallest relevant test suite, lint/typecheck, and project-specific checks.
   - Report exact commands and results.

GSD phases are governance and sequencing containers, not technical completion boundaries.

## Project Mode

Project mode: brownfield

### Greenfield

- Establish Target State and Completion Contract first.
- Create or update `.planning/ROADMAP.md`.
- Create initial OpenSpec specs or an `initial-target-state` change.
- Establish test, lint, and build baselines early.

### Brownfield

- Inspect existing architecture, conventions, tests, and specs first.
- Prefer minimal compatible changes.
- Reuse existing components, services, APIs, tokens, routing, data fetching, and error handling.
- Add characterization or regression tests before risky changes.

## When OpenSpec Is Required

Create or update `openspec/changes/<change-id>/` before implementation if work changes user-visible behavior, public APIs, data models, permissions, persistence, integrations, migrations, error handling, or compatibility behavior.

## Superpowers Discipline

Superpowers is activated project-locally through `.codex/skills/`; do not enable it globally for this workflow.

- Before structured ideation or solution exploration, use `superpowers:brainstorming`.
- Before writing or committing to a non-trivial plan, use `superpowers:writing-plans`.
- Before implementing a feature, bugfix, or risky behavior change, use `superpowers:test-driven-development`.
- Before claiming work is complete, fixed, passing, ready to commit, or ready for PR, use `superpowers:verification-before-completion`.
- If either Superpowers skill is unavailable, run the project orchestrator dependency check and activation before continuing.

## Execution Rules

- Execute one task at a time unless explicitly instructed otherwise.
- Prefer TDD for business logic, bug fixes, and risky behavior.
- Do not expand task scope without updating the plan.
- Do not introduce dependencies without documenting why.
- Do not modify unrelated files.

## Verification Rules

Before marking work complete, run relevant tests, run lint/typecheck/build where applicable, update OpenSpec tasks, update `.planning/STATE.md`, record verification evidence, and report remaining risks.

## Context Checkpoint and Compaction

At major workflow boundaries, create a durable checkpoint before continuing.

Major boundaries include project setup completed, codebase mapping completed, design saved, OpenSpec change planned, phase plan saved, verification passed, change archived, and phase shipped.

Before compaction, persist `.planning/STATE.md`, relevant `.planning/phases/` files, relevant `openspec/changes/` files, changed files summary, validation commands and results, unresolved risks, and next action.

Compaction is not a source of truth. Repository files remain authoritative. When a checkpoint is complete,
recommend `/compact` in Codex CLI before moving to the next major stage. If an external harness runs API
compaction, record the compact result under `.planning/compact-results/`. If compaction is unavailable,
start a new session from the checkpoint file.

## Forbidden Without Explicit Approval

- Deleting large amounts of code.
- Changing public APIs.
- Changing persistence schema.
- Adding production dependencies.
- Rewriting architecture.
- Bypassing failing tests.
- Archiving OpenSpec changes without verification.
