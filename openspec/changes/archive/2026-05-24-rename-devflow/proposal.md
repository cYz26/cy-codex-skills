## Why

The plugin's current `Codex Project Orchestrator` name no longer matches its broader role as a plan-first workflow kit for Codex development. Renaming it to `DevFlow` captures both the `Development Workflow` abbreviation and the goal of helping developers find flow while moving through setup, planning, verification, checkpoint, and context-tool governance.

## What Changes

- Rename the plugin identity from `codex-project-orchestrator` to `dev-flow`.
- Rename the user-facing display name to `DevFlow`.
- Update marketplace registration, release/dev plugin paths, README references, preflight checks, tests, and warning labels.
- Keep existing skill names such as `project-orchestrator` unchanged for compatibility with project-local workflow routing.
- Support the new hook config file `.dev-flow.json` while preserving `.codex-project-orchestrator.json` as a legacy fallback.
- **BREAKING**: Marketplace install references should use `dev-flow` after this change.

## Capabilities

### New Capabilities

- `devflow-plugin-identity`: Covers the plugin's canonical package id, display name, marketplace registration, repository paths, hook labels, and compatibility expectations.

### Modified Capabilities

- `current-system`: The repository's current-system description gains the plugin identity expectation.

## Impact

- Affects plugin manifests under `dev/plugins/` and `plugins/`.
- Affects `.agents/plugins/marketplace*.json` entries and repository README plugin lists.
- Affects package/preflight tests, dependency fixtures, hook tests, and warning strings.
- Affects docs and verification command examples that reference the old plugin path.
- Does not add production dependencies or rename the existing project-local skill protocol.
