## Why

DevFlow currently integrates Superpowers, GSD, and OpenSpec, but the ownership boundary is implicit. Superpowers 5.1.0 writes its own spec and plan artifacts by default, while DevFlow treats OpenSpec/GSD/DevFlow files as the durable workflow source of truth; without an explicit mapping, agents can create parallel plans that drift.

The dependency workflow also needs better update reliability: project-local Superpowers symlinks can remain pointed at an old cached plugin path after marketplace cache rotation, `gsd-progress` is used but not validated, and update tooling should support read-only version checks before executing package updaters.

## What Changes

- Document the canonical artifact mapping: Superpowers provides process discipline and review gates; OpenSpec, GSD, and DevFlow planning files remain the canonical artifacts.
- Update DevFlow skills and generated `AGENTS.md` guidance so Superpowers outputs are treated as drafts/input unless copied into canonical OpenSpec/GSD/DevFlow artifacts.
- Add dependency coverage for `gsd-progress`, which `workflow-doctor` already routes to.
- Add a refresh path for project-local symlinked skills whose provider source changed.
- Add read-only dependency update checks for GSD and OpenSpec, while keeping update/apply behavior explicit.
- Replace hard-coded Python executable guidance in context-tool audit docs with portable `python3` commands.

## Capabilities

### New Capabilities
- `devflow-dependency-workflow`: DevFlow's rules for integrating external workflow tools, validating required dependencies, refreshing project-local skill links, and checking external updater state.

### Modified Capabilities
- `devflow-plugin-quality`: DevFlow quality checks now include dependency workflow guidance, project-local skill refresh behavior, and portable audit commands.

## Impact

- Affected files:
  - `dev/plugins/dev-flow/assets/templates/AGENTS.md.template`
  - `dev/plugins/dev-flow/skills/*/SKILL.md`
  - `dev/plugins/dev-flow/scripts/workflow_dependency_catalog.py`
  - `dev/plugins/dev-flow/scripts/workflow_project_skill_install.py`
  - `dev/plugins/dev-flow/scripts/codex_auto_update_plugins_skills.py`
  - focused DevFlow tests and release-copy files under `plugins/dev-flow/`
- No production dependencies are added.
- No public plugin id, hook schema, or OpenSpec/GSD command names change.
