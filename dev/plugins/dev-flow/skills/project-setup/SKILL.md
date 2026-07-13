---
name: project-setup
description: Use when initializing or refreshing DevFlow workflow files in a project.
---

# Project Setup

Initialize DevFlow without inventing roadmap artifacts or overwriting project
guidance.

## Capability Routing

Default to `core + none`. Write `workflow.methodology_profile: core` and
`workflow.roadmap_provider: none` in `.dev-flow.json`; external providers are
opt-in. Resolve any requested profile from `docs/provider_profiles.json` and
show its activation plan before apply.

## Procedure

1. Run dependency and project-mode diagnosis.
2. Run `scripts/audit_context_tools.py --repo <repo> --json` and keep actions
   read-only unless separately approved.
3. Run `scripts/scaffold_workflow.py --repo <repo> --dry-run --json`.
4. Review writes, ownership, conflicts, and tracking status. Apply only after
   the plan is safe.
5. Run `scripts/validate_workflow_state.py --repo <repo> --json`.

DevFlow writes state, checkpoints, verification, context health, and brownfield
maps only under `.planning/devflow/`. Root `.planning/` roadmap/phase files are
created only by a selected roadmap provider. Existing `AGENTS.md` is preserved;
`AGENTS.md.generated` is merge-only.

Legacy state or provider links route through dry-run migration. Do not clean or
activate dependencies during scaffold. Setup is complete when validation names
the effective profile, all planned writes have one owner, and the next action
is explicit.
