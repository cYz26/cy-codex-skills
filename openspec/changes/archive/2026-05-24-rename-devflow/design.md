## Context

The repository currently publishes the workflow plugin from `dev/plugins/codex-project-orchestrator` and `plugins/codex-project-orchestrator`. Its manifest name, marketplace entries, documentation, warning labels, and package preflight checks all use the old `codex-project-orchestrator` identity. The plugin's feature set has expanded into Codex-first workflow setup, AI-native technical planning, OpenSpec/GSD/Superpowers routing, verification gates, checkpoints, and context-tool audit.

## Goals / Non-Goals

**Goals:**

- Make `DevFlow` the user-facing plugin name.
- Make `dev-flow` the canonical plugin id and marketplace name.
- Rename dev and release plugin folders so marketplace paths match the new id.
- Keep existing project-local skill names and routing behavior stable.
- Preserve support for existing `.codex-project-orchestrator.json` hook config while documenting `.dev-flow.json` as the preferred file.
- Update tests and preflight checks so packaging fails if old identity leaks back into canonical surfaces.

**Non-Goals:**

- Do not rename the `project-orchestrator` skill or dependent project-local skill checks.
- Do not rewrite workflow scripts beyond identity strings and config-file lookup.
- Do not archive older OpenSpec history or rewrite verification evidence from previous changes.
- Do not add dependencies.

## Decisions

1. Use `DevFlow` for display names and `dev-flow` for machine ids.
   - Rationale: plugin manifests and marketplace names already use kebab-case ids, while the requested name is PascalCase and better suited to UI text.
   - Alternative considered: use `DevFlow` everywhere. That would be inconsistent with existing plugin id conventions and harder to use in CLI/install references.

2. Rename plugin directories to `dev-flow`.
   - Rationale: keeping old directory names after changing manifest and marketplace names would preserve ambiguity and make docs/tests less direct.
   - Alternative considered: only change `interface.displayName`. That is lower risk but would not satisfy a full plugin rename.

3. Keep skill names unchanged.
   - Rationale: `project-orchestrator`, `feature-intake`, and related skills are workflow protocol names. Renaming them would force a larger migration across dependency activation and existing repo-local installs.
   - Alternative considered: rename all skills to match `DevFlow`. That expands blast radius without improving the plugin identity.

4. Support both new and legacy hook config filenames.
   - Rationale: users may already have `.codex-project-orchestrator.json` in target repos. Reading it as a fallback avoids breaking hook mode configuration.
   - Alternative considered: hard switch to `.dev-flow.json`. That would be cleaner but unnecessarily breaking.

## Risks / Trade-offs

- Marketplace references using `codex-project-orchestrator` will stop matching the canonical plugin name. Mitigation: update local marketplace catalogs and docs, and keep project-local skill names stable.
- Existing generated verification docs will still mention old paths. Mitigation: do not rewrite historical evidence; update current docs and command references only.
- Directory rename can obscure unrelated dirty changes in the diff. Mitigation: move the directories in place and avoid reverting existing modified content.
