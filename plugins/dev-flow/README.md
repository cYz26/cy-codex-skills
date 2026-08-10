# DevFlow

DevFlow is the Codex-first workflow router for one durable control plane:
OpenSpec owns behavior proposals/specs/tasks; DevFlow owns intake, execution
state, evidence, review, release gates, and project refresh. Matt skills supply
bounded engineering primitives without creating another workflow.

## Core Contract

- Full OpenSpec is required for behavior, API, data, persistence, integration,
  migration, permission, error-handling, and compatibility changes.
- `AGENTS.md`, `ENGINEERING_POLICY.md`, `TASK_LEDGER.md`,
  `EVIDENCE_TEMPLATE.md`, `REVIEW_CHECKLIST.md`, and
  `.planning/devflow/STATE.md` are the project control plane.
- Approved multi-item work uses `auto-until-terminal`; phases, reviews,
  verification, and checkpoints are not Human Gates.
- The authority-delta resolver is the only classifier. Repairable drift stops
  as `FAIL_CLOSED_REPAIR`; only non-empty concrete `missingAuthority` can become
  `AWAIT_HUMAN`, through the single receipt-bound gate recorder.

Minimal configuration is `{"workflow":{"mode":"full-openspec"}}`. Static
capability routing lives in `scripts/workflow_methodology.py`; unknown or
drifted required capabilities fail closed.

## Project-Directed Implementation Readiness

An approved plan may bind an `ImplementationReadinessRequirement v1` to an
exact provider, consumer revision, semantic plan, target profile, capabilities,
limitations, and evidence. Ready proves evidence, not authority. The gate never
discovers, installs, invokes, or substitutes a provider.

## Generated Artifact Lifecycle

The automatic task-owned reclamation requires a Generated Artifact Contract sealed
before creation. After owner exit, the trusted orchestrator may apply only a
fresh `AUTO_CLEAN` plan and must verify its cleanup receipt. `WAIT_OWNER`
retries; `RETAIN` preserves retained evidence; unsafe or drifted evidence is
technical repair. Legacy `HUMAN_GATE` is resolver input only. Direct CLI
mutation still requires `cleanup --apply`.
Recoverable quarantine remains exact and non-recursive; physical purge is a
separate destructive Human Gate. See `docs/generated-artifact-lifecycle.md`.

## Milestone External Effects

`scripts/milestone_external_effects.py` plans, advances, and verifies one sealed
standing milestone. It binds Goal/change, reviewed candidate, validation,
remote/ref, commit, immutable tag/Release assets, and named source/cache/project
targets. A current contract covers its predictable downstream chain once; it
never grants PR, merge, force-push, archive, alternate publication, or unnamed
refresh. Every effect is receipt-bound, read back, and same-identity idempotent.

## Incidental Finding Lifecycle

- `CONTINUE_WITH_MINIMAL_GUARD`: one required in-scope RED/GREEN guard.
- `DEFER_AND_CONTINUE`: record a non-blocking follow-up in `TASK_LEDGER.md`.
- `BLOCKED_AWAITING_HUMAN`: a concrete permission, ownership/product decision,
  or material risk acceptance is missing.

Required Completion Contract behavior cannot be deferred. The finding register
does not authorize follow-up work, and DevFlow never starts that follow-up
automatically; unresolved Human disposition blocks completion.

## SubAgent Strategy

DevFlow is the policy/router layer; scripts and hooks do not
spawn subagents. Delegation requires a validated Agent Task Contract and
disjoint write set. Root control-plane files, OpenSpec, `.planning/devflow/**`,
release metadata, generated release, integration, and final proof stay with the
main agent. Workers return `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or
`BLOCKED` with files, commands, tests, and risks.

## Goal Workflow

Use `define-goal` for user-requested goals and long-running,
migration/release, broad, cross-context, or delegation-backed work. A Goal
names outcome, verification evidence, scope/non-goals, threshold, and stop
conditions. Hooks may recommend a goal but never call goal tools.

## Project Refresh

`plugin_project_migration.py plan/apply/verify/rollback` is the only project
writer. Its sealed plan protects user-authored, historical, ambiguous, and
legacy files. DevFlow changes record versioned Project Refresh Impact with
tracked-input digests, schema decision, fixtures, and compatibility evidence.
Upgrading alone grants no standing authority and cleans no historical files.

## Release Promotion

Develop under `dev/plugins/dev-flow/`. The promotion gate copies allowlisted
assets and builds the deterministic runtime archive only after source-bound
verification:

```bash
python3 dev/plugins/dev-flow/scripts/release_promotion_gate.py --repo . --apply --json
python3 plugins/dev-flow/scripts/verify_release_runtime.py --plugin-root plugins/dev-flow --json
```

Run packaged tests and Plugin Eval against `plugins/dev-flow`. Publication uses
the reviewed exact-tag GitHub Actions path, then verifies tag, commit, asset
names, sizes, and SHA-256 before any named refresh. Git transport uses
`git ls-remote` independently of GitHub control-plane authentication and never
falls back to force, merge, rebase, alternate release, or another consumer.

## References

- `docs/side_effect_policy.json`: effect vocabulary and default-deny routes.
- `docs/generated-artifact-lifecycle.md`: cleanup invariants and receipts.
- `docs/git_transport_routing.md`: native Git versus GitHub control plane.
- `docs/dev-flow-release-policy.json`: deterministic version/tag/assets.
- `.codex-plugin/project-migration.json`: compatibility and refresh contract.
