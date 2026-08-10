---
name: dev-flow-refresh
description: Use when DevFlow has upgraded, when refreshing the local/global DevFlow plugin installation or installed cache, or when refreshing DevFlow project-local workflow configuration across active projects.
---

# DevFlow Refresh

Refresh DevFlow before its named projects. `codex-updater` owns broad inventory,
`plugin-project-migration` owns the one-project plan/apply/verify/rollback seam,
`project-setup` owns first setup, and `workflow-doctor` owns diagnosis.

## 1. Global Before Project

Start with the targeted local plugin refresh unless the user explicitly asks
for the broader `codex-updater` workflow:

```bash
codex plugin add dev-flow@cy-codex-skills --json
```

Verify source/cache freshness before claiming the global refresh is complete.
Use the first checker that exists in the current repository:

```bash
python3 dev/plugins/dev-flow/scripts/doctor_workflow.py --repo <repo> --check-cache-drift --json
python3 dev/scripts/codex_auto_update_plugins_skills.py --json
```

Do not claim cache freshness from the install command alone.

## 2. Route Each Named Project

Refresh only named projects or active projects with a trusted DevFlow adoption
marker: `.dev-flow.json`, `.planning/devflow/STATE.md`, or
`openspec/config.yaml`. `AGENTS.md`, legacy skill content, or a directory name
alone never opts a project into refresh.

After global freshness, read [the project refresh procedure](references/project-refresh.md)
before running its read-only diagnostics or making any project write. It owns the exact
`plugin_project_migration.py` commands, receipts, rollback, quarantine, and
legacy `.codex/skills` boundary. Do not duplicate migration logic here.

When dependency-layout detail is needed, run
`activate_project_dependencies.py --dry-run --json` only as supplemental
read-only evidence. Project refresh writes still use the sealed migration
engine and its named authorizations.

## 3. Guard Every Write

Require explicit intent, the sealed `planSha256`, exact selected actions, and
every named authorization. Drift alone never authorizes apply, conflict
resolution, legacy cleanup, or configuration migration. Preserve history,
receipts, quarantine, backups, local patches, ambiguous content, and all
unclassified paths.

### AGENTS Drift Gate

Keep current guidance unchanged. Treat `AGENTS.md.generated` only as a merge
candidate; never overwrite active `AGENTS.md`.
Merge only durable workflow rules while preserving project rules. Record
`git status` before and after an authorized refresh.

Configuration migration, recognized project-local GSD/legacy uninstall,
obsolete-skill cleanup, and
implementation-readiness artifacts retain their separate authorizations and
ownership. Refresh never chooses a provider, synthesizes readiness evidence,
or turns source/release/cache parity into consumer authority. Standing
authority covers only its exact named cache/project plan/apply/verify target.

## Final Evidence

Run receipt-bound `verify` after every apply. Report global source/release/cache
identity, included/skipped projects, plan digests, selected authorizations,
apply and verification receipts, changed/preserved paths, conflicts, manual
review, quarantine mappings, rollback availability, and task-reload need. Report `AGENTS status` as
`unchanged`, `merge-required`, or `candidate-conflict`. An unresolved manual
action, authorization, AGENTS merge, cleanup, dependency action, or cache drift
prevents a `refreshed`/`current` claim.
