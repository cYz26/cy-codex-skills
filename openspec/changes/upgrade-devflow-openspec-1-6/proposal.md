## Why

DevFlow pins OpenSpec `1.5.0` and assumes `openspec init --tools codex`
deterministically creates five project-local `openspec-*` skills. OpenSpec
`1.6.0` is now the published npm `latest`, adds a sixth core `update` workflow,
and derives skill/command delivery from user-global configuration; with
`delivery: commands`, the current DevFlow activation writes global Codex
prompts and leaves the required project skill sources absent.

## What Changes

- Pin the supported OpenSpec CLI and updater contract to released version
  `1.6.0`, including its Node `>=20.19.0` runtime requirement.
- Generate the six official core OpenSpec skills in an isolated staging
  environment, then materialize verified copies under project-local
  `.agents/skills/` without changing the user's global OpenSpec profile,
  delivery mode, or `$CODEX_HOME/prompts`.
- Add `openspec-update-change` to DevFlow routing, diagnostics, migration, and
  refresh behavior.
- Align DevFlow guidance with OpenSpec 1.6 status/instructions/action-context,
  validation, and archive exit-code contracts while keeping DevFlow/OpenSpec
  artifacts as the canonical source of truth.
- Add regression coverage for global-side-effect isolation, generated-version
  verification, six-workflow completeness, refresh, drift, and failure paths.

## Capabilities

### New Capabilities

- `devflow-openspec-integration`: Version-pinned, deterministic, project-local
  integration of the released OpenSpec CLI and its core Codex skills.

### Modified Capabilities

- None.

## Impact

- Affected dependency policy: `dev/plugins/dev-flow/docs/dependency-provenance.json`.
- Affected runtime: dependency diagnostics/updater, project activation and
  skill materialization, migration catalogs, routing guidance, and release
  packaging.
- Affected project layout: `.agents/skills/openspec-*` gains
  `openspec-update-change`; generated legacy `.codex/skills` and global OPSX
  prompts are no longer prerequisites or activation targets.
- Upstream evidence: [OpenSpec v1.6.0 source](https://github.com/Fission-AI/OpenSpec/tree/v1.6.0),
  [1.6.0 changelog](https://github.com/Fission-AI/OpenSpec/blob/v1.6.0/CHANGELOG.md),
  and [supported-tool delivery contract](https://github.com/Fission-AI/OpenSpec/blob/v1.6.0/docs/supported-tools.md).
