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

Project mutation requires explicit user intent to migrate/apply. Provider-file
migration and rollback are separate approvals from ordinary project migration.

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

Run ordinary project apply only when the user explicitly authorizes migration:

```bash
python3 scripts/plugin_project_migration.py --repo <repo> --apply --json
```

Apply mode may refresh safe project-local skill symlinks and writes audit
artifacts under `.planning/devflow/plugin-project-migration/`.

Apply provider selection/state files only after reviewing the separate dry-run
`providerMigration` report:

```bash
python3 scripts/plugin_project_migration.py \
  --repo <repo> \
  --apply-provider-files \
  --json
```

This snapshots every exact target and records its manifest below
`.planning/devflow/provider-migration/snapshots/<migration-id>/manifest.json`.
It does not install or update provider dependencies.

## Rollback Procedure

Rollback is destructive cleanup and is never inferred from sync, diagnosis, or
a failed migration. Obtain the exact `manifestPath` from the successful apply
result, review its target list, then run only after the user explicitly asks to
restore that file list:

```bash
python3 scripts/plugin_project_migration.py \
  --repo <repo> \
  --rollback-manifest <absolute-manifest-path> \
  --json
```

Supplying `--rollback-manifest` is the CLI authorization for the side-effect
policy `destructive.cleanup: explicit_file_list_and_rollback`. It is mutually
exclusive with `--apply` and `--apply-provider-files`. Rollback validates the
canonical manifest/checkpoint location, target and snapshot hashes, and every
target's current post-migration hash before the first restore. Any drift stops
without writes. A restore failure compensates already-restored targets back to
their verified post-migration state and requires review.

## Safety Rules

- Automatic hook/updater paths are sync-only.
- Default invocation is dry-run; never add a rollback manifest automatically.
- Do not replace non-symlink project-local skill directories.
- Do not overwrite user content outside declared managed targets.
- Never copy a manifest or snapshot to a different migration directory before
  rollback; canonical containment is part of the verification contract.
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
- report path under `.planning/devflow/plugin-project-migration/`;
- provider manifest path and rollback policy decision when those actions ran.
