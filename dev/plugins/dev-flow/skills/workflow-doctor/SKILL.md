---
name: workflow-doctor
description: Use when workflow state, provider selection, specs, tasks, evidence, or generated guidance drift.
---

# Workflow Doctor

Diagnose the broken contract before choosing repair size.

## Capability Routing

Resolve provider readiness through `docs/provider_profiles.json`. Diagnose core,
methodology, roadmap, goal, and release readiness separately. An unselected
provider never blocks workflow health.

## Procedure

1. Run `scripts/validate_workflow_state.py --repo <repo> --json`.
2. Run `scripts/doctor_workflow.py --repo <repo> --write-report --json`.
3. Inspect `.dev-flow.json`, `.planning/devflow/STATE.md`, provider lock,
   OpenSpec artifacts, tracking status, cache drift, and generated guidance.
   For an active change, compare `openspec status --change <id> --json` and
   `openspec instructions <artifact> --change <id> --json`; use returned
   `artifactPaths` and `actionContext` to distinguish schema paths from drift.
4. For unclear behavior or compatibility, route to `openspec-explore`. For
   roadmap drift, use the selected read-only roadmap adapter.
5. State root cause, broken contracts, systemic repair, tests, docs, migration,
   compatibility, and verification. Then justify systemic, minimal, staged, or
   deferred execution.

Legacy or mixed state produces a migration plan; diagnosis never rewrites root
roadmap files or user-owned provider links. `AGENTS.md.generated` remains a
merge candidate. A doctor result is complete when it separates blockers from
warnings, names owners and hashes, and supplies a safe next command.
