## Why

Agent Reach is no longer a recommended Codex workflow dependency for this repository, but the DevFlow updater still includes it in dry-run and apply update plans when the executable is present. That keeps an outdated tool visible as something agents should maintain.

## What Changes

- Remove Agent Reach from DevFlow's automatic plugin/skill update planning.
- Ensure updater dry-runs and apply runs do not emit an `agent-reach` external-updater item.
- Mark Agent Reach as not recommended in repository and DevFlow documentation.
- Keep the change narrow: no uninstall, migration, or destructive cleanup is performed.

## Capabilities

### New Capabilities
- `devflow-updater-policy`: DevFlow update tooling policy for excluded or deprecated external tools.

### Modified Capabilities
- `current-system`: Repository baseline now records that Agent Reach is a deprecated, not-recommended skill.

## Impact

- Affected files:
  - `dev/plugins/dev-flow/scripts/codex_auto_update_plugins_skills.py`
  - `dev/plugins/dev-flow/tests/test_dependencies.py`
  - release-copy equivalents under `plugins/dev-flow/`
  - `README.md`
  - `dev/scripts/README.md`
  - DevFlow README files
- No production dependencies are added.
- No installed Agent Reach files are removed.
