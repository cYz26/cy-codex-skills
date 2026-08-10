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

Resolve `decision-resolution`, `implementation-planning`,
`architecture-guidance`, and when domain language is in scope
`domain-language-modeling` through the static DevFlow contract in
`scripts/workflow_methodology.py`. Use `grilling` for unresolved decisions;
DevFlow owns implementation planning; architecture work may use
`codebase-design`, while domain concepts and invariants explicitly add
`domain-modeling`. Record evidence and triggered skills in the Skill Routing Ledger.

## Required Shape

1. Target State — final external behavior and internal boundaries.
2. Scope / Non-Goals — explicit write and compatibility boundaries.
3. Architecture Decisions — choices, evidence, and rejected alternatives.
4. Completion Contract — binary acceptance criteria.
5. Critical Path — dependency-ordered required behavior protected from
   incidental work.
6. Incidental Finding Budget — normally one bounded RED/GREEN cycle inside the
   approved contract and write set.
7. Escalation Triggers (Authority Delta) — separate technical repair from
   concrete missing permission/risk; bind standing milestones to exact effects
   and targets.
   For model execution, define Standing Goal Execution Authority with exact
   task/provider/model/existing-auth credential policy/cost policy/serial
   identity. State that a one-use attempt receipt is technical evidence rather
   than one-use permission; record actual monetary cost without per-call
   confirmation, and route non-blocking related work to `DEFER_AND_CONTINUE`.
8. Capability Slices — dependency-ordered, production-complete slices; each
   includes implementation, validation, and cleanup.
9. Execution Ledger — owner, write set, status, evidence, and human gate.
10. Continuation Policy — default `auto-until-terminal`, the next-item
    selection rule, the six continuation outcomes, and every genuine Human
    Gate. A phase label alone is not a gate.
11. Generated Artifact Strategy — state whether disposable output exists. When
    it does, define pre-creation registration, a task/run isolated root or
    constrained adjacent scope, owner exit, retention, receipt, exact
    `AUTO_CLEAN`, repair, and Human Gate behavior.
12. Validation Commands — focused, broad, runtime, docs, and release checks.
13. Project Refresh Impact — for DevFlow changes, record disposition, inspected
    surfaces, schema decision, contract revision/digest, migration/fixture
    coverage, and source/release/cache proof; otherwise record why it is not
    applicable.
14. Project-Directed Implementation Readiness — when the project selects an
    external implementation provider, record the provider policy, target
    profile, exact capabilities, consumer/change bindings, evidence contract,
    limitations, and override policy. Mark unresolved readiness non-executable;
    do not add provider discovery, installation, activation, or fallback.
15. Risks / Rollback — stop conditions and reversible actions.
16. Goal Mode Prompt and Continue Prompt when recovery risk warrants them.
17. Review Checklist and Final Verification.

Required behavior does not belong in MVP, Future Work, or a later delivery
phase. Incidental hardening does not enter the Critical Path unless it affects
safe completion; classify and record it through the Incidental Finding
Lifecycle instead of silently expanding the plan.

## Workflow Gates

Behavior/API/data/integration/migration/compatibility/error-handling changes
require OpenSpec before implementation. Apply the Goal Suitability Gate through
`define-goal` when the user requests a goal or the work is long-running,
multi-slice, migration/release oriented, cross-context, delegation-backed, or
likely to lose its definition of done.

Add a SubAgent Strategy for independent Capability Slices. Record authorization
state, disjoint write sets, Agent Task Contract path, main-agent-owned
artifacts, and fallback. No worker starts before that contract is valid.

If a readiness Requirement applies, every product-mutation slice and mutating
delegation depends on a current Ready receipt plus its ordinary authority. A
direction review or draft requirement may precede that receipt; it cannot make
the plan execution-ready.

For disposable output, choose one registration-only Generated Artifact
Strategy. Prefer a task/run-specific isolated root. A contract must be sealed
before creation; a post-creation contract cannot legitimize residue. Record the
retention policy and require a fresh `AUTO_CLEAN` plan plus terminal cleanup
receipt before completion.

## Canonical Artifact Mapping

Methodology notes are review inputs. Promote approved decisions into OpenSpec
or the DevFlow Execution Ledger before they satisfy a gate; canonical files
win conflicts.

## Output Resources

When creating a durable task ledger, copy and adapt
`assets/task-ledger-template.md`; do not invent a second planning source. Read
`references/goal-prompt-template.md` only when the Goal Suitability Gate says
the plan needs Goal Mode or a recovery Continue Prompt.

## Completion

The plan is complete when every required behavior maps to a slice, criterion,
validation command, owner, rollback path, and ledger item, with no unresolved
Open Questions. Each non-terminal item also names its automatic next action so
the orchestrator can continue without routine phase confirmation.
