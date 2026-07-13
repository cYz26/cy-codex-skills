---
name: project-orchestrator
description: Use when routing Codex setup, planning, execution, verification, or workflow repair.
---

# Project Orchestrator

Route project work through one canonical control plane. Read `AGENTS.md`,
`.dev-flow.json`, `.planning/devflow/STATE.md`, `openspec/config.yaml`, and the
active ledger before choosing a workflow action.

## Route

1. If workflow files are missing, route to `project-setup`.
2. Classify the request with `feature-intake` and
   `docs/routing.matrix.json`. Full OpenSpec is mandatory for behavior, API,
   data, persistence, integration, migration, permission, error-handling, or
   compatibility work.
3. Run dependency diagnosis. Resolve the configured methodology profile and
   roadmap provider before proposing activation; diagnosis is read-only. Pass
   each capability needed by the current route explicitly, for example:
   `python3 scripts/check_dependencies.py --repo <repo> --capability implementation-planning --json`.
   If a selected capability is missing, preview activation with the same
   repeatable `--capability` flags before any `--apply`.
4. Route current or external capability uncertainty through
   `capability-research` and its Capability Evidence Gate.
5. Route an incomplete OpenSpec change to `change-plan`, an approved item to
   `execute-task`, completion to `verify-and-archive`, and drift to
   `workflow-doctor`.
6. Route a non-trivial technical plan to `ai-native-tech-plan`.

## Capability Routing

Route stable capability IDs from `docs/provider_profiles.json`, never a
provider name: `decision-resolution`, `implementation-planning`,
`test-first-execution`, `root-cause-diagnosis`, `change-review`,
`completion-proof`, `execution-orchestration`, and `architecture-guidance`.
The resolved profile supplies the implementation; OpenSpec and DevFlow still
own canonical artifacts and evidence. Provider-specific mappings and migration
rules live in `docs/provider-profile-migration.md`.

## Goal Gate

Route to `define-goal` when the user requests goal-backed work or the work is
long-running, multi-slice, migration/release oriented, cross-context, or likely
to lose its definition of done. A goal contract names outcome, verification,
scope, non-goals, success threshold, and stop conditions. Scripts may recommend
goal mode but do not call goal tools.

## SubAgent Decision Gate

Recommend a split without spawning when independent domains or disjoint write
sets make delegation useful but authority is absent. With explicit user
authorization, create a validated Agent Task Contract containing Goal,
Scope, Constraints, Verification, Evidence, and Human Gate. The main agent owns
OpenSpec, `.planning/devflow/`, shared docs, and final integration unless the
contract serializes those writes. Each result reports status (`DONE`,
`DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`), files changed or
inspected, commands, risks, and review needs.

## Compatibility Artifact Mapping

Provider drafts are inputs only. Promote approved methodology notes, including
legacy `docs/superpowers/specs/` and `docs/superpowers/plans/`, into the active
OpenSpec change, selected roadmap-provider plan, or DevFlow ledger before they
satisfy a gate.

## Completion

The route is complete when it names workflow mode, required capabilities,
canonical artifacts, readiness blockers, side-effect approvals, next skill,
and validation command. Keep setup, planning, and repair read-only until the
selected action is approved.
