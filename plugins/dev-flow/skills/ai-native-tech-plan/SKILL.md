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
- SubAgent Strategy
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
2. Add a Skill Routing Ledger before the final plan or design. Record request
   kind, workflow mode, `capability-research: required/used/skipped`,
   `brainstorming: required/used/skipped`, `decision-grilling:
   required/used/skipped`, `writing-plans: required/used/skipped/pending`,
   OpenSpec/GSD routing, and the reason for any skipped gate.
3. If behavior, API, persistence, integration, compatibility, or error handling changes are involved, route through OpenSpec before implementation.
4. If the plan depends on current documentation, external/platform behavior, plugin or hook semantics, local installed cache, or unstable platform assumptions, use `capability-research` before choosing the implementation path.
5. If goals, constraints, tradeoffs, implementation shape, or Open Questions remain, use `superpowers:brainstorming`; if Brainstorming has not happened yet, mark the artifact as draft, not final. If Open Questions remain after evidence gathering, use decision-grilling: inspect local evidence first, ask one question at a time, provide a recommended answer, and map resolved decisions into OpenSpec, GSD, or a DevFlow ledger.
6. Apply the Goal Suitability Gate before writing the final plan, before
   context-health drift appears. Route goal creation/refinement through
   `define-goal` when the user asks for a goal or when the task is
   long-running, multi-slice, migration or release oriented, broad-refactor
   oriented, cross-context, subagent/delegation backed, or otherwise likely to
   lose its definition of done. The Goal Mode Prompt should include
   verification evidence, scope boundaries, non-goals, and stop conditions, but
   this skill does not call goal tools directly. Before goal creation, apply the
   Goal Quality Gate so the candidate objective also names the outcome, success
   threshold, and conditions that require stopping for human guidance. After `define-goal` shapes the
   objective, use `/goal <objective>` in a Codex app, IDE, or CLI composer; use
   `/goal`, `/goal pause`, `/goal resume`, and `/goal clear` to inspect or
   control it. If unavailable, enable `features.goals` or run
   `codex features enable goals`. Treat context-health goal drift as a repair
   signal, not the primary trigger.
   - Complexity gate: use project complexity and recovery cost as inputs. Add
     +2 for multiple OpenSpec changes, +2 for multiple capability slices, +2
     for prompts like "continue/依次/持续/until human/直到需要人工介入", +1 for
     data model, persistence, integration, migration, AI/API, or platform
     collection, +1 for archive/release gates, and +1 for expected interruption
     or context compaction. Score >=3 means include a Goal Mode Prompt and stop
     for `/goal <objective>` or explicit skip; score 1-2 means recommend a
     goal; score 0 means no goal required.
7. Before committing to a non-trivial implementation plan, use `superpowers:writing-plans`.
8. Add a SubAgent Strategy section when independent Capability Slices can run in
   parallel or when context-health/review risk suggests delegation. Record the
   authorization state, proposed worker ownership, disjoint write sets,
   Agent Task Contract path and validation command, main-agent-owned artifacts,
   and fallback when subAgents are unavailable. The Agent Task Contract must
   define Goal, Scope, Constraints, Verification, Evidence, and Human Gate
   before any delegated agent, subagent, worker, or parallel execution starts.
9. For medium or large tasks, write the Execution Ledger to a repo file such as `.ai/tasks/<yyyy-mm-dd>-<task-name>.md`, or the repo's established planning location.
10. During implementation, use `superpowers:test-driven-development` where applicable and update ledger statuses only after validation.
11. Before completion, use `superpowers:verification-before-completion` and verify the Completion Contract.

## Superpowers, GSD, and OpenSpec Fit

- Superpowers provides brainstorming, writing-plans, test-driven-development, and verification-before-completion discipline.
- GSD phases are governance and sequencing containers, not technical completion boundaries.
- OpenSpec remains required for behavior-level proposal, design, specs, tasks, verification, sync, and archive.
- The AI-native plan adds execution contracts, ledgers, and validation surfaces so work can continue after interruption or compaction.

## Superpowers Artifact Mapping

Use Superpowers outputs as planning discipline, then persist the approved result in canonical workflow files. `docs/superpowers/specs/...` maps to OpenSpec proposal/design/specs for behavior work. `docs/superpowers/plans/...` maps to OpenSpec `tasks.md`, `.planning/phases/.../PLAN.md`, or a DevFlow-approved ledger. Do not keep Superpowers notes as a second source of truth after the canonical artifacts exist.

## Output Contract

When generating a plan, include:

1. Skill Routing Ledger
2. Target State
3. Scope / Non-Goals
4. Architecture Decisions
5. SubAgent Strategy
6. Completion Contract
7. Capability Slices
8. Execution Ledger
9. Acceptance Criteria
10. Validation Commands
11. Risks / Rollback
12. Goal Mode Prompt
13. Continue Prompt
14. Review Checklist

For detailed templates, read only the relevant bundled file:

- Planning principles: `references/planning-principles.md`
- AGENTS.md snippet: `references/agents-md-snippet.md`
- Goal and continue prompts: `references/goal-prompt-template.md`
- Task ledger template: `assets/task-ledger-template.md`
- Review checklist: `assets/review-checklist.md`
