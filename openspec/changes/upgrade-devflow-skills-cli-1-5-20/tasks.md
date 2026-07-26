# Skills CLI 1.5.20 Upgrade Execution Contract

## 1. Capability Evidence and Plan

- [x] 1.1 Verify npm `latest`, package repository, Node engine requirement,
  local Node compatibility, and the `1.5.20` CLI install arguments.
- [x] 1.2 Record the proposal, design, delta spec, Skill Routing Ledger,
  validation commands, rollback, and zero Open Questions.
- [x] 1.3 Run strict OpenSpec validation for the implementation-ready change.

## 2. Test-First Development Contract

- [x] 2.1 Add exact assertions for `skills@1.5.20`, methodology Node
  `>=22.20.0`, and the unchanged installer arguments in development and
  packaged provenance tests.
- [x] 2.2 Run the focused development and packaged provenance tests and record
  the expected RED failures against `skills@1.5.9`.
- [x] 2.3 Update only the development provenance verification date, installer
  pin, and methodology runtime requirement.
- [x] 2.4 Rerun the focused development test to GREEN and confirm Matt source,
  hashes, adaptations, and selected skills remain unchanged.

## 3. Source Verification

- [x] 3.1 Run complete source-only pre-promotion tests, strict change and
  repository OpenSpec validation, workflow validation, and `git diff --check`.
- [x] 3.2 Inspect the scoped diff, record source verification evidence, and
  create the source-hash-bound release verification receipt.
- [x] 3.3 Confirm the release sync dry-run reports only the expected DevFlow
  provenance-contract drift.

## 4. Release Promotion and Final Verification

- [x] 4.1 Obtain explicit durable authorization for the separate `dev-flow`
  release promotion external effect.
- [x] 4.2 Promote the verified development source through
  `release_promotion_gate.py --target dev-flow --apply` and prove a second
  release dry-run is current.
- [x] 4.3 Run the complete development suite, packaged tests, release runtime
  verification, and release-target Plugin Eval; fix failures and disposition
  actionable warnings.
- [x] 4.4 Run the internal updater dry-run without applying cache or project
  refresh, then update evidence, workflow state, and this execution ledger.

## Execution Ledger

| Slice | Owner | Write Set | Evidence | Human Gate | Status |
|---|---|---|---|---|---|
| Capability evidence and plan | main agent | this OpenSpec change | npm/CLI/local scan and strict validation | none | done |
| RED contract tests | main agent | `dev/plugins/dev-flow/tests/test_dependencies.py`, `dev/plugins/dev-flow/tests/test_packaged_runtime.py` | focused expected failures | none | done |
| Development source GREEN | main agent | `dev/plugins/dev-flow/docs/dependency-provenance.json` | 26 focused tests passed | none | done |
| Source verification | main agent | change evidence, verification receipt, workflow state | 338 source tests, 56 strict OpenSpec items, receipt `241036fa1b01eb64a8a4a7cd80e636ad9755c91d59e24259967283916f3962db` | none | done |
| Release promotion | main agent | generated `plugins/dev-flow/**` counterpart and evidence | promotion, package/runtime tests, Plugin Eval | explicit release authorization | done |

## Completion Claim

- [x] Development and release provenance expose the exact reviewed installer
  contract.
- [x] Fresh focused, source, full, packaged, runtime, OpenSpec, workflow,
  Plugin Eval, updater dry-run, and diff evidence is recorded.
- [x] Release promotion ran only after explicit authorization; cache refresh,
  direct-main commit, and SSH push remain separately authorized follow-through.
  No project migration, archive, PR, credential mutation, or unrelated cleanup
  was performed by this change.
