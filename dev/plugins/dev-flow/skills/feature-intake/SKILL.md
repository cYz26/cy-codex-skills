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
  `Full OpenSpec`, `Lightweight Ledger`, or `Prototype Mode`. Use
  `docs/routing.matrix.json` as the machine-readable route source.
- Apply the Goal Suitability Gate before execution, before context-health drift
  appears. Use `define-goal` when the user asks to create, set, refine, or use a
  goal, or when the development task is long-running, multi-slice, migration or
  release oriented, broad-refactor oriented, cross-context,
  subagent/delegation backed, or otherwise likely to lose its definition of
  done. `define-goal` owns active goal checks and requires verification
  evidence, scope boundaries, and stop conditions before goal creation. Apply
  the Goal Quality Gate before goal creation: the candidate objective must also
  include outcome, non-goals, and a pass/fail success threshold.
- Treat implementation complexity and recovery cost as Goal Suitability inputs,
  not calendar estimates. Require a goal when complexity score is 3 or higher:
  +2 multiple OpenSpec changes, +2 multiple capability slices, +2 language such
  as "continue/依次/持续/until human/直到需要人工介入", +1 data model,
  persistence, integration, migration, AI/API, or platform collection, +1
  archive/release gate, +1 expected interruption or context compaction. Score
  1-2 recommends a goal; score 0 does not. Record required gates in
  `.planning/STATE.md` under `goal_gate` and pause for `/goal <objective>` or
  an explicit skip with reason.
- After `define-goal` shapes the objective, use `/goal <objective>` in a Codex
  app, IDE, or CLI composer. Use `/goal`, `/goal pause`, `/goal resume`, and
  `/goal clear` to inspect or control it; if unavailable, enable
  `features.goals` or run `codex features enable goals`.
- Do not require a Codex goal for ordinary narrow implementation work solely
  because it has multiple steps. Treat context-health goal drift as a repair
  signal after drift is discovered, not the primary trigger.
- Use `ai-native-tech-plan` for technical plans, implementation plans, architecture plans, Codex execution plans, workflow plans, or requests to avoid partial delivery.
- Use `capability-research` when the requirement depends on a current or external capability, platform behavior, plugin/runtime behavior, hook/API support, CLI support, installed-cache state, or local-vs-platform ambiguity.
- Use `superpowers:brainstorming` for open goals, constraints, tradeoffs, or implementation shape.
- Use decision grilling inside brainstorming when plan/design ambiguity remains:
  inspect local evidence first, ask one question at a time, provide a
  recommended answer, and map resolved decisions into canonical OpenSpec, GSD,
  or DevFlow ledger artifacts. Use `scripts/workflow_decision_grilling.py
  --json` when a machine-readable routing check is useful.
- Use `openspec-explore` for unclear behavior, compatibility, requirements, or acceptance criteria.
- Use `openspec-propose` before behavior/API/data/integration changes.
- Use `gsd-discuss-phase` and `gsd-plan-phase` for stages, refactors, or milestones.
- Use `superpowers:writing-plans` before committing to a non-trivial plan.
- Before delegated agent, subagent, worker, or parallel execution, require an
  Agent Task Contract with Goal, Scope, Constraints, Verification, Evidence,
  and Human Gate sections. Ordinary narrow main-agent work does not need this
  gate solely because it has multiple steps.

## Skill Routing Ledger

For design, research, architecture, product-shape, or technical-plan requests,
record the routing decision before writing the final artifact:

- kind: one of the classification kinds above.
- workflow mode: Full OpenSpec, Lightweight Ledger, or Prototype Mode.
- capability-research: required/used/skipped, with reason.
- brainstorming: required/used/skipped, with reason.
- decision-grilling: required/used/skipped, with reason.
- writing-plans: required/used/skipped/pending, with reason.
- openspec/gsd: required/used/skipped, with reason.

If goals, constraints, tradeoffs, implementation shape, or `Open Questions`
remain, `brainstorming` cannot be skipped. Mark any generated design as draft
until `superpowers:brainstorming` resolves the choice or the ledger records
`brainstorming: required`. If `Open Questions` remain, decision grilling also
cannot be skipped unless the questions are already answerable from local code,
runtime, cache, tool-output, or authoritative documentation evidence.

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

Contract-first work must record or validate `TASK_LEDGER.md`,
`EVIDENCE_TEMPLATE.md`, and `REVIEW_CHECKLIST.md` before execution or
verification claims.

## Superpowers Artifact Mapping

When Superpowers produces `docs/superpowers/specs/...` or `docs/superpowers/plans/...`, treat those files as drafts or review notes. For behavior work, copy the approved design and task content into canonical OpenSpec artifacts under `openspec/changes/<change-id>/`. For phase or milestone work, copy the approved plan content into `.planning/phases/.../PLAN.md` or a DevFlow-approved ledger.

Use `docs/superpowers_gate_matrix.json` to explain required method gates, and
use artifact promotion checks before accepting Superpowers outputs as canonical.

## Output

For behavior work, clarify Target State, Completion Contract, validation surface, success criteria, and the Skill Routing Ledger, then run `scripts/create_change.py --repo <repo> --change-id <id> --title <title> --type <kind> --json`.
