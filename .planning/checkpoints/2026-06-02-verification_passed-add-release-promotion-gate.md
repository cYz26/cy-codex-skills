# Checkpoint: Release Promotion Gate Verified

created_at: 2026-06-02T12:10:17+08:00

## Current State

The `add-release-promotion-gate` OpenSpec change is implemented and verified.
DevFlow now has a release sync engine, explicit sync CLI, Stop-hook promotion
gate, DevFlow packaging metadata, release-first Plugin Eval target resolution,
and updated guidance.

## Changed Areas

- `dev/plugins/dev-flow/scripts/workflow_release_sync.py`
- `dev/plugins/dev-flow/scripts/sync_release_assets.py`
- `dev/plugins/dev-flow/scripts/release_promotion_gate.py`
- `dev/plugins/dev-flow/.codex-plugin/release-sync.json`
- `dev/plugins/dev-flow/hooks.json`
- `plugins/dev-flow/` release mirror and generated runtime archive
- `docs/release-isolation.md`
- `dev/plugins/README.md`
- `dev/skills/README.md`
- `dev/plugins/dev-flow/assets/templates/AGENTS.md.template`
- `openspec/changes/add-release-promotion-gate/`
- `dev/plugins/dev-flow/tests/test_release_sync.py`

## Verification

See `.planning/verification/20260602121017-add-release-promotion-gate.md`.

## Next Action

Review the staged diff and commit the combined release runtime packaging plus
release promotion gate work. OpenSpec archive remains a separate post-commit
step.
