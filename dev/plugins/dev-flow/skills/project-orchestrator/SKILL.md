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
3. Run dependency diagnosis. Pass each capability needed by the current route
   explicitly, for example:
   `python3 scripts/check_dependencies.py --repo <repo> --capability implementation-planning --json`.
   If a required capability is missing, preview activation with the same
   repeatable `--capability` flags before any `--apply`.
4. Route current or external capability uncertainty through
   `capability-research` and its Capability Evidence Gate.
5. Route an incomplete OpenSpec change to `change-plan`, an approved item to
   `execute-task`, completion to `verify-and-archive`, and drift to
   `workflow-doctor`.
6. Route a non-trivial technical plan to `ai-native-tech-plan`.

## Capability Routing

Route stable capability IDs from `scripts/workflow_methodology.py`:
`decision-resolution`, `implementation-planning`,
`test-first-execution`, `root-cause-diagnosis`, `change-review`,
`completion-proof`, `execution-orchestration`, `architecture-guidance`, and
when domain language is in scope `domain-language-modeling`.
Only triggered Matt primitives are project-local requirements; OpenSpec and
DevFlow own canonical artifacts and evidence.

## Goal Gate

Route to `define-goal` when the user requests goal-backed work or the work is
long-running, multi-slice, migration/release oriented, cross-context, or likely
to lose its definition of done. A goal contract names outcome, verification,
scope, non-goals, success threshold, and stop conditions. Scripts may recommend
goal mode but do not call goal tools.

## SubAgent Decision Gate

Delegate when independent domains or disjoint write sets make parallel work
materially useful. First create a validated Agent Task Contract containing
Goal, Scope, Constraints, Verification, Evidence, and Human Gate. The main agent owns
OpenSpec, `.planning/devflow/`, shared docs, generated release paths, and final
integration without delegation exceptions. Each result reports status (`DONE`,
`DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`), files changed or
inspected, commands, risks, and review needs.

## Canonical Artifact Mapping

Methodology notes are inputs only. Promote approved content into the active
OpenSpec change or DevFlow ledger before it satisfies a gate.

## Incidental Finding Lifecycle

Route every out-of-path finding without creating a second backlog:

- `CONTINUE_WITH_MINIMAL_GUARD` for a bounded in-scope guard needed for safe
  completion;
- `DEFER_AND_CONTINUE` for optional non-blocking work recorded in the tracked
  `TASK_LEDGER.md` Incidental Finding Register;
- `BLOCKED_AWAITING_HUMAN` for severe, ambiguous, scope-expanding, authority-
  expanding, or product-decision work.

Unknown severity fails closed. A blocked finding stops mutation until the
human answers one concrete question and the decision is durable in OpenSpec or
the active ledger. The register does not authorize follow-up, and required
Completion Contract behavior cannot be deferred.

## Completion

The route is complete when it names workflow mode, required capabilities,
canonical artifacts, readiness blockers, side-effect approvals, next skill,
and validation command. Keep setup, planning, and repair read-only until the
selected action is approved.
