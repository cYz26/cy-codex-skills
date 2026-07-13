# OpenSpec 1.6 DevFlow Upgrade Evidence

## RED contract — 2026-07-13

Command:

```bash
python3.12 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_openspec_1_6.py' -v
```

Result: expected failure; 10 tests ran with 7 assertion failures and 5 errors.

The failures proved the pre-change implementation:

- still pinned OpenSpec 1.5.0 and exposed only five workflows;
- had no Node `>=20.19.0` runtime gate;
- preferred stale global skill metadata over the installed CLI version;
- used unpinned `npm update -g` for apply updates;
- invoked `openspec init` against the real project with no isolated XDG or
  Codex home;
- invoked the command during the tested dry-run path;
- did not validate exact generated skill set/version;
- linked generated sources rather than copying ephemeral staging content;
- had no batch custom-target conflict or transactional rollback contract; and
- did not clean a failed generation target because no staging boundary existed.

These are contract failures, not incidental fixture failures. Production code
was unchanged when this RED run was recorded.

## GREEN and release evidence — 2026-07-13

### Official release contract

- Audited the official `v1.6.0` tag at
  `e1b51d111ab446b54dee2d6159ac245f0339ae52`, its npm package/tarball, CLI
  help, generated Codex artifacts, and post-tag `main`. Post-tag changes were
  release/website-only, so DevFlow pins the released `1.6.0` instead of main.
- `src/core/profiles.ts` is the authoritative released workflow source and
  defines `core` as `propose`, `explore`, `apply`, `update`, `sync`, and
  `archive`. The release's `docs/supported-tools.md` still lists the old
  five-item core set, but its generated-skill list includes
  `openspec-update-change`; real `openspec init --profile core` also generated
  all six. DevFlow therefore follows source plus real CLI output, not the stale
  prose list.
- `package.json` requires Node `>=20.19.0`. Generated skills carry
  `generatedBy: "1.6.0"` and `allowed-tools: Bash(openspec:*)`.

### Source implementation and tests

- OpenSpec 1.6 integration suite: 11/11 passed, including dependency/runtime,
  write-free dry-run, isolated generation, exact-set/version rejection,
  command/setup failure cleanup, regular-copy survival, custom batch conflict,
  transactional rollback, and pinned updater coverage.
- Provider profile suite: 63/63 passed. Provider guidance suite: 9/9 passed.
- Final complete development discovery:
  `PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest discover -s dev/plugins/dev-flow/tests`
  ran 450 tests in 62.298 seconds; all passed.
- `git diff --check` passed. Strict
  `openspec validate upgrade-devflow-openspec-1-6 --strict --no-interactive`
  passed.

### Release package

- `release_promotion_gate.py --apply --json` synchronized the DevFlow release;
  the immediate `--check --json` returned `status: current` with no changed,
  missing, deleted, or stale output.
- Packaged discovery ran 8 tests; all passed.
- Runtime archive verification passed 277 checks with no failures. Archive
  SHA-256:
  `efc0c73755e2630864506ce26e76f9076cc421d5553a25481597a1b400047b48`.
- Release-target Plugin Eval scored 86/B, medium risk, with 0 failures, 3
  static token-budget warnings, and 2 informational findings. The warnings are
  unchanged plugin-wide debt: 385 trigger, 11,996 invoke, and 27,397 deferred
  estimated tokens. They are deferred because restructuring all 16 skills is
  outside this OpenSpec integration change and needs measured-usage plus
  behavior review; residual risk is static instruction cost, with a follow-up
  path through the existing token/outcome benchmark plan.

### Real OpenSpec 1.6 and local rollout

- The pinned command `npm install -g @fission-ai/openspec@1.6.0` changed the
  machine CLI from `1.5.0` to `1.6.0`; Node is `24.13.0`, satisfying
  `>=20.19.0`.
- Real isolated activation returned `generation.status: verified` for exactly
  six skills and initially returned `openspec_transaction.status: applied`.
  Every target is a regular copied directory under `.agents/skills`, not a
  staging symlink, and every `SKILL.md` reports `generatedBy: "1.6.0"`.
- A second activation through the refreshed installed DevFlow cache returned
  `openspec_transaction.status: current`, `changed: false`, with all six skills
  `already-present`. The real OpenSpec config hash stayed
  `1cfa273ff52c007ed07478ebfd47942ce005324b08776b8c00b16a6e5271cb5b`
  before and after. The global OPSX prompt count stayed zero and its aggregate
  empty-set hash stayed
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- `dev-flow@cy-codex-skills` was refreshed using the actual ChatGPT App Codex
  binary. Installed-cache and release runtime hashes both equal the archive
  hash above, and updater diagnostics report `matches-source`.
- Repository-local DevFlow links were restored to the canonical
  `dev/plugins/dev-flow/skills` source after the installed-cache smoke. Final
  migration inspection reports control plane `current`, skill layout
  `current`, and no missing or stale project skills.

### Diagnostics and remaining boundaries

- Workflow validation passed with no issues or warnings; doctor/cache-drift
  diagnosis is `healthy` with no repair recommendation. Dependency diagnosis
  verifies OpenSpec `1.6.0`, Node `24.13.0`, and the project-local update/sync
  workflows.
- `plugin_project_migration.py` intentionally returns `blocked` only because
  provider migration cannot run while active change
  `upgrade-devflow-openspec-1-6` exists. No provider migration is requested by
  this change; its plugin control plane and skill layout are current with no
  stale or missing skills. The block is preserved rather than bypassed.
- Scaffold remained dry-run-only. `AGENTS.md.generated` is merge-only; durable
  OpenSpec 1.6 routing was already merged into active `AGENTS.md` without
  replacing project-specific guidance. Legacy `.codex/skills` cleanup was not
  requested or performed.
- The PATH `codex` shim is independently stale: the active `codex-switch`
  official profile points to missing `/Applications/Codex.app/Contents/Resources/codex`.
  Refresh used the existing `/Applications/ChatGPT.app/Contents/Resources/codex`
  (`0.144.0-alpha.4`) directly. Rebinding that machine profile is outside this
  change and remains an operational follow-up.
- OpenSpec archive remains unperformed. Repository submission and the fresh
  local refresh were separately authorized after this initial evidence; their
  result is recorded below.

## Remote-main submission gate — 2026-07-13

The user separately authorized direct submission to remote `main` and a fresh
local DevFlow/project refresh. Archive remains outside this authorization.

- `PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest discover -s dev/plugins/dev-flow/tests`
  passed 450 tests in 62.515 seconds.
- `PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest discover -s plugins/dev-flow/tests`
  passed 8 tests.
- `openspec validate upgrade-devflow-openspec-1-6 --strict --no-interactive`
  passed under OpenSpec 1.6.0.
- Release promotion dry-run remained `current`; runtime verification passed all
  277 checks with archive SHA-256
  `efc0c73755e2630864506ce26e76f9076cc421d5553a25481597a1b400047b48`.
- Release-target Plugin Eval remained 86/B with 0 failures, 3 previously
  recorded static token-budget warnings, and 2 informational findings.
- `git diff --check` passed, and a fresh `git fetch origin main` confirmed the
  branch base and `origin/main` had no commit divergence before submission.

## Submission and refresh result — 2026-07-13

- Commit `b44f01a` (`feat(devflow): upgrade OpenSpec integration to 1.6`) was
  pushed as a fast-forward directly to `origin/main`. Local `main` was then
  fast-forwarded and verified at the same commit.
- `/Applications/ChatGPT.app/Contents/Resources/codex plugin add
  dev-flow@cy-codex-skills --json` refreshed the named cache successfully. The
  installed runtime and release runtime SHA-256 values both equal
  `efc0c73755e2630864506ce26e76f9076cc421d5553a25481597a1b400047b48`.
- Project refresh dry-run was write-free. Apply generated the exact six skills
  through the isolated OpenSpec 1.6 path and reported the transaction
  `current`, with all six targets `already-present` as regular directories.
- Every local OpenSpec skill reports `generatedBy: "1.6.0"` and
  `allowed-tools: Bash(openspec:*)`. DevFlow project links still resolve to the
  repository source tree.
- The global OpenSpec config SHA-256 remained
  `1cfa273ff52c007ed07478ebfd47942ce005324b08776b8c00b16a6e5271cb5b` and
  the global OPSX prompt count remained zero.
- Final workflow validation and cache doctor passed. Project control plane and
  skill layout remain current, `AGENTS.md.generated` is absent, and the only
  migration status is the expected protective block for the active verified
  change and phase.
- The PATH `codex` shim still targets the missing legacy Codex App binary. The
  refresh used the available ChatGPT App binary directly; changing the
  independent `codex-switch` profile remains out of scope.
- The refreshed session exposed a separate stale AgentKB hook/cache race. A
  temporary targeted refresh restored the missing hook long enough to finish
  diagnostics, but the user confirmed AgentKB had intentionally been
  uninstalled in the Plugins manager. Final local state was therefore restored
  with a targeted AgentKB removal; no repository file or marketplace-wide
  update was involved.
