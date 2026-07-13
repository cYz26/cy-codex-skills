# Task Ledger

## Active Change: OpenSpec 1.6 Integration

### Goal Contract

- goal_id: openspec:upgrade-devflow-openspec-1-6 (no active Codex goal)
- objective: Upgrade DevFlow to the released OpenSpec 1.6.0 contract with six
  deterministic project-local Codex skills, pinned dependency updates, and no
  writes to user-global OpenSpec or Codex prompt configuration.
- scope_in: `dev/plugins/dev-flow`, generated release assets, OpenSpec change
  evidence, current-project DevFlow/OpenSpec refresh, and control-plane docs.
- scope_out: unreleased OpenSpec main, stores/custom-schema adoption, global
  OPSX prompt enablement, unrelated dependency/provider updates, and archive.
- acceptance_criteria: OpenSpec 1.6.0 and Node >=20.19 are enforced; isolated
  generation verifies and copies exactly six official skills; dry-run is
  write-free; custom targets survive; source/package/runtime/cache/project
  verification passes; no real global OPSX prompt is created.
- validation_commands: focused and complete DevFlow unittest discovery,
  strict OpenSpec 1.6 validation, release promotion dry-run/apply/current,
  packaged/runtime verification, release-target Plugin Eval, cache drift,
  project migration/workflow/scaffold diagnostics, and `git diff --check`.
- knowledge_update_target: none

### Tasks

| task_id | summary | owner | write_set | contract_path | required_evidence | review_gate | status |
|---|---|---|---|---|---|---|---|
| DF-OS-1 | Official 1.6 source/package/CLI research and canonical change | main | `openspec/changes/upgrade-devflow-openspec-1-6/**` | not-delegated | tag/package/generated-skill/global-delivery reproduction | strict OpenSpec validation | done |
| DF-OS-2 | RED dependency, isolation, copy, refresh, failure, and cleanup contracts | main | DevFlow tests and change evidence | not-delegated | focused failing test output | test-first review | done |
| DF-OS-3 | Isolated six-skill integration, routing, updater, diagnostics, and guidance | main | `dev/plugins/dev-flow/**`, control-plane guidance | not-delegated | focused GREEN tests and global-path invariants | spec review | done |
| DF-OS-4 | Release synchronization and packaged/runtime verification | main | generated `plugins/dev-flow/**` | not-delegated | release current, packaged/runtime tests, Plugin Eval | release gate | done |
| DF-OS-5 | Pinned CLI, named plugin cache, and current-project refresh | main | local CLI/cache and project `.agents/skills` | not-delegated | version/cache/project diagnostics | named upgrade request | done |
| DF-OS-6 | Final evidence and control-plane closeout | main | change tasks/evidence, ledger, local state | not-delegated | exact commands/results/risks and clean global prompt check | no archive without approval | done |

### Execution Log

- 2026-07-13: Audited official OpenSpec `v1.5.0`, released `v1.6.0`, npm
  package metadata/tarball, generated Codex skills, CLI help, and post-tag
  `main`; selected released `1.6.0` and Node `>=20.19.0`.
- 2026-07-13: Reproduced that real `delivery: commands` overrides the current
  DevFlow `--profile core` init assumption, then proved isolated
  `XDG_CONFIG_HOME` and `CODEX_HOME` generate the six 1.6 skills without global
  writes. Strict validation of the canonical change passed.
- 2026-07-13: RED ran 10 tests with 7 failures and 5 errors; the completed
  isolated implementation then passed 10/10 plus provider profile 63/63 and
  guidance 9/9. Full development discovery passed 448 source tests; its only
  expected failure was stale packaged preflight awaiting release sync.
- 2026-07-13: Installed pinned OpenSpec 1.6.0 on Node 24.13.0. A real isolated
  activation verified and copied six skills while preserving byte-identical
  global OpenSpec configuration and OPSX prompt snapshots.
- 2026-07-13: Added a final regression for staging-directory setup failure;
  the focused OpenSpec 1.6 suite passed 11 tests and complete development
  discovery passed 450 tests in 62.298 seconds.
- 2026-07-13: Release promotion synchronized the packaged runtime and the
  immediate recheck returned `current`. Packaged discovery passed 8 tests;
  runtime verification passed 277 checks with archive SHA-256
  `efc0c73755e2630864506ce26e76f9076cc421d5553a25481597a1b400047b48`.
- 2026-07-13: Release-target Plugin Eval remained 86/B with 0 failures and the
  same three plugin-wide static token-budget warnings. Broader 16-skill token
  restructuring is deferred to measured usage/outcome work outside this
  OpenSpec integration change.
- 2026-07-13: Refreshed the named DevFlow cache and proved its runtime hash
  matches release. Current-project activation generated and copied six 1.6.0
  OpenSpec skills, then an installed-cache rerun was idempotent (`current`, no
  writes). Global OpenSpec config hash stayed identical and global OPSX prompt
  count remained zero.
- 2026-07-13: Final workflow validation and doctor passed; project control
  plane/skill layout are current with no stale or missing skills. Provider
  migration remains correctly blocked by the active OpenSpec change and was
  not bypassed. Archive remains unperformed.
- 2026-07-13: User separately authorized direct submission to remote `main`
  and a fresh local DevFlow/project refresh. The submission gate reran 450
  source tests, 8 packaged tests, strict OpenSpec validation, 277 runtime
  checks, release-current validation, `git diff --check`, and release-target
  Plugin Eval (86/B, 0 failures); all blocking checks passed.
- 2026-07-13: Commit `b44f01a` (`feat(devflow): upgrade OpenSpec integration
  to 1.6`) was pushed directly to `origin/main`; local `main` was
  fast-forwarded and verified aligned with the remote.
- 2026-07-13: Refreshed `dev-flow@cy-codex-skills` with the available ChatGPT
  App Codex binary. Installed-cache and release runtime SHA-256 values both
  equal `efc0c73755e2630864506ce26e76f9076cc421d5553a25481597a1b400047b48`.
  Project activation verified all six OpenSpec 1.6.0 skills as current regular
  directories; workflow validation and doctor passed, `AGENTS.md.generated`
  is absent, global OpenSpec config remained byte-identical, and no global
  OPSX prompt was created. Provider migration remains intentionally blocked by
  the still-active verified change and phase; no migration or cleanup was
  bypassed.

## Previous Completed Change: Provider Architecture

## Goal Contract

- goal_id: openspec:optimize-devflow-provider-architecture (no active Codex goal)
- objective: Implement the approved DevFlow provider architecture with an
  independent core, optional methodology/roadmap providers, namespaced state,
  reversible migration, and measured default-switch gates.
- scope_in: `dev/plugins/dev-flow`, DevFlow control-plane guidance, release
  sync/runtime verification plumbing, OpenSpec evidence, and isolated tests.
- scope_out: third-party provider installation, broad real-project migration,
  global methodology-plugin or Matt-pack disable/removal, provider-cache
  deletion, archive, and paid/live benchmark execution. Repository release
  sync, named DevFlow cache refresh, explicit `core + none` persistence,
  digest-bound verified legacy-link cleanup, commit, and push are authorized by
  the user's continuation and optimization requests.
- acceptance_criteria: Source tests and OpenSpec validation pass; `core + none`
  has no universal Superpowers, Matt, or GSD dependency; stable routing and
  ledger output uses capability ids; unselected providers are action-free;
  Matt activation is project-local; cleanup is digest-authorized,
  transactional, dry-run-first, and reversible; release/runtime/cache parity
  is fresh; default remains core until the benchmark and human gates pass.
- validation_commands: DevFlow unittest discovery, strict OpenSpec validation,
  provider benchmark dry-run, release-promotion gate and post-sync dry-run,
  packaged discovery/runtime verification, release-target Plugin Eval, named
  installed-cache refresh, project diagnostics, digest-bound cleanup plus
  idempotence check, updater/cache-drift checks, and `git diff --check`.
- knowledge_update_target: none

## Tasks

Use `contract_path` for delegated agent, subagent, worker, or parallel
execution. Use `not-delegated` for ordinary main-agent tasks.

| task_id | summary | owner | write_set | contract_path | required_evidence | review_gate | status |
|---|---|---|---|---|---|---|---|
| DF-PA-1 | Provider registry, adapters, and scoped readiness | main | `dev/plugins/dev-flow/docs/**`, provider/dependency scripts and tests | not-delegated | profile matrix and source/hash tests | standards + spec review | done |
| DF-PA-2 | Roadmap ownership, namespaced state, migration, and rollback | main + agents | planning/roadmap/migration scripts and tests | `.planning/agent-tasks/20260710-devflow-provider-implementation-research.md` | ownership, apply failure, idempotence, rollback, GSD binding tests | standards + spec review | done |
| DF-PA-3 | Provider-neutral routing and context cleanup | main | active skills, templates, routing matrix | not-delegated | static guidance tests and Plugin Eval diagnostic | release-target Eval | done |
| DF-PA-4 | Strict-vs-lean benchmark framework | provider_benchmark_impl | `dev/plugins/dev-flow/evals/provider-profiles/**`, benchmark scripts/tests | `.planning/agent-tasks/20260710-devflow-provider-implementation-research.md` | 10-task/3-repeat dry-run and threshold tests | live run requires user approval | done |
| DF-PA-5 | Live benchmark and default decision | unassigned | raw/model evidence only | not-delegated | 60-run dry-run complete; live paired evidence belongs to a later default-switch change | explicit spend + blind review | skipped_with_reason |
| DF-PA-6 | Release sync and packaged runtime | main | generated `plugins/dev-flow/**` | not-delegated | post-sync current, packaged 3x2 smoke, runtime verification, release Eval | repository release/commit/push authorized | done |
| DF-PA-7 | Installed cache and real-project refresh | main | local runtime/project state | not-delegated | cache matches release; migration and skill layout current | explicit apply authorized by continuation request | done |
| DF-PA-8 | Provider-neutral gates and durable routing ledgers | provider_neutral | decision matrix/runtime, plan linter, AGENTS/task-ledger templates, focused routing tests | `.planning/agent-tasks/20260713-devflow-provider-hardening.md` | RED/GREEN provider-neutral gate and generated-template tests | independent review | done |
| DF-PA-9 | Unselected diagnostics and verified-link deactivation | provider_diagnostics + main | dependency summaries, activation cleanup path, dependency tests | `.planning/agent-tasks/20260713-devflow-provider-hardening.md` | action-free summary plus digest/persistence/dirfd/rollback/preservation/idempotence tests | independent safety review | done |
| DF-PA-10 | Matt project locality and current strict compatibility | matt_local_version + main | Matt resolution/provenance/install, Superpowers metadata, profile/runtime tests | `.planning/agent-tasks/20260713-devflow-provider-hardening.md` | project-local lock/unique-source allowlist and 6.1.1 manifest/version tests | independent provider-boundary review | done |
| DF-PA-11 | Release, local refresh, evidence, and remote submission | main | generated release, local DevFlow/project provider state, evidence/status | not-delegated | 438 dev, 8 packaged, 277 runtime, OpenSpec/Eval/cache-drift evidence | independent final review | done |

Agent Task Contract template: `AGENT_TASK_CONTRACT.md`.

## Execution Log

- 2026-07-10: Source architecture implemented with TDD and cross-agent review.
- 2026-07-10: Live dependency, migration, release, refresh, and benchmark apply
  actions intentionally not executed; their separate approval gates remain.
- 2026-07-10: Final independent standards/spec/trust reviews found and closed
  provider route-hash, config fail-open, migration readiness/TOCTOU, release
  authorization/target-drift, and benchmark raw-evidence integrity gaps.
- 2026-07-10: Focused verification passed for provider/dependency (196),
  roadmap/migration (111), routing/guidance (67), and benchmark (27) tests.
  Release sync remains pending and all real apply gates remain closed.
- 2026-07-10: Release diagnostics were hardened to a packager-complete static
  output list; dynamic managed-output commands are rejected without execution.
  Benchmark inputs are now frozen and rechecked around every model call, with
  whole-run invalidation on drift. Independent delta review found no P0/P1/P2.
- 2026-07-10: Fresh focused release/benchmark verification passed 53 tests in
  15.892 seconds. Final complete DevFlow development suite passed 388 tests in
  58.785 seconds with no failures or skips.
- 2026-07-13: User authorized continuing the repository release and remote
  submission. Release promotion synchronized the compact packaged test and
  template, removed the stale generated bytecode file, and the second dry-run
  reported `current` with no changed, missing, deleted, or stale output.
- 2026-07-13: Packaged runtime tests passed all 7 tests, including the isolated
  3 methodology x 2 roadmap selection matrix. Runtime verification passed all
  275 checks with archive SHA-256
  `1aa795c12fb166e753dc8523d2ab56b0a2f79ecef553f06abb2afdedcb6b8a9a`.
- 2026-07-13: Release-target Plugin Eval remained 86/B, medium risk, with zero
  failures and the same three static token-budget warning IDs. The live
  provider comparison remains deferred to a later default-switch proposal;
  `core + none` remains the default.
- 2026-07-13: Final development discovery passed 399 tests in 59.332 seconds
  with no failures or skips; packaged discovery passed 7 tests, and strict
  OpenSpec/release/static validation is the final pre-commit gate.
- 2026-07-13: Independent delta review found that generated entrypoint wrappers
  could write `devflow_launcher` bytecode during the documented verifier and
  that the generated AGENTS template omitted two exact routing-ledger fields.
  RED regressions reproduced both issues; generated wrappers now disable
  bytecode before importing the launcher, templates carry every exact ledger
  field, and the focused repair suite passed 68 tests.
- 2026-07-13: Runtime verification was deliberately rerun without the
  `PYTHONDONTWRITEBYTECODE` environment variable and still left release sync
  `current`, proving the verifier no longer dirties its own release tree.
- 2026-07-13: The latest Superpowers/Matt and active-runtime re-audit reopened a
  hardening slice for provider-neutral core gates, advisory-only unselected
  diagnostics, Matt project-local activation, safe legacy-link deactivation,
  current compatibility metadata, and named DevFlow cache/project refresh.
- 2026-07-13: Upstream comparison pinned Superpowers `v6.1.1`/main at
  `d884ae04edebef577e82ff7c4e143debd0bbec99`, Matt main at
  `391a2701dd948f94f56a39f7533f8eea9a859c87`, and Matt `v1.1.0` at
  `d574778f94cf620fcc8ce741584093bc650a61d3`. The approved Matt allowlist is
  6,771 static words versus 20,957 for six comparable Superpowers skills; this
  supports opt-in instruction efficiency, not an outcome-equivalence claim.
- 2026-07-13: Independent review found and closed provider-cleanup parent
  escape/TOCTOU, wrong-digest side writes, missing selection persistence,
  Matt bootstrap precedence, no-repo strict action leakage, provenance action
  leakage, malformed ledger fail-open behavior, and stale guidance. Cleanup now
  anchors parent directories with no-follow dirfds and inode checks.
- 2026-07-13: Final development discovery passed 438 tests in 65.373 seconds;
  packaged discovery passed 8 tests; runtime verification passed 277 checks
  with archive SHA-256
  `6f860c942a16fc853a5caa05ce4f2ef465c28cb1b5f19108a7e2239e173c8570`.
- 2026-07-13: Release sync is `current`. Release-target Plugin Eval is 86/B,
  medium risk, with zero failures and the same three static token-budget
  warnings (`385` trigger, `11,430` invoke, `27,044` deferred tokens). Live
  outcome measurement remains deferred to a separately authorized future
  default-switch study.
- 2026-07-13: The named DevFlow cache was refreshed with the active ChatGPT App
  runtime and now `matches-source`; project migration and skill layout are
  `current`, workflow doctor is healthy, explicit `core + none` is persisted,
  and a post-cleanup dry-run reports no remaining verified Superpowers links.
- 2026-07-13: The validated provider branch was fast-forwarded into `main` and
  pushed to `origin`. Local `main` and `origin/main` were verified aligned; this
  ledger closeout is the only post-verification documentation change.

## Final Result

DevFlow now defaults to an independent `core + none` control plane. Matt is an
optional project-local six-skill methodology profile, Superpowers is an
optional strict profile with manifest-driven hooks, and GSD is required only
when explicitly selected as the roadmap provider. Release and installed-cache
parity are verified, and remote submission to `origin/main` is complete.
OpenSpec archive is intentionally not performed without its separate
authorization.
