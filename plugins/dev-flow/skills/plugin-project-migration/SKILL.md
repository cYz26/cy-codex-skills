---
name: plugin-project-migration
description: Use when plugin or skill runtime updates may require project-local configuration sync or migration.
---

# Plugin Project Migration

Use this Skill to inspect and apply project-local migrations after Codex
plugins or skills update.

## Boundary

Hooks and updater integration run sync-only checks. They may report pending
migrations, stale project-local skill links, or missing migration state, but
they do not edit `AGENTS.md`, `.agents/skills`, legacy `.codex/skills`,
`openspec/`, `.planning/`, or project scripts.

Project mutation requires explicit user intent to migrate/apply.

## Sync Procedure

1. Run the sync script from the DevFlow plugin root:

```bash
python3 scripts/plugin_project_migration.py --repo <repo> --json
```

2. Review:
   - active migration-aware plugins;
   - runtime plugin version;
   - stored project migration version;
   - missing or stale project-local skills;
   - conflicts;
   - recommended next action.

3. If the report is `migration_pending`, ask before applying unless the user
   already explicitly requested migration.

## Migrate Procedure

Run apply only when the user explicitly authorizes migration:

```bash
python3 scripts/plugin_project_migration.py --repo <repo> --apply --json
```

Apply mode may refresh safe project-local skill symlinks and writes audit
artifacts under `.dev-flow/plugin-project-migration/`.

## Safety Rules

- Automatic hook/updater paths are sync-only.
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
- report path under `.dev-flow/plugin-project-migration/`.
