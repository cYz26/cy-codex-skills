---
name: plugin-project-migration
description: Use when plugin or skill runtime updates may require project-local configuration sync or migration.
---

# Plugin Project Migration

Inspect and, when explicitly authorized, apply project-local migrations after
Codex plugins or skills update.

## Boundary

Hooks and updater integration run sync-only checks. They may report pending
migrations, stale project-local skill links, or missing migration state, but
they do not edit `AGENTS.md`, `.agents/skills`, legacy `.codex/skills`,
`openspec/`, `.planning/`, or project scripts.

Project writes require exact direct or named-standing authority. Retired
workflow configuration requires its own `workflow-config-migration`
authorization; ordinary compatibility apply never has it.

## Sync

1. Run the sync script from the DevFlow plugin root:

```bash
python3 scripts/plugin_project_migration.py --repo <repo> --json
```

Review:
   - active migration-aware plugins;
   - runtime plugin version;
   - stored project migration version;
   - missing or stale project-local skills;
   - conflicts;
   - recommended next action.

If the report is `migration_pending`, stop before writes unless the user already
requested migration.

For the versioned interface, prefer the read-only plan:

```bash
python3 scripts/plugin_project_migration.py plan \
  --repo <repo> --plugin-root <verified-dev-flow-root> --json
```

The plan is one-project-only, deterministic, redacted, and sealed by
`planSha256`. It reports exact managed read/write sets, fingerprints,
dependencies, authorizations, manual actions, preserved paths, verification,
and source contract identity.

## Ordinary Apply

Apply only with current direct or named-standing authority:

```bash
python3 scripts/plugin_project_migration.py --repo <repo> --apply --json
```

Apply mode may refresh safe project-local skill symlinks and writes audit
artifacts under `.planning/devflow/plugin-project-migration/`. It routes through
the same sealed transaction engine as the subcommands and never selects the
workflow-configuration action, `legacy-workflow-uninstall`, or
`legacy-skill-layout-cleanup`.
Official OpenSpec skill refresh is a separate isolated activation operation:
preview and then explicitly apply `activate_project_dependencies.py
--refresh-project-skills`. It copies verified OpenSpec 1.7 skills transactionally;
legacy `.codex/skills` remain migration inputs and are not auto-deleted.

## Versioned Apply, Verify, and Rollback

Apply a reviewed plan with exact current authorizations and optional repeated
`--action` selections:

```bash
python3 scripts/plugin_project_migration.py apply \
  --repo <repo> --plugin-root <verified-dev-flow-root> \
  --expect-plan <sha256:...> \
  --allow project-refresh-apply \
  --allow workflow-config-migration \
  --allow legacy-workflow-uninstall \
  --allow legacy-skill-layout-cleanup --json
```

Supply only the authorizations present in the reviewed plan. Recognized GSD and
Superpowers cleanup uses `legacy-workflow-uninstall`; verified obsolete
generated OpenSpec copies use `legacy-skill-layout-cleanup`. Cleanup actions
move exact file, symlink, or trusted-tree preimages into deterministic retained
quarantine and are family-closed: select every action in a reported family or
none. Ambiguous, mixed-ownership, historical, user-authored, or unclassified
paths remain manual/preserved and are never imported into either authority.

Standing authority never widens a plan; identity/action drift stops.

The executor preflights the complete selected transaction, stages in an
isolated project-local root, promotes deterministically, verifies, advances
state last, and emits apply plus verification receipts. Verify or roll back a
receipt with:

```bash
python3 scripts/plugin_project_migration.py verify \
  --repo <repo> --plugin-root <verified-dev-flow-root> \
  --receipt <apply-receipt> --json
python3 scripts/plugin_project_migration.py rollback \
  --repo <repo> --plugin-root <verified-dev-flow-root> \
  --receipt <apply-receipt> --apply --json
```

Without rollback `--apply`, the command is authorization-required and
read-only. Rollback refuses any post-apply edit.

## Legacy Configuration

The isolated inspector remains available for diagnosis. Automatic rewrite is
limited to one recognized non-conflicting legacy shape in a clean Git-tracked
regular `.dev-flow.json` with an exact commit/blob preimage. It removes only
retired selectors, preserves unrelated values/types, sets
`workflow.mode=full-openspec`, emits no raw values, and requires
`workflow-config-migration`. All ambiguous, untracked, dirty, non-Git,
unreadable, symlinked, or non-regular inputs remain unchanged and manual-only.
Old integration files and cleanup are never imported into configuration
migration authority. Revision-4 project refresh may separately plan exact
recognized legacy uninstall actions under the two named cleanup authorizations.

## Safety Rules

- Automatic hook/updater paths are sync-only.
- Default invocation is dry-run.
- Do not replace non-symlink project-local skill directories.
- Do not overwrite user content outside declared managed targets.
- Stop and report conflicts when a managed target has local content.
- Never overwrite active `AGENTS.md`; create only a non-conflicting
  `AGENTS.md.generated` merge candidate.
- Preserve legacy `.codex/skills`, custom official-skill copies, and historical
  planning data unless an exact obsolete generated OpenSpec copy is listed in a
  sealed revision-4 cleanup plan and `legacy-skill-layout-cleanup` is supplied.
- Never purge retained legacy-uninstall quarantine during ordinary refresh.
- Refreshing revision-4 Skills/templates never creates or changes an
  implementation-readiness Requirement, provider Evidence/Receipt, provider
  override, selection, installation, activation, or command execution.
- Treat `applied_incomplete` and `verified_incomplete` as attention, not a
  refreshed/current claim.
- Report generated files, conflicts, and validation commands before claiming
  migration is complete.

## Output

Summarize:

- current runtime version;
- project stored version;
- pending migrations or drift;
- changed files if apply ran;
- conflicts and manual next steps;
- report path under `.planning/devflow/plugin-project-migration/`.
- plan digest, selected action IDs, authorizations, apply/verification receipts,
  active-to-quarantine mappings, rollback status, and the exact next action;
- whether a new Codex task/session is required to reload the surfaced Skill
  inventory after cleanup.
