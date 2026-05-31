## Why

The current updater is useful as a conservative maintenance script, but review found three reliability gaps: marketplace refresh does not reinstall already installed plugins into cache, Git mirror dry-run output reports intent rather than actual update availability, and the repository-level updater script has drifted from the DevFlow plugin updater.

## What Changes

- Add installed-plugin refresh planning and apply behavior after marketplace updates.
- Add source-vs-installed plugin cache verification to the updater report.
- Make Git mirror dry-run perform a non-mutating remote comparison instead of always reporting `would-update`.
- Make the repository-level `dev/scripts` updater delegate to the canonical DevFlow updater implementation.
- Keep local modification safeguards: dirty Git mirrors and cache trees that differ from their known source are skipped rather than overwritten.

## Capabilities

### New Capabilities
- `devflow-updater-reliability`: DevFlow update tooling reliability, installed cache verification, and canonical updater entrypoint behavior.

### Modified Capabilities
- `devflow-updater-policy`: Deprecated-tool exclusion remains in force while updater reliability is improved.

## Impact

- Affected files:
  - `dev/plugins/dev-flow/scripts/codex_auto_update_plugins_skills.py`
  - `plugins/dev-flow/scripts/codex_auto_update_plugins_skills.py`
  - `dev/scripts/codex_auto_update_plugins_skills.py`
  - `dev/plugins/dev-flow/tests/test_dependencies.py`
  - `plugins/dev-flow/tests/test_release_smoke.py`
  - updater documentation and local automation prompt if needed
- No production dependencies are added.
- No installed plugin is removed.
