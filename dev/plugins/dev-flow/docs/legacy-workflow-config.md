# Legacy Workflow Configuration Inspector

DevFlow no longer activates retired workflow extensions. Their identifiers may
still appear in old project configuration, installation links, planning
history, or source-only historical documents. Those appearances are migration
evidence, not supported runtime choices.

## Read-Only Inspection

Run:

```bash
python3 scripts/inspect_legacy_workflow_config.py --repo . --json
```

The report:

- detects retired snake_case and camelCase selection keys;
- inventories old lock files, generated skill links, runtime markers, and
  historical planning paths;
- classifies safe generated candidates, preserved user/history data, unknown
  ownership, and conflicts;
- recommends `{"workflow":{"mode":"full-openspec"}}` as the current target;
- redacts all legacy values, provider-lock contents, and unrelated current
  configuration values while reporting field presence and value type;
- lists manual follow-up without changing the repository.

The inspector uses only the Python standard library. It does not import the
active dependency, activation, updater, migration, or release runtime. It has
no apply, install, activate, cleanup, rollback, unlink, rename, chmod, symlink,
network, Git, archive, or cache-refresh path.

## Migration Boundary

Current DevFlow readers fail closed when retired keys are present and direct the
operator here. They never infer a replacement or silently ignore the keys.
Project migration does not import this inspector and cannot apply its findings.

Any cleanup or migration is a separate future action requiring an exact file
list, ownership review, backup/rollback evidence, and explicit authorization.
Preserve ambiguous, user-authored, historical, and unreported current settings
by default.
