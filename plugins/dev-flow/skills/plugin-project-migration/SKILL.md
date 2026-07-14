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

Project mutation requires explicit user intent to migrate/apply. Retired
workflow configuration is outside ordinary project migration.

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

## Ordinary Apply

Run ordinary project apply only when the user explicitly authorizes migration:

```bash
python3 scripts/plugin_project_migration.py --repo <repo> --apply --json
```

Apply mode may refresh safe project-local skill symlinks and writes audit
artifacts under `.planning/devflow/plugin-project-migration/`.
Official OpenSpec skill refresh is a separate isolated activation operation:
preview and then explicitly apply `activate_project_dependencies.py
--refresh-project-skills`. It copies verified 1.6 skills transactionally;
legacy `.codex/skills` remain migration inputs and are not auto-deleted.

## Legacy Configuration

When retired workflow keys or old integration files are present, run
`inspect_legacy_workflow_config.py` separately. This migration skill does not
import that inspector, apply its findings, or perform cleanup. Preserve
ambiguous and user-authored files until a separately approved action names
exact paths and rollback evidence.

## Safety Rules

- Automatic hook/updater paths are sync-only.
- Default invocation is dry-run.
- Do not replace non-symlink project-local skill directories.
- Do not overwrite user content outside declared managed targets.
- Stop and report conflicts when a managed target has local content.
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
