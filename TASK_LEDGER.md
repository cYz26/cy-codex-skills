# Task Ledger

## Active Change: Harden Lark Feishu Ops Runtime Contracts

### Goal Contract

- goal_id: OpenSpec change `harden-lark-feishu-ops-runtime-contracts` (no
  Codex goal requested)
- objective: Upgrade every reachable local Lark CLI installation to official
  1.0.69 and deliver a versioned Lark Feishu Ops 0.2.0 plugin whose delegation,
  guidance, continuity, doctor, sync, source/release, and verification
  contracts are fail-closed, privacy-safe, current with official CLI/Codex
  behavior, and proven from development plus generated-release seams.
- scope_in: both reachable local `lark-cli` executables and read-only
  post-upgrade checks; `dev/plugins/lark-feishu-ops/**`; generated
  `plugins/lark-feishu-ops/**`; focused target-selection changes to the existing
  DevFlow release-promotion facade/tests; target-specific release metadata; Lark plugin
  tests/docs/evals; this OpenSpec change; root ledger/state/checkpoint/evidence;
  release-target Plugin Eval and independent review.
- scope_out: Feishu data mutation; auth/profile changes; global official Lark
  skill unload; installed Codex plugin cache refresh; other-project migration;
  production dependencies; unrelated plugin/runtime refactors; destructive
  binary removal; OpenSpec archive; commit; push; PR creation.
- acceptance_criteria: both reachable CLI paths report 1.0.69 with the NVM-first
  path canonical and read-only health/embedded-skill checks passing; unknown,
  raw, mutating, and caller-downgraded actions cannot run direct; arbitrary
  guidance paths are rejected; persisted continuity is bounded metadata-only
  with lifecycle/freshness/security controls; doctor and sync report current
  binaries, skills, roots, versions, homes, JSON and full asset parity; dev
  source and generated 0.2.0 release are current; all focused/full/OpenSpec/
  workflow/release/eval/review gates pass with Plugin Eval zero failures and at
  least 91/B.
- validation_commands: exact CLI path/version/update/skills/doctor/auth smoke;
  Python 3.12 focused and complete development discovery; syntax compilation;
  skill/plugin validation; target release sync dry-run/apply/current; packaged
  runtime smoke; strict change/all OpenSpec; workflow/checkpoint validation;
  fixture-secret scan; release-target Plugin Eval; updater dry-run; independent
  standards/spec review; `git diff --check`.
- success_threshold: every OpenSpec task complete, every acceptance scenario
  covered by passing observable tests, no in-scope P1/P2 finding, no unapproved
  external side effect, release Eval score >=91/B with zero failures, and all
  generated runtime assets current.
- stop_conditions: stop on package ownership that requires destructive removal,
  authentication or Feishu-resource mutation, dependency addition, public name
  change, private-data migration, unrelated dirty-file overlap, release gate
  failure without safe rollback, or a new scope-changing decision.
- knowledge_update_target: none

### Tasks

| task_id | summary | owner | write_set | contract_path | required_evidence | review_gate | status |
|---|---|---|---|---|---|---|---|
| LFO-1 | Current capability evidence, read-only audits, Full OpenSpec, baseline, and planning checkpoint | main + read-only auditors | OpenSpec, ledger, state, checkpoint, evidence | `.planning/agent-tasks/20260715-lark-feishu-ops-cli-upgrade-audit.md`; `.planning/agent-tasks/20260715-lark-feishu-ops-release-audit.md`; `.planning/agent-tasks/20260715-lark-feishu-ops-security-test-audit.md` | official/local matrix, validated contracts, strict change validation, clean baseline | no unresolved question | done |
| LFO-2 | Reversible upgrade and alignment of all reachable Lark CLI executables | main | user-global CLI installations only | not-delegated | path/version/owner before-after, rollback commands, embedded-skill/read-only smoke | no auth/profile or Feishu mutation | done |
| LFO-3 | Canonical development source, release metadata, and RED public-seam contracts | main | `dev/plugins/lark-feishu-ops/**` | not-delegated | no-apply release drift and observed RED suites | TDD seam review | done |
| LFO-4 | Fail-closed policy, strict runtime adapter, trusted embedded guidance, and dynamic domains | main | development scripts/tests | not-delegated | focused GREEN risk/guidance/runtime tests | security + compatibility review | done |
| LFO-5 | Metadata-only continuity, secure persistence, lifecycle, purge, and freshness | main | development scripts/tests | not-delegated | focused GREEN privacy/lifecycle/storage tests | privacy review | done |
| LFO-6 | Multi-binary doctor, current/legacy skill roots, provenance, strict JSON, and full sync parity | main | development scripts/tests | not-delegated | focused GREEN doctor/sync tests and CLI smoke | readiness review | done |
| LFO-7 | Skill/protocol/docs/eval/version updates, target-aware promotion gate, and generated 0.2.0 release | main | development source, focused DevFlow release-gate facade/tests, and generated `plugins/lark-feishu-ops/**` | not-delegated | validators, DevFlow compatibility suite, source receipt, release apply/current, packaged smoke | release authorization and diff review | done |
| LFO-8 | Integrated verification, Plugin Eval, independent two-axis review, and durable closeout | main + review agents | evidence, ledger, state | review contracts created after implementation | full command matrix, findings disposition, clean diff | no archive/cache/commit/push | done |

### Execution Log

- 2026-07-15: The user approved upgrading Lark CLI to the official latest
  version and implementing the complete systemic plugin optimization previously
  recommended. Installed-cache refresh, global skill unload, archive, commit,
  push, and PR creation remain explicit separate effects.
- 2026-07-15: Intake classified the work as a Full OpenSpec integration,
  security, compatibility, migration, and plugin-release change. Official and
  local evidence confirmed latest Lark CLI 1.0.69, two reachable stale versions,
  27 embedded skills, current `.agents/skills` discovery, native Codex subagent
  lifecycle, and the existing fail-open/privacy/readiness defects.
- 2026-07-15: Three read-only audit contracts passed the DevFlow contract
  validator. The proposal, design, three capability specs, and dependency-
  ordered tasks for `harden-lark-feishu-ops-runtime-contracts` are complete,
  have no open questions, and pass strict OpenSpec validation. Production work
  begins with reversible CLI alignment and public-seam RED tests.
- 2026-07-15: Baseline verification passed 47/47 existing plugin tests, plugin
  and skill validation, strict OpenSpec 51/51, workflow validation, and
  `git diff --check`; release Plugin Eval scored 91/B with zero failures and two
  warnings. Public probes reproduced every planned P1/P2 behavior gap.
- 2026-07-15: Both npm-global Lark CLI owners were upgraded by absolute pinned
  commands: NVM 1.0.63 -> 1.0.69 and Homebrew-prefix 1.0.60 -> 1.0.69. The
  canonical official updater synchronized 27 skills to 1.0.69; both update
  checks are current/in-sync, read-only doctor and verified auth checks pass,
  and no auth/profile or Feishu resource mutation occurred.
- 2026-07-15: Canonical development source and public-seam RED contracts were
  established. The observed RED baseline was 29 agent-context assertion
  failures, 22 doctor failures, and eight sync/release failures with no fixture
  errors; the target-aware promotion-gate tests followed their own RED-to-GREEN
  cycle.
- 2026-07-15: Shared runtime, fail-closed policy, and schema-v2 metadata state
  modules now back the stable facades. Agent-context GREEN is 20/20, including
  embedded CLI guidance, unknown/write/high-risk routing, 0600 atomic bounded
  state, sensitive-domain no-cache, purge, pruning, lifecycle, and freshness.
  Sync GREEN is 7/7; Doctor behavior is GREEN with the remaining prompt parity
  update delegated in the documentation write set.
- 2026-07-15: The integrated development source is pre-promotion ready. All
  70 Lark plugin tests and 39 focused DevFlow release tests pass; Python syntax,
  plugin/skill structure, strict OpenSpec 51/51, workflow state, fixture scan,
  and `git diff --check` pass. Source Plugin Eval improved to 81/C after fixing
  its trigger description. Its remaining development-tree token finding comes
  from deliberately retained tests/evals, while the complexity warning is an
  evaluator whole-file decision count rather than an identified oversized
  function; the generated release remains the authoritative >=91/B gate.
- 2026-07-15: Read-only release planning reports exactly the expected 0.2.0
  runtime/document changes plus removal of old release-only tests, evals, and
  bytecode. The user's request to complete the approved optimization is durable
  release authorization for only `lark-feishu-ops`; installed-cache refresh,
  global skill unload, archive, commit, push, and PR creation remain excluded.
- 2026-07-15: The issuer-gated promotion facade now preserves the `dev-flow`
  default while selecting target-specific verification profiles. Built-in Lark
  promotion reports its nine-test generated-package command; other targets
  fail closed before authorization/sync unless release metadata declares a
  valid verification command. The authorized 0.2.0 Lark release was promoted,
  inspected, and a second target check is `current` with source receipt
  SHA-256 `811eadebb53040adb330302a798741c0990449383528e87278d7625a62b70a9b`.
- 2026-07-15: Fresh integrated verification passed 90/90 Lark development
  tests, 339/339 DevFlow tests, 9/9 release-package tests, the offline packaged
  self-test, 19-file AST parsing, plugin/skill validators, strict OpenSpec
  51/51, release parity, workflow validation, fixture/privacy checks, and
  `git diff --check`. Both absolute Lark CLI paths report 1.0.69 and official
  update status is `already_up_to_date` with 27 skills in sync.
- 2026-07-15: Release-target Plugin Eval scored 91/B with zero failures. The
  two warnings are retained with explicit disposition: deferred supporting
  text is deliberately on-demand, while the Python heuristic reports maximum
  complexity 238 together with `py_function_count: 0`, so it identifies no
  actionable function. Release coverage artifacts remain absent by design;
  behavior is covered by the development and packaged suites.
- 2026-07-15: Independent final Standards and Spec/Security reviews passed
  with no remaining actionable P0-P3 finding. The updater dry-run reports the
  installed 0.1.0 plugin cache differs from repository release 0.2.0 and would
  refresh; no apply ran. Doctor core readiness passes but its aggregate status
  remains WARN because 27 verified official global Lark skills remain exposed.
  No cache refresh, global skill unload, auth/profile change, Feishu mutation,
  destructive rollback, archive, commit, push, or PR action was performed.
- 2026-07-15: The user separately authorized the local global plugin-cache
  refresh and remote Git publication. The first sync-mediated refresh exposed a
  stale `codex-switch` shim targeting the removed `/Applications/Codex.app`
  path and made no cache change. The verified official ChatGPT app CLI at
  `/Applications/ChatGPT.app/Contents/Resources/codex` 0.144.2 then installed
  `lark-feishu-ops@cy-codex-skills` 0.2.0 by absolute path. Post-refresh
  verification reports `matches-source`, 17/17 runtime files byte-identical,
  no changed/missing/unexpected files, and no refresh recommendation. The 27
  verified official global Lark skills remain intentionally loaded because the
  user authorized refresh, not unload; auth/profile and Feishu resources remain
  unchanged.

## Previous Verified Change: Simplify DevFlow to Matt-native Methodology

### Goal Contract

- goal_id: Codex goal `019f5e9f-b2eb-7070-96c1-37ae2143bbcd`
- objective: Implement and verify one active DevFlow/OpenSpec control plane with
  the pinned six-skill MattPocock engineering pack, bounded subagent execution,
  and an isolated read-only legacy provider inspector while removing every
  active Superpowers/GSD runtime, routing, config, fixture, readiness, release,
  and documentation dependency.
- scope_in: DevFlow development source/tests/docs/templates/provenance,
  generated release, root workflow control plane, the new OpenSpec change,
  explicit legacy inspection of this checkout, and the separately authorized
  targeted activation of exactly six Matt skills in this project's
  `.agents/skills`.
- scope_out: broader Matt workflow skills, roadmap replacement, production
  dependencies, ignored legacy installation cleanup, installed-cache refresh,
  broad current-project migration, OpenSpec skill regeneration, other-project
  migration, archive, unrequested commit, and push.
- acceptance_criteria: active config has no provider selection; static
  capabilities use only DevFlow/OpenSpec and the six pinned Matt primitives;
  normal diagnostics expose no Superpowers/GSD surface; legacy inspection is
  deterministic/read-only/import-isolated; subagent write ownership is
  validated; source/package/runtime/OpenSpec/workflow/eval/review gates pass.
- validation_commands: focused RED/GREEN suites, full Python 3.12 development
  and package discovery, strict change/all OpenSpec validation, release
  promotion/current/runtime checks, workflow validation, forbidden-reference
  and import checks, release-target Plugin Eval, and `git diff --check`.
- stop_conditions: stop on a newly discovered compatibility break beyond the
  approved provider removal, destructive migration, dependency addition,
  ambiguous historical/user-data deletion, scope-changing product decision,
  or an in-scope failure that cannot be repaired safely.
- knowledge_update_target: none

### Tasks

| task_id | summary | owner | write_set | contract_path | required_evidence | review_gate | status |
|---|---|---|---|---|---|---|---|
| DF-MN-1 | Target contract, upstream pin, active-surface audit, and Full OpenSpec plan | main + audit agents | OpenSpec, ledger, checkpoint | `.planning/agent-tasks/20260714-simplify-devflow-matt-native-audit.md`; `.planning/agent-tasks/20260714-simplify-devflow-matt-capability-audit.md`; `.planning/agent-tasks/20260714-simplify-devflow-migration-test-audit.md` | strict change validation, source/hash matrix, replace/remove/migrate/preserve map | no unresolved decision | done |
| DF-MN-2 | RED public-seam contracts for methodology, config, legacy inspection, agents, and forbidden active references | main | development tests | not-delegated | observed target failures before production edits | TDD seam review | done |
| DF-MN-3 | Static methodology, side-effect policy, readiness, and project-local Matt activation | main + methodology-hardening | development scripts/docs/data/tests | `.planning/agent-tasks/20260714-simplify-devflow-methodology-hardening.md` | focused GREEN capability and activation tests | standards + spec review | done |
| DF-MN-4 | Control-plane simplification, legacy inspector, and active Superpowers/GSD removal | main | runtime/config/hooks/state/archive/docs/tests | not-delegated | focused GREEN plus import/forbidden-reference proof | compatibility review | done |
| DF-MN-5 | Generated release alignment and full verification | main | generated `plugins/dev-flow/**`, evidence | not-delegated | full dev/package/runtime/OpenSpec/workflow/Eval results | separate durable release authorization | done |
| DF-MN-6 | Independent two-axis review and durable closeout | main + review agents | review/evidence/ledger/state | `.planning/agent-tasks/20260714-simplify-devflow-final-review.md`; `.planning/agent-tasks/20260714-simplify-devflow-final-spec-review.md` | findings disposition and rerun evidence | no archive/push/cache/migration | done |

### Execution Log

- 2026-07-14: The user approved complete active Superpowers/GSD removal, one
  DevFlow/OpenSpec plus Matt path, an isolated read-only legacy migrator, and a
  bounded subagent strategy. A quality-gated Codex goal was created.
- 2026-07-14: Two read-only agents mapped the active provider call graph and
  independently verified Matt `v1.1.0` at commit
  `d574778f94cf620fcc8ce741584093bc650a61d3`, the six existing skill hashes,
  and the exclusion of flow-owning skills such as `implement` and `to-spec`.
- 2026-07-14: `simplify-devflow-matt-native` proposal, design, three delta
  specs, and tasks were completed with no open questions and passed strict
  OpenSpec validation. Production implementation starts with public-seam RED
  tests; shared artifacts and generated release remain main-agent-owned.
- 2026-07-14: The source implementation replaced provider/profile/roadmap
  selection with a static six-skill Matt methodology, minimal fail-closed
  config, trusted project-local dependency checks, exact OpenSpec 1.6 local
  skills, and deterministic read-only legacy inspection. Active
  Superpowers/GSD modules, fixtures, benchmarks, phase gates, and maintained
  guidance were removed from development source.
- 2026-07-14: Bounded subagent execution was enforced through validated worker
  ids, exact disjoint write sets, protected primary-agent paths, evidence and
  stop conditions. One contracted worker hardened methodology/project-skill
  trust; independent Standards and Spec reviews found and drove fixes for
  symlink/nonregular trees, rollback preservation, fail-closed config/state,
  complete release receipts, and shared-file ownership.
- 2026-07-14: Focused release and archive regression suites passed 35/35 and
  18/18 after the final source hardening. The checked-in release remains stale
  by design, so complete development discovery has the single expected
  release-smoke failure and runtime verification reports drift until separately
  authorized promotion. Current-project Matt activation is also still an
  explicit write boundary; no silent skill migration or legacy cleanup ran.
- 2026-07-14: The canonical pre-promotion runner passed 298/298 tests across
  17 source modules; strict OpenSpec passed 50/50, workflow-state validation
  returned zero issues and only the expected pending-compact advisory, and
  `git diff --check` passed. A current
  source receipt was recorded with SHA-256
  `7d68b75270734cb0afa7d9eb59f9b83ee8369451c7dfcd0de90aae2e007f26ae`;
  release dry-run reports `pending`, ready with no blockers, but no durable
  release authorization.
- 2026-07-14: A contracted read-only activation audit confirmed all six Matt
  project skills are missing (not drifted), the pinned vendored source is
  ready, and a dry-run would copy exactly those six skills. The active Goal
  excludes active-project migration, so current-project activation and GSD
  cleanup are retained as out-of-scope residuals rather than completion gates.
- 2026-07-14: Completion and active-surface audits found two source gaps and an
  evidence-schema gap. The inspector now recognizes `.codex/config.toml`
  registrations without exposing values; maintained release logic uses a
  generic `docs/history/**` quarantine; development and release tests enforce
  exact legacy-name allowlists; all 13 current-change agent contracts pass
  batch validation with unique workers and disjoint writes.
- 2026-07-14: Source-only Plugin Eval scored 68/D with one development-tree
  token-cost failure, active budget 10,324 tokens, deferred cost 263,920
  tokens, and four warnings. That diagnostic is deferred
  because trimming tests/history would be destructive and out of scope; the
  generated release target remains the required final zero-failure Eval after
  authorized promotion.
- 2026-07-14: Final source re-review passed. The expanded legacy matcher covers
  retired provider/profile/selector/binding/phase identifiers and the only
  remaining hits outside the source allowlist are in the intentionally stale
  generated release. Completion evidence now passes 13/13 contract, scope-out,
  receipt/hash, and authorization-only-gate checks.
- 2026-07-14: A disposable copy of the current worktree completed real release
  promotion without touching the live checkout. The simulated promoted tree
  passed 332/332 development tests, 5/5 packaged tests, 282/282 runtime checks,
  OpenSpec 50/50, workflow/diff validation, release Eval 86/B with zero
  failures, and a second idempotent apply (`status=current`). Live release
  promotion remains separately authorization-gated.
- 2026-07-14: No release promotion, installed-cache refresh, other-project
  migration, active-project migration, destructive legacy cleanup, archive,
  commit, or push is included in the current authorization. Source verification
  evidence is frozen before requesting the remaining release apply decision.
- 2026-07-14: The missing live release authorization repeated across the Goal's
  required continuation threshold after all safe source and disposable-release
  work was exhausted. Goal `019f5e9f-b2eb-7070-96c1-37ae2143bbcd` was marked
  blocked; explicit `授权发布同步` is the sole resume condition.
- 2026-07-14: The user resumed the Goal and separately approved live release
  sync plus the current project's targeted six-skill Matt refresh. The release
  gate promoted `dev/plugins/dev-flow` to `plugins/dev-flow`; a check and second
  apply both returned `current` with no changed, missing, stale, or deleted
  managed paths.
- 2026-07-14: Project refresh diagnostics ran before and after apply. With
  `--skip-official-installs` and six explicit capabilities, dry-run planned and
  apply copied only `grilling`, `tdd`, `diagnosing-bugs`, `code-review`,
  `codebase-design`, and `domain-modeling`. OpenSpec remained `current` with
  `changed=false`; ignored GSD history was preserved.
- 2026-07-14: Live post-promotion verification passed 332/332 development
  tests, 5/5 packaged tests, 282/282 runtime checks, strict OpenSpec 50/50,
  workflow validation with zero issues, 29/29 forbidden-reference checks,
  9/9 legacy-isolation checks, release parity/idempotence, and `git diff
  --check`. Release-target Plugin Eval scored 86/B with zero failures; its
  three static token-budget warnings are recorded for measured-usage follow-up.
- 2026-07-14: Local-reference dry-run confirmed the installed DevFlow cache
  still differs from the newly promoted release. Cache refresh, broad project
  migration, GSD cleanup, archive, commit, and push remain outside the granted
  actions.
- 2026-07-14: Independent Standards review passed. Spec review found one P2
  packaged-document allowlist exception; RED tests reproduced it, the legacy
  document was generalized, both allowlists were tightened, the new
  source-bound receipt was promoted, and all final suites were rerun. Targeted
  Standards and Spec re-reviews both passed with no unresolved finding. Final
  evidence is recorded at
  `.planning/devflow/verification/20260714214817-simplify-devflow-matt-native-final.md`.

## Previous Completed Change: DevFlow Skill Portfolio Optimization

### Goal Contract

- goal_id: Codex goal `019f5b76-7521-7d11-aa82-624f0392a461`
- objective: Review and optimize every DevFlow plugin skill, classify each by
  ownership/reachability/compatibility, remove only evidence-backed dead
  resources, keep source and release coherent, and finish with focused/full
  tests, strict OpenSpec, runtime checks, zero-failure release Plugin Eval, and
  a lower active invoke budget.
- scope_in: `dev/plugins/dev-flow/skills/**`, focused DevFlow tests, generated
  `plugins/dev-flow/**`, change evidence, root ledger, and DevFlow state.
- scope_out: public skill retirement, invocation-policy changes, provider or
  dependency changes, live/paid benchmarks, installed-cache refresh, project
  migration, archive, commit, and push.
- acceptance_criteria: sixteen public skills remain; six duplicated unlinked
  resources are removed; every retained/new resource is directly linked;
  release invoke cost is at most 10,000 tokens with zero Plugin Eval failures
  and score at least 86/B; all required validation passes.
- validation_commands: focused RED/GREEN and quick validation, complete
  development/package discovery, strict OpenSpec, release promotion/current,
  runtime verification, workflow validation, release-target Plugin Eval,
  updater dry-run, and `git diff --check`.
- stop_conditions: stop on ambiguous public consumers, removal requiring a
  retirement migration, invocation-policy changes, dependency/provider scope,
  failed validation that cannot be fixed in scope, or any external apply gate.
- knowledge_update_target: none

### Tasks

| task_id | summary | owner | write_set | contract_path | required_evidence | review_gate | status |
|---|---|---|---|---|---|---|---|
| DF-SP-1 | Portfolio/reference/eval/compatibility audit and Full OpenSpec plan | main + audit agents | OpenSpec and audit contract | `.planning/agent-tasks/20260713-devflow-skill-portfolio-audit.md` | 16-skill matrix, official docs, baseline Eval, strict validation | no unresolved public deletion | done |
| DF-SP-2 | RED portfolio and resource-reachability contracts | main | focused DevFlow tests | not-delegated | expected failing tests before edits | TDD review | done |
| DF-SP-3 | Progressive-disclosure rewrites and six-file cleanup | main | source skills | not-delegated | GREEN tests and 16 quick validators | skill correctness review | done |
| DF-SP-4 | Budget iteration and broad source verification | main | source skills/tests/evidence | not-delegated | invoke <=10000, full source suite, strict OpenSpec | Plugin Eval gate | done |
| DF-SP-5 | Generated release and runtime verification | main | generated `plugins/dev-flow/**` | not-delegated | promotion/current, packaged suite, runtime hash, release Eval | release gate | done |
| DF-SP-6 | Independent review and durable closeout | main + reviewers | evidence, ledger, state | `.planning/agent-tasks/20260713-devflow-skill-portfolio-review.md` | findings disposition, workflow and diff checks | no archive/commit/push | done |

### Execution Log

- 2026-07-13: Selected `core + none`; intake classified the request as a Full
  OpenSpec compatibility-changing plugin refactor and created an active Codex
  goal with explicit evidence, scope, non-goals, and stop conditions.
- 2026-07-13: Three read-only agents audited references, Plugin Eval, and
  packaging/compatibility. All sixteen skills are public, required, installed,
  and not safe to delete directly. Six unlinked duplicated resources are safe
  cleanup candidates; `dev-flow-refresh` is the primary main-body optimization.
- 2026-07-13: Official Codex docs confirmed progressive disclosure and that
  disabling implicit invocation removes natural-language triggering. The plan
  therefore preserves fifteen implicit skills plus explicit-only
  `claude-code-delegate`.
- 2026-07-13: Release baseline is 86/B, medium risk, zero failures, trigger 385,
  invoke 11,996, deferred 27,397, active 12,381. All sixteen individual skills
  are 100/A. The new OpenSpec change is complete and strictly valid.
- 2026-07-13: Portfolio RED ran 71 tests with 20 expected resource-contract
  failures. The source implementation then linked or added eight conditional
  resources, removed only six approved duplicates, preserved all sixteen public
  names, and passed 71/71 plus all sixteen quick validators.
- 2026-07-13: Three independent closeout reviews returned one clean release
  verdict and four actionable P1/P2 concerns. The implementation restored the
  explicit delegation-authority gate, routes project diagnostics through their
  reference, asserts branch-specific resource use, and records exact TDD and
  two-target Plugin Eval evidence.
- 2026-07-14: Independent pre-commit scope review found that the compressed
  `dev-flow-refresh` description accidentally made a DevFlow upgrade a
  prerequisite for project refresh. A focused RED/GREEN contract now protects
  the three independent refresh triggers in both source and release metadata.
- 2026-07-14: Final development discovery passed 455/455 in 66.339 seconds.
  Generated release promotion is current, packaged discovery passed 8/8,
  runtime verification reports `verified`, and source/release Skill trees are
  byte-identical.
- 2026-07-14: Final release Plugin Eval is 86/B with zero failures: trigger 390,
  invoke 9,906, deferred 28,435, explicit-only 799, total 38,731. Active cost is
  10,296, down 2,085 from baseline without changing invocation policy.
- 2026-07-14: The local-reference updater remained dry-run-only. Release assets
  and project skill layout are current; the installed DevFlow cache still needs
  an explicit refresh, and project migration remains blocked by the active
  phase/change. No cache, migration, archive, or push was applied; the local
  commit was authorized separately after implementation closeout.

## Previous Completed Change: OpenSpec 1.6 Integration

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

## Historical Snapshot: Superseded Provider Architecture

> Historical evidence from the 2026-07-13 provider-architecture change. This
> section is superseded by the active Matt-native change above and MUST NOT be
> used as current configuration, routing, dependency, or execution guidance.

### Goal Contract

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

### Tasks

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

### Execution Log

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

### Historical Final Result (Superseded)

At that historical fixed point, DevFlow defaulted to an independent `core +
none` control plane. Matt was an optional project-local six-skill methodology
profile, Superpowers was an optional strict profile with manifest-driven hooks,
and GSD was required only when explicitly selected as the roadmap provider.
Release and installed-cache parity were verified, and remote submission to
`origin/main` was complete. OpenSpec archive was intentionally not performed
without its separate authorization.
