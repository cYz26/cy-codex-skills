---
name: project-setup
description: Use when initializing DevFlow workflow files or restoring a missing project control plane.
---

# Project Setup

Initialize a missing DevFlow control plane without inventing planning artifacts.
Route established-project upgrades to `dev-flow-refresh`.

## Capability Routing

Write the minimal `workflow.mode: full-openspec` configuration. Resolve
triggered capabilities from `scripts/workflow_methodology.py` and preview
project-local skill activation before apply.

## Procedure

1. Run dependency and project-mode diagnosis.
2. Run `scripts/audit_context_tools.py --repo <repo> --json` and keep actions
   read-only unless separately approved.
3. Run `scripts/scaffold_workflow.py --repo <repo> --dry-run --json`.
4. Review writes, ownership, conflicts, and tracking status. Apply only after
   the plan is safe.
5. Preview `scripts/activate_project_dependencies.py --repo <repo>
   --refresh-project-skills --dry-run --json`; explicit apply generates the
   six OpenSpec 1.7 skills in isolation and copies them to `.agents/skills`
   without enabling global OPSX prompts.
6. Run `scripts/validate_workflow_state.py --repo <repo> --json`.

DevFlow writes state, checkpoints, verification, context health, and brownfield
maps only under `.planning/devflow/`. Existing `AGENTS.md` is preserved;
`AGENTS.md.generated` is merge-only.

Legacy state or retired workflow files route through read-only inspection. Do
not clean or activate dependencies during scaffold. Setup is complete when the
minimal configuration is valid, all planned writes have one owner, and the
next action is explicit.
