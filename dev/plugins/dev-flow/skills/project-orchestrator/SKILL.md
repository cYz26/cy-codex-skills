---
name: project-orchestrator
description: Use when routing Codex setup, planning, execution, verify, or repair.
---

# Project Orchestrator

Router for Codex-first project work.

## Procedure

Read `AGENTS.md`, `.planning/STATE.md`, and `openspec/config.yaml`. Run dependency check; activate missing project-local dependencies.

Also check the contract-first control plane when execution or delegation is in
scope: `ENGINEERING_POLICY.md`, `TASK_LEDGER.md`,
`EVIDENCE_TEMPLATE.md`, and `REVIEW_CHECKLIST.md`.

## Repair Framing

For bugs, broken workflows, state drift, or failed mechanisms, apply systemic repair framing
before choosing an execution size. The route should gather
enough evidence to describe the systemic and thorough solution first, then
justify whether the work should execute that solution, a minimal fix, a staged
repair, or a deferred follow-up.

## SubAgent Decision Gate

At planning, execution, context-health, and review boundaries, evaluate whether
subAgents would materially improve the work. Recommend a split when the task has
independent domains, disjoint write sets, repeated investigation pressure,
repeated command failures, or a bounded review/delegation need.

If the user or active workflow has not authorized delegated parallel work,
recommend a split without spawning subAgents. Delegation requires explicit user authorization,
an approved GSD execution flow, or an approved Superpowers subagent plan before execution.

Reuse existing execution systems instead of duplicating them: route approved
phase/wave execution to `gsd-execute-phase`, task-by-task implementation to
`subagent-driven-development`, independent investigation to
`dispatching-parallel-agents`, and inline fallback to `executing-plans`.

Before delegation, define worker ownership and disjoint write sets. The main agent owns OpenSpec
artifacts, `.planning/STATE.md`, verification evidence, shared README/docs
coordination, and final integration unless those shared files are explicitly
serialized.

Require each subAgent result to report status (`DONE`, `DONE_WITH_CONCERNS`,
`NEEDS_CONTEXT`, or `BLOCKED`), files changed or inspected, commands or tests
run, residual risks, and review needs. The main agent reviews diffs and reruns
validation before marking ledger items complete.

## Routing

- No workflow files: use `project-setup`.
- Use `docs/routing.matrix.json` as the machine-readable workflow routing
  source. Full OpenSpec remains mandatory for behavior, API, data model,
  persistence, migration, integration, permission, error-handling, or
  compatibility changes.
- Apply the Goal Suitability Gate during routing, before context-health drift
  appears. Use `define-goal` when the user asks to create, set, refine, or use a
  goal, asks for goal-backed execution, or when the development task is
  long-running, multi-slice, migration or release oriented, broad-refactor
  oriented, cross-context,
  subagent/delegation backed, or otherwise likely to lose its definition of
  done. `define-goal` owns the active goal check and goal-tool calls.
- After `define-goal` shapes the objective, use `/goal <objective>` in a Codex
  app, IDE, or CLI composer. Use `/goal`, `/goal pause`, `/goal resume`, and
  `/goal clear` to inspect or control it; if unavailable, enable
  `features.goals` or run `codex features enable goals`.
- For ordinary implementation work that is narrow, do not force goal creation
  only because the task has multiple steps; route through the normal DevFlow
  gates below. Treat context-health goal drift as a repair signal, not the
  primary trigger.
- For design, research, architecture, or product-shape requests with open goals,
  constraints, tradeoffs, or implementation shape, use `feature-intake before ai-native-tech-plan`.
  Intake must decide whether `capability-research`,
  `superpowers:brainstorming`, OpenSpec, GSD, or `ai-native-tech-plan` owns the
  next gate.
- Technical plan, implementation plan, architecture plan, Codex execution plan, workflow plan, or anti-partial-delivery request: use `ai-native-tech-plan`.
- Current, external, platform, plugin, API, hook, CLI, installed-cache, or local-vs-platform capability uncertainty: use `capability-research` for the Capability Evidence Gate before choosing a solution.
- New feature, bug, behavior/API change, migration, or integration: use `feature-intake`.
- Active change without proposal/design/specs/tasks: use `change-plan`.
- Approved task with plan and tests ready: use `execute-task`.
- Implementation complete or user asks to finish: use `verify-and-archive`.
- State files conflict or artifacts are missing: use `workflow-doctor`.
- Major workflow boundary or context cleanup request: use `checkpoint-compact`.
- Global plugin/skill context audit, cleanup recommendation, or authorized cleanup/install request: use `context-tool-audit`.

## Dependency Skills

Routes: `capability-research`; `ai-native-tech-plan`; `superpowers:brainstorming`, `superpowers:writing-plans`, `superpowers:test-driven-development`, `superpowers:verification-before-completion`; `openspec-explore`, `openspec-propose`, `openspec-apply-change`, `openspec-archive-change`; `gsd-discuss-phase`, `gsd-plan-phase`, `gsd-execute-phase`, `gsd-verify-work`.

## Superpowers Artifact Mapping

Superpowers provides process discipline; OpenSpec, GSD, and DevFlow planning files are the canonical artifacts. Map `docs/superpowers/specs/...` into `openspec/changes/<change-id>/proposal.md`, `design.md`, or `specs/` for behavior work. Map `docs/superpowers/plans/...` into `openspec/changes/<change-id>/tasks.md`, `.planning/phases/.../PLAN.md`, or a DevFlow-approved Execution Ledger before implementation.

Use `docs/superpowers_gate_matrix.json` as the machine-readable method gate
source. Superpowers docs, SDD reports, and review notes must be promoted through
the artifact mapping rules before they satisfy DevFlow canonical gates.

## Safety

Do not edit production code during setup/intake/planning. Do not archive without verification evidence. Ask before dependencies, migrations, API breaks, or broad rewrites. Treat GSD phases as workflow governance; technical completion is governed by Target State, Completion Contract, Capability Slices, Execution Ledger, and Validation Commands. DevFlow hooks and scripts do not call goal tools; they can only route users back to `define-goal` in a Codex surface that supports goals.
