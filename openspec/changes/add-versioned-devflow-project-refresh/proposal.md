## Why

DevFlow can refresh its installed plugin, project-local skills, and missing
control-plane files, but it cannot deterministically upgrade an established
project's retired `.dev-flow.json` configuration. The current Skill therefore
depends on agents interpreting several independent diagnostic commands, while
future DevFlow changes have no executable gate proving that the project-refresh
contract evolved with project-facing workflow changes.

## What Changes

- Keep `dev-flow-refresh` as the human-facing orchestration Skill for the
  global-before-project sequence, project discovery, authorization, AGENTS
  review, and final evidence.
- Deepen the existing `plugin_project_migration.py` CLI into the one
  deterministic single-project refresh seam with read-only plan, plan-bound
  apply, verification, transactional rollback, stable JSON, and compatibility
  for current read-only hook/updater callers.
- Version the project workflow schema independently from the DevFlow plugin
  release and provide a unique migration chain for known older configurations.
- Migrate only recognized, trusted configuration inputs; preserve unrelated
  settings and historical files, redact values from reports, and fail closed on
  ambiguous ownership, stale plans, path conflicts, or missing authorization.
- Keep active `AGENTS.md` merge-only and legacy `.codex/skills` cleanup outside
  automatic project refresh.
- Add an executable project-refresh contract digest and release-impact gate so
  changes to refresh-sensitive config, templates, skill inventory, dependency
  layout, or migration behavior cannot pass DevFlow pre-promotion and release
  verification with stale migration coverage.
- Add a required Project Refresh Impact disposition to DevFlow planning and
  review guidance.

## Capabilities

### New Capabilities

- `devflow-project-refresh`: Versioned, deterministic, reversible refresh of an
  established DevFlow project's workflow configuration and managed project
  surfaces behind explicit authorization.

### Modified Capabilities

- `devflow-plugin-quality`: DevFlow pre-promotion and release verification also
  prove project-refresh contract, migration registry, packaged CLI, and
  source/release/cache compatibility.

## Impact

- DevFlow migration/config/scaffold modules, the existing project migration CLI
  and state, refresh Skill/reference, manifests, tests, README, and generated
  project-control-plane guidance.
- Development and generated release plugin counterparts; installed-cache
  refresh and applying the migration to consumer projects remain separate
  explicit actions.
- Existing read-only hook/updater JSON remains compatible. No production
  dependency, automatic project discovery write, active AGENTS overwrite,
  legacy cleanup, commit, push, publication, or archive is introduced.
