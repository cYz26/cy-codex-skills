# Baseline evidence

Date: 2026-08-08 Asia/Shanghai

## Characterization

All pre-edit suites passed:

| Surface | Tests | Result |
| --- | ---: | --- |
| Continuous execution | 12 | PASS |
| Runtime gates | 35 | PASS |
| Generated Artifact Lifecycle | 60 | PASS |
| Git transport preflight | 9 | PASS |
| Release sync | 45 | PASS |
| Project refresh | 62 | PASS |
| Methodology routing | 33 | PASS |
| Implementation readiness | 26 | PASS |
| Total | 282 | PASS |

Commands used `PYTHONDONTWRITEBYTECODE=1 python3.12` on each corresponding source test file. State validation and doctor both returned healthy with zero issues after activating the change.

## Repository and remote

- Worktree HEAD: `f8f42cd208a6b15ab415025f6fd62f003178d77e`
- Worktree tree: `7783850e5d3b7ea02ed178a5652fd874302e29fc`
- Remote: `git@github.com:cYz26/cy-codex-skills.git`
- Remote `refs/heads/main`: `f8f42cd208a6b15ab415025f6fd62f003178d77e`
- Remote `refs/tags/dev-flow-v0.4.0`: absent at baseline
- Worktree state: detached; only the planned tracked state edit was visible before production changes

## Plugin, marketplace, cache, and refresh

- Development plugin: `dev-flow` `0.3.0+codex.20260529145038`
- Generated release plugin: `dev-flow` `0.3.0+codex.20260529145038`
- Development tree digest: `a8e7d900952d2fa050c60f308c1c125f8f6da1244e16d586869c76b896e909c9`
- Release tree digest: `bc774be7dee104603bca61831f1c797084c70d6b1d539d72f113ff030fb72c80`
- Release marketplace: `cy-codex-skills` local source `./plugins/dev-flow`
- Development marketplace: `cy-codex-skills-dev` local source `./dev/plugins/dev-flow`
- Installed named cache: `/Users/cy/.codex/plugins/cache/cy-codex-skills/dev-flow/0.3.0+codex.20260529145038`
- Read-only updater classified that cache as `matches-source`, with project refresh revision 9, schema head 8, and matching source/release/cache refresh identity.
- The broad updater also listed many unrelated would-refresh targets, confirming it cannot be used as the milestone writer.

## Runtime provenance limitation

- Runtime archive: `ce7fcbf7b36e85d632b0e634e4042d778006f3be633cc408b9a1c0939ebc64a4`
- Runtime manifest: `cf2ff81059185e5950cd96fb5bc06fd18c90b698616291863e536fdce445e177`
- Runtime checksum file: `eaa7f1124df64ab25a24e192a11ad9b8d0da9abf104488c41cdc2f2b06a5b062`
- Manifest source count: 137
- Legacy `sourceCommit`: `132efed1a4932d3aa294a823eabcabd1441d0d22`
- Recorded build executable: `/Users/cy/.homebrew/opt/python@3.12/bin/python3.12`

The manifest's source hashes match shipped bytes, but the commit provenance is an older base and the command contains a workstation-specific absolute path. The new release must bind reviewed source-tree/file digests and normalized logical build arguments; it must not attempt an impossible self-reference to the containing commit.

## Named source project observation

The named source checkout remained at the baseline commit, but a fresh read showed unrelated uncommitted changes in `.planning/devflow/STATE.md` and `TASK_LEDGER.md`. This task did not create or modify those source-checkout bytes. Final project refresh must preserve them, must not reset/stash/overwrite them, and must route an active owner to `WAIT_OWNER` rather than Human Gate. The worktree implementation can continue independently.
