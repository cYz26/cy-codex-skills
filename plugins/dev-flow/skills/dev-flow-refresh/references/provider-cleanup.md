# Provider Cleanup Procedure

Read this file only when the user explicitly requests deactivation or cleanup
of a selected methodology or roadmap provider.

Start with a dry-run and retain the complete report:

```bash
python3 dev/plugins/dev-flow/scripts/activate_project_dependencies.py \
  --repo <project> \
  --skip-official-installs \
  --deactivate-provider <provider-id> \
  --dry-run \
  --json > provider-cleanup-dry-run.json
```

Review verified project-local links, preservation decisions, per-link rollback
commands, and `planDigest`. Apply only with the same provider and digest:

```bash
python3 dev/plugins/dev-flow/scripts/activate_project_dependencies.py \
  --repo <project> \
  --skip-official-installs \
  --deactivate-provider <provider-id> \
  --authorize-provider-cleanup <provider-id> \
  --provider-cleanup-plan <planDigest> \
  --apply \
  --json > provider-cleanup-apply.json
```

Retain both JSON files and rerun dry-run after apply. Preserve unverified,
copied, conflicting, and manual-review paths. This operation never deletes
global provider configuration, installed plugin caches, or source caches;
global plugin disablement requires separate authorization.
