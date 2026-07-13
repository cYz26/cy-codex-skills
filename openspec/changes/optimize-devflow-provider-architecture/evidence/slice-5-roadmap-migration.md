# Slice 5 Roadmap Ownership and Migration Evidence

## RED

The focused tests and final independent review first reproduced these unsafe
behaviors:

- DevFlow wrote/read legacy root planning state without one namespaced owner;
- GSD readiness could be inferred from installed files without a trusted
  content lock;
- rollback restored hashes without proving provider readiness;
- apply and rollback could overwrite a target changed after their first hash
  check; and
- GSD verification evidence could be supplied by caller-controlled result
  fields rather than the bound UAT artifact.

## GREEN

Command:

```bash
python3.12 -m unittest \
  dev/plugins/dev-flow/tests/test_planning_ownership.py \
  dev/plugins/dev-flow/tests/test_roadmap_provider.py \
  dev/plugins/dev-flow/tests/test_provider_migration.py \
  dev/plugins/dev-flow/tests/test_archive_policy.py \
  dev/plugins/dev-flow/tests/test_plugin_project_migration.py \
  dev/plugins/dev-flow/tests/test_checkpoint_compact_contract.py \
  dev/plugins/dev-flow/tests/test_context_health.py
```

Result: `Ran 111 tests in 3.962s` and `OK`.

Verified behavior:

- DevFlow-owned state, evidence, checkpoint, compact, context-health, and
  migration records are below `.planning/devflow/**`;
- GSD root roadmap/phase artifacts are read-only to DevFlow and are required
  only when `roadmap_provider: gsd` is selected;
- first GSD trust is bootstrapped only from an in-process successful pinned
  installer receipt, then bound to runtime, manifest, skill, and agent hashes;
- migration dry-run creates no snapshot or repository writes;
- authorized temporary-fixture apply is atomic and idempotent;
- apply and rollback recheck all target fingerprints before and during
  replacement, compensate safe partial work, and preserve concurrent edits;
- rollback re-diagnoses the recorded provider selection and restores only when
  readiness matches the pre-migration record; and
- GSD phase evidence is derived from the active binding and hash-current UAT,
  not caller-provided success fields.

No real project migration, provider install, GSD phase mutation, or archive was
executed.
