# Provider Migration and Rollback

Read this file only after ordinary migration diagnostics identify a provider
state change, or when the user explicitly requests rollback of a recorded
provider migration.

## Provider-file migration

Review the dry-run `providerMigration` report, then apply only with explicit
provider-file authorization:

```bash
python3 scripts/plugin_project_migration.py \
  --repo <repo> \
  --apply-provider-files \
  --json
```

Apply snapshots every exact target and writes the canonical manifest below
`.planning/devflow/provider-migration/snapshots/<migration-id>/manifest.json`.
It does not install or update provider dependencies. Retain the apply result and
manifest as verification evidence.

## Destructive rollback

Obtain `manifestPath` from the successful apply result and review its exact
target list. Run only when the user explicitly asks to restore that list:

```bash
python3 scripts/plugin_project_migration.py \
  --repo <repo> \
  --rollback-manifest <absolute-manifest-path> \
  --json
```

`--rollback-manifest` is the CLI authorization for
`destructive.cleanup: explicit_file_list_and_rollback`; it is mutually
exclusive with `--apply` and `--apply-provider-files`. Never copy a manifest or
snapshot to another migration directory: canonical containment is verified.

Before the first restore, rollback verifies manifest/checkpoint location,
target and snapshot hashes, and every target's current post-migration hash. Any
drift stops without writes. A restore failure compensates already-restored
targets back to their verified post-migration state and requires review.
