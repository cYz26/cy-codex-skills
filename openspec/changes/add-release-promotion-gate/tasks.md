# Tasks: Release Promotion Gate

## Target State

DevFlow automatically promotes changed dev plugin/skill assets to release
counterparts at verified workflow boundaries, and Plugin Eval defaults to the
release asset when one exists.

## Completion Contract

- [x] Add tests for dev plugin and standalone skill release target discovery.
- [x] Add tests for dry-run drift detection and explicit apply.
- [x] Add tests for DevFlow's packaged runtime build metadata.
- [x] Add tests for hook timing: no action before verification, sync after
  verification passed.
- [x] Add tests proving Plugin Eval target resolution prefers release paths.
- [x] Implement release sync engine and CLI.
- [x] Add DevFlow release sync metadata.
- [x] Add release promotion hook and hook registration.
- [x] Update docs and AGENTS template with release-first Plugin Eval guidance.
- [x] Regenerate DevFlow release runtime archive.
- [x] Run focused tests, DevFlow dev/release tests, OpenSpec validation, and
  Plugin Eval on the release package.

## Execution Ledger

| Slice | Status | Evidence |
|---|---|---|
| Contract and tests | done | `python3 -m unittest dev/plugins/dev-flow/tests/test_release_sync.py` |
| Sync engine and CLI | done | `sync_release_assets.py --json`, `--apply --json`, `--eval-target dev/plugins/dev-flow --json` |
| Gate and guidance | done | DevFlow Stop hook order test and release mirror sync |
| Final verification | done | `.planning/verification/20260602121017-add-release-promotion-gate.md` |
