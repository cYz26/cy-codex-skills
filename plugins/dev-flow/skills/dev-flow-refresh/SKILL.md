---
name: dev-flow-refresh
description: Use when DevFlow has upgraded, when refreshing the local/global DevFlow plugin installation or installed cache, or when refreshing DevFlow project-local workflow configuration across active projects.
---

# DevFlow Refresh

Refresh DevFlow, then its active projects. This skill owns that sequence and
evidence; `codex-updater` owns full inventory/update,
`plugin-project-migration` migration apply, `project-setup` first-time setup,
and `workflow-doctor` root-cause diagnosis.

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

## 2. Discover and Diagnose Projects

Refresh only named projects or active projects with a DevFlow marker such as
`AGENTS.md`, `.planning/devflow/STATE.md`, `openspec/config.yaml`, migration
state, or DevFlow links under `.agents/skills`.

After global freshness is established, whenever a specific project qualifies
for refresh, read `references/project-refresh.md` before running its read-only
diagnostics or making any project write. It owns the exact
`plugin_project_migration.py`, `validate_workflow_state.py`,
`doctor_workflow.py`, `scaffold_workflow.py`, and `git status` sequence, plus
the guarded `activate_project_dependencies.py` apply paths and legacy
`.codex/skills` handling.

Project writes require explicit intent. Do not overwrite `AGENTS.md`, resolve
conflicts, remove legacy links, or apply a
project migration merely because diagnostics found drift.

## 3. AGENTS Drift Gate

Every project refresh checks durable workflow-rule drift. If dry-run produces
`AGENTS.md.generated`, compare it with active `AGENTS.md`; it is merge-required
evidence, not guidance. Preserve project rules and keep task scope in OpenSpec
or the Execution Ledger. The project reference owns merge and validation.

## 4. Legacy Configuration Boundary

If diagnostics report retired workflow keys or legacy integration files, run
the read-only `inspect_legacy_workflow_config.py` report. Ordinary refresh does
not interpret, migrate, or remove them. Any cleanup is a separate action with
an exact file list, ownership review, rollback evidence, and explicit
authorization.

## Final Evidence

Rerun validation, cache-drift diagnosis, migration sync, and `git status` per
project. Report global status, included/skipped projects, changed/generated
files, conflicts, manual review, and restart need. Report `AGENTS status` as
`unchanged`, `merged`, `generated-deferred`, or `conflict`; deferred means the
current durable workflow rules may be stale.
