## Why

This repository already separates development assets under `dev/` from release
assets used by marketplaces and installs. Promotion is currently documented as a
manual copy step, and individual plugins can drift after development validation.
Plugin Eval guidance also lets agents evaluate the development tree even when a
release package exists, which makes quality signals noisy and can hide release
packaging issues.

DevFlow needs a deterministic release-promotion gate so plugin and skill work
automatically moves from development sources to release sources at the right
workflow boundary, then evaluates the release package as the primary quality
target.

## What Changes

- Add a repository-aware `sync_release_assets.py` CLI for dev-to-release asset
  discovery, dry-run drift checks, explicit apply, and release eval target
  resolution.
- Add a `release_promotion_gate.py` hook entrypoint that triggers at verified
  workflow boundaries. When verification has passed and dev assets are ahead of
  release assets, it applies release sync and asks for release validation.
- Add release sync metadata for DevFlow so its release copy uses the packaged
  runtime archive instead of a raw `scripts/` copy.
- Update release-isolation and AGENTS template guidance so Plugin Eval targets
  release plugin/skill paths by default, with dev-path eval reserved for
  diagnostics.
- Keep sync deterministic and allowlist-based: runtime files are promoted,
  while logs, fixtures, local reports, and scratch output remain in `dev/`.

## Capabilities

### New Capabilities

- `release-promotion-gate`: repository-local promotion detection, apply, and
  release evaluation target selection for plugins and skills.

### Modified Capabilities

- `devflow-plugin-quality`: Plugin Eval primary target becomes the release
  asset when a release counterpart exists.
- `devflow-plugin-identity`: DevFlow hooks include the release promotion gate.

## Impact

- Affected files:
  - `dev/plugins/dev-flow/scripts/sync_release_assets.py`
  - `dev/plugins/dev-flow/scripts/release_promotion_gate.py`
  - `dev/plugins/dev-flow/scripts/workflow_release_sync.py`
  - `dev/plugins/dev-flow/.codex-plugin/release-sync.json`
  - `dev/plugins/dev-flow/hooks.json`
  - `dev/plugins/dev-flow/assets/templates/AGENTS.md.template`
  - `docs/release-isolation.md`
  - release mirror files under `plugins/dev-flow/`
  - tests under `dev/plugins/dev-flow/tests`
- No production dependency is added.
- Automatic sync runs only at verification/stop boundaries, not on every edit.
- Existing dev/release directories without a dev counterpart are ignored.
