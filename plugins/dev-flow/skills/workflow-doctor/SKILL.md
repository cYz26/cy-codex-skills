---
name: workflow-doctor
description: Use when workflow state, specs, tasks, evidence, dependencies, or generated guidance drift.
---

# Workflow Doctor

Diagnose the broken contract before choosing repair size.

## Capability Routing

Resolve triggered methodology readiness through
`scripts/workflow_methodology.py`. Diagnose workflow, OpenSpec, triggered Matt
resources, goal, cache, and release readiness separately.

## Procedure

1. Run `scripts/validate_workflow_state.py --repo <repo> --json`.
2. Run `scripts/doctor_workflow.py --repo <repo> --write-report --json`.
3. Inspect `.dev-flow.json`, `.planning/devflow/STATE.md`, OpenSpec artifacts,
   tracking status, cache drift, and generated guidance.
   Also run `scripts/implementation_readiness.py inspect --repo <repo>
   --change-id <change> --json` when that canonical namespace exists. Report
   Requirement/Evidence/Receipt/override trust, exact binding drift, stable
   issue codes, and the one next action separately from ordinary authority.
   For an active change, compare `openspec status --change <id> --json` and
   `openspec instructions <artifact> --change <id> --json`; use returned
   `artifactPaths` and `actionContext` to distinguish schema paths from drift.
4. For unclear behavior or compatibility, route to `openspec-explore`. Retired
   workflow keys route to `inspect_legacy_workflow_config.py`.
5. State root cause, broken contracts, systemic repair, tests, docs, migration,
   compatibility, and verification. Then justify systemic, minimal, staged, or
   deferred execution.

Legacy or mixed state produces a read-only inspection plan; diagnosis preserves
user-owned files. `AGENTS.md.generated` remains a merge candidate. A doctor
result is complete when it separates blockers from warnings, names owners and
hashes, and supplies a safe next command.

Report resolver evidence read-only; repairable drift is not `AWAIT_HUMAN` and no marker is written.

The doctor never creates or promotes a Requirement, writes a Receipt or
override, selects a fallback, runs provider commands, or installs/activates a
provider.
