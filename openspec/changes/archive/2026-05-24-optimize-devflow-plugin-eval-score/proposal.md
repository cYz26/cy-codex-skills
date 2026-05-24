## Why

Plugin Eval currently rates the DevFlow release package as high risk because the package has too many default prompts, heavy static token budgets, a monolithic context-tool helper module, long Python lines, and no release-package test signal. These findings make the plugin look more expensive and harder to maintain than its workflow value justifies.

## What Changes

- Trim DevFlow's visible starter prompts to the Codex-supported limit of three.
- Tighten high-cost skill trigger descriptions while preserving routing intent.
- Split the context-tool audit/apply implementation into focused modules with a stable compatibility facade.
- Add release-package smoke tests that exercise manifest and context-tool behavior without copying the full development test suite.
- Remove Python long-line warnings in the optimized areas.
- Re-run Plugin Eval for both release and development plugin roots after implementation and record the results.
- No production dependencies are added.

## Capabilities

### New Capabilities

- `devflow-plugin-quality`: Covers Plugin Eval quality expectations for DevFlow manifests, skill metadata, context-tool implementation structure, release-package test signal, and evaluation evidence.

### Modified Capabilities

- None.

## Impact

- Affects DevFlow plugin manifests under `plugins/dev-flow` and `dev/plugins/dev-flow`.
- Affects selected DevFlow skill metadata in `skills/*/SKILL.md`.
- Affects context-tool Python modules under `scripts/` for both dev and release plugin roots.
- Adds compact release-package tests under `plugins/dev-flow/tests/`.
- Adds development tests or updates existing tests under `dev/plugins/dev-flow/tests/`.
- Affects OpenSpec and planning evidence only for this change.
