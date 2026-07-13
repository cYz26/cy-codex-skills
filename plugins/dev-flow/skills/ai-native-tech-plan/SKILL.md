---
name: ai-native-tech-plan
description: Use when writing technical plans with Target State, Completion Contract, Execution Ledger, and Validation Commands.
---

# AI-native Technical Planning

Write the complete requested Target State unless the user explicitly asks for
a prototype or partial target. A plan is an executable contract, not a calendar
or staffing forecast.

## Preconditions

Read `AGENTS.md`, `.planning/devflow/STATE.md`, the active OpenSpec change, and
relevant source. Add a Skill Routing Ledger. If unstable platform assumptions,
current documentation, plugin/runtime behavior, or local capability evidence
affects the design, run `capability-research`. Open Questions remain means the
artifact is draft, not final; resolve them before committing to the plan.

## Capability Routing

Resolve `decision-resolution`, `implementation-planning`, and
`architecture-guidance` through `docs/provider_profiles.json`. Record the
chosen profile and evidence, but keep provider procedure in
`docs/provider-profile-migration.md`. The plan itself stays provider-neutral.

## Required Shape

1. Target State — final external behavior and internal boundaries.
2. Scope / Non-Goals — explicit write and compatibility boundaries.
3. Architecture Decisions — choices, evidence, and rejected alternatives.
4. Completion Contract — binary acceptance criteria.
5. Capability Slices — dependency-ordered, production-complete slices; each
   includes implementation, validation, and cleanup.
6. Execution Ledger — owner, write set, status, evidence, and human gate.
7. Validation Commands — focused, broad, runtime, docs, and release checks.
8. Risks / Rollback — stop conditions and reversible actions.
9. Goal Mode Prompt and Continue Prompt when recovery risk warrants them.
10. Review Checklist and Final Verification.

Required behavior does not belong in MVP, Future Work, or a later delivery
phase. Roadmap phases may sequence work but cannot redefine technical
completion.

## Workflow Gates

Behavior/API/data/integration/migration/compatibility/error-handling changes
require OpenSpec before implementation. Apply the Goal Suitability Gate through
`define-goal` when the user requests a goal or the work is long-running,
multi-slice, migration/release oriented, cross-context, delegation-backed, or
likely to lose its definition of done.

Add a SubAgent Strategy for independent Capability Slices. Record authorization
state, disjoint write sets, Agent Task Contract path, main-agent-owned
artifacts, and fallback. No worker starts before that contract is valid.

## Compatibility Artifact Mapping

Provider planning notes, including legacy `docs/superpowers/plans/`, are review
inputs. Promote approved content into OpenSpec `tasks.md`, the selected roadmap
plan, or the DevFlow Execution Ledger; canonical files win conflicts.

## Completion

The plan is complete when every required behavior maps to a slice, criterion,
validation command, owner, rollback path, and ledger item, with no unresolved
Open Questions.
