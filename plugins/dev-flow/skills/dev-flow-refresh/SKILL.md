---
name: dev-flow-refresh
description: Use when DevFlow has upgraded, when refreshing the local/global DevFlow plugin installation or installed cache, or when refreshing DevFlow project-local workflow configuration across active projects.
---

# DevFlow Refresh

Refresh DevFlow, then its active projects. This skill owns that sequence and
evidence; `codex-updater` owns full inventory/update,
`plugin-project-migration` owns the deterministic one-project plan/apply/
verify/rollback seam, `project-setup` owns first-time setup, and
`workflow-doctor` owns root-cause diagnosis. Do not reproduce migration logic
in this Skill.

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

Refresh only named projects or active projects with a trusted DevFlow adoption
marker: `.dev-flow.json`, `.planning/devflow/STATE.md`, or
`openspec/config.yaml`. `AGENTS.md`, legacy skill content, or a directory name
alone never opts a project into refresh.

After global freshness is established, whenever a specific project qualifies
for refresh, read `references/project-refresh.md` before running its read-only
diagnostics or making any project write. It owns the exact
`plugin_project_migration.py` plan/apply/verify/rollback sequence, supplemental
diagnostics, receipt handling, and legacy `.codex/skills` boundary.

When dependency-layout detail is needed, run
`activate_project_dependencies.py --dry-run --json` only as supplemental
read-only evidence. Project refresh writes still use the sealed migration
engine and its named authorizations.

Project writes require explicit intent, the sealed `planSha256`, the exact
selected actions, and every named authorization. Do not overwrite
`AGENTS.md`, resolve conflicts, remove legacy links, or apply a migration
merely because diagnostics found drift. The ordinary compatibility
`--apply` path never grants `workflow-config-migration` authority.

## 3. AGENTS Drift Gate

Every project plan checks durable workflow-rule drift semantically. Current
guidance remains unchanged. Stale guidance may create only a non-conflicting
`AGENTS.md.generated` merge candidate; active `AGENTS.md` is never overwritten.
The candidate is merge-required evidence, not active guidance. Merge only
durable workflow rules, preserve project rules, and keep task scope in OpenSpec
or the Execution Ledger. Record `git status` before and after any authorized
project refresh so unrelated work remains distinguishable.

## 4. Legacy Configuration Boundary

The planner may offer the ordered `legacy-selection-v0-to-v1` and
`full-openspec-v1-to-v2` chain only for a clean Git-tracked regular
`.dev-flow.json` with an exact rollback blob. It removes only retired
selectors, preserves every unrelated JSON value/type, sets `workflow.mode` to
`full-openspec`, advances the versioned project contract, redacts values, and
requires the separate `workflow-config-migration` authorization. Unsafe or
conflicting configuration stays manual-only. Legacy integration files and
`.codex/skills` cleanup remain separate actions with exact paths and approval.

Refresh contract revision 4 adds a recoverable uninstall path for recognized
project-local GSD, attested Superpowers skills, and obsolete generated OpenSpec
copies. The ordinary plan reports each `quarantine_path`, deterministic
quarantine destination, capability family, fingerprint, preserved path, and
named authorization. It remains read-only. GSD and Superpowers require
`legacy-workflow-uninstall`; obsolete OpenSpec copies require
`legacy-skill-layout-cleanup`. Selecting one item in a family requires selecting
the complete family. Ordinary compatibility `--apply` never selects either
authorization.

Authorized apply moves exact preimages below
`.planning/devflow/plugin-project-migration/quarantine/legacy-workflow-uninstall/`,
verifies both active absence and quarantine identity, and records receipt-bound
rollback. Preserve planning history, migration journals, backups, local
patches, ambiguous content, and every unclassified path. Do not purge retained
quarantine as part of refresh. Reload the Codex task after verified cleanup so
the surfaced Skill inventory no longer reflects removed project-local skills.

## 5. Implementation-Readiness Boundary

Project schemas 2 and 3 and their immutable configuration targets do not
acquire a provider-selection key. Refresh contract revision 4 retains the generic
implementation-readiness CLI, schemas, lifecycle guidance, Skills, templates,
and compatibility fixtures introduced by revision 3, while adding only the
legacy-uninstall refresh behavior above. The planner may report stale
Skill links or generated-guidance drift, but refresh does not create a
Requirement, choose a provider or target, write provider Evidence/Receipts,
record an override, or run provider commands.

After an authorized refresh, inspect any readiness namespace already owned by
the project and report whether its receipt remains current. A refreshed Skill
link or template never proves implementation readiness, and a source/release/
cache identity match never grants consumer apply or ordinary task authority.

## Final Evidence

Run receipt-bound `verify` after every apply. Report global source/release/cache
identity, included/skipped projects, plan digests, selected authorizations,
apply and verification receipts, changed/preserved paths, conflicts, manual
review, quarantine mappings, rollback availability, and task-reload need. Report `AGENTS status` as
`unchanged`, `merge-required`, or `candidate-conflict`. An unresolved manual
action, authorization, AGENTS merge, cleanup, dependency action, or cache drift
prevents a `refreshed`/`current` claim.
