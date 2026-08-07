# Implementation Evidence

## Task 1.1 — Approval and Executable Baseline

- Timestamp: `2026-08-06T14:53:06+08:00`
- User authorization: `开始实现一下`
- Authorized boundary: development-source implementation through fresh source
  verification. Generated `plugins/dev-flow/**`, installed-cache refresh,
  consumer-project apply, AGENTS candidate merge, legacy cleanup, dependency
  changes, archive, commit, push, PR, and publication remain closed.
- OpenSpec route: `spec-driven`, change state `ready`, 0/37 tasks before this
  receipt. Proposal, both delta specs, design, tasks, status, and apply
  instructions were reread before production edits.
- Methodology: `test-first-execution` is `ready`; public seams are the existing
  project-migration CLI JSON/filesystem contract and executable refresh-impact
  release checks.
- Goal Gate: required by task size, recorded as `skipped_with_reason` because
  goal tools require an explicit goal-backed request; the durable Goal Contract
  remains in `design.md`.

### Identity Baseline

- Repository `HEAD` and `origin/main`:
  `187c81cb25a13cde58b9c972a9ed050311f82775`.
- OpenSpec: `1.7.0`; Python: `3.12.13`.
- Development, generated release, and installed-cache project-migration
  manifests all have SHA-256
  `ed291d0fbb5307df3ad455ea3510bf03136978ab730538a5a0e4b1ca45110a64`.
- Installed cache:
  `/Users/cY/.codex/plugins/cache/cy-codex-skills/dev-flow/0.3.0+codex.20260529145038`;
  read-only updater result is `matches-source`.
- Doctor diagnosis is `healthy`; project migration and skill layout are
  `current`; active runtime/stored plugin version is
  `0.3.0+codex.20260529145038`.

### Schema and Impact Baseline

- Project-migration manifest schema: `1.0`.
- Migration state schema: `1.0`; it stores only plugin release version,
  project-local skills, managed files, and timestamp.
- `managedFiles` is empty; there is no independent project workflow schema,
  migration-engine schema, refresh-contract revision/digest, migration chain,
  or verified receipt reference.
- No existing root policy, template, or DevFlow Skill contains a Project Refresh
  Impact record. Baseline disposition is therefore `changed`: this change adds
  the initial executable contract, project schema head `1`, v0-to-v1 migration,
  fixture matrix, and pre-promotion/release enforcement.

### Worktree and Write Set

- The approved exact development write set is recorded in `tasks.md`.
- The only visible pre-existing worktree edit is
  `openspec/changes/separate-git-transport-from-github-auth/evidence/implementation.md`
  at 40 added lines. Its baseline diff digest is
  `156697b2fda831afd5ac23a2e5ce8ffc98d18836f345535915bded204d812ba6`;
  it is unrelated and must remain untouched.
- No apply, cache refresh, project migration, release sync, cleanup, commit, or
  network-mutating command ran during baseline capture.

## Task 1.2 — Planner Safety Matrix

- Seam: public `plan_project_refresh(repo, plugin_root)` result plus complete
  fixture-tree snapshot before and after the call.
- RED 1: `ModuleNotFoundError: workflow_project_refresh` for a non-adopted
  directory established the missing deterministic seam.
- RED 2: adopted current configuration raised `NotImplementedError`.
- RED 3: clean tracked legacy configuration returned `baseline_ambiguous`
  instead of a redacted authorized migration.
- RED 4: an adopted project without `.dev-flow.json` returned `missing` rather
  than a create-if-absent action.
- RED 5: conflict and unsafe-input fixtures did not enumerate the preserved
  configuration path; the unreadable fixture also exposed a test-snapshot
  permission assumption, fixed without weakening the production assertion.
- GREEN: `/opt/homebrew/bin/python3.12 -B -m unittest
  dev/plugins/dev-flow/tests/test_project_refresh.py -v` passes 6/6.
- Covered behavior: current schema, no adoption marker, clean tracked legacy
  root/workflow selectors, conflicting aliases, exact unknown JSON
  value/type preservation fingerprint, redaction, absent config in an adopted
  project, and untracked, dirty, non-Git, symlinked, non-regular, and unreadable
  config inputs. Every planning fixture proves zero writes by full-tree
  snapshot.
- Changed files: `tests/test_project_refresh.py` and new
  `scripts/workflow_project_refresh.py`; no external effect or residual blocker.

## Task 1.3 — Version Registry and Sealed Plans

- RED: the plan had no `sourceIdentity`; the contract could not distinguish
  plugin release, engine schema, project schema, or refresh revision.
- GREEN introduced development manifest schema `2.0`, engine schema `2.0`,
  project schema range `0..1`, stable migration ID
  `legacy-selection-v0-to-v1`, immutable config target, declared tracked inputs,
  and a canonical refresh-contract digest.
- Registry fixtures prove gap, fork, cycle, duplicate ID, and unknown
  predecessor/no-route graphs return `blocked` before a project write.
- Plan fixtures prove identical managed state yields byte-equivalent plans;
  unrelated Git WIP is reported but excluded from `planSha256`; managed config
  and declared source input changes alter the recomputed plan and apply returns
  `plan_stale` with zero additional writes.
- Unrecognized configuration is `baseline_ambiguous`; the supported v0 fixture
  resolves through exactly one step to head v1.
- GREEN command: `/opt/homebrew/bin/python3.12 -B -m unittest
  dev/plugins/dev-flow/tests/test_project_refresh.py -v` passes 13/13.
- New contract assets and five migration fixtures are development-source only;
  generated release and installed cache remain untouched.

## Tasks 1.4–3.6 — Transactional Engine and Compatible CLI

- Added RED/GREEN coverage for real overlap and symlink-parent preflight with
  complete repository/external snapshots, missing authorization, stale plans,
  state-last advancement, promotion and verification failure, incomplete
  subsets, post-apply edits, receipt replay/tamper, retained recovery state,
  explicit rollback, and compatibility invocations.
- The existing `plugin_project_migration.py` now exposes `plan`, `apply`,
  `verify`, and `rollback`. Canonical flags are `--expect-plan` and repeated
  `--allow`; the older `--plan-sha256` and `--authorize` spellings remain
  accepted. No-subcommand inspection and legacy `--apply` remain compatible;
  the latter never grants `workflow-config-migration`.
- The executor accepts only a finite operation set, validates ownership,
  dependencies, path overlap, symlink ancestry, before fingerprints, sources,
  and rollback completeness before the first project write, then stages and
  promotes deterministically. Migration state is written only after project
  paths verify.
- Apply and rollback receipts are repository-, migration-state-, and
  action-set-bound. Verification reads managed paths afresh. Rollback refuses
  post-apply edits; failed restoration retains a journaled transaction and
  blocks later refresh until manual recovery is recorded.
- Managed links, verified Matt/OpenSpec trees, and compatibility-mode missing
  control-plane files now use the central executor. The verified-tree path
  preserves historical result fields while exposing the retained transaction
  path, and successful temporary control-plane directories are removed only
  when this invocation created them.
- Review repairs added after RED reproduction: reject forged deletion receipts,
  represent current config with stale/missing state as a state-only refresh,
  fail closed on retained Skill-tree transactions, verify trusted Skill-source
  ancestry, preserve baseline analyzer errors, reject immutable-target removal,
  and return stable JSON rather than tracebacks for operator errors.

## Tasks 4.1–4.5 — Skill, Guidance, and Protected Surfaces

- `dev-flow-refresh` is the global-first orchestrator and delegates every
  deterministic one-project write to the existing CLI. Its reference records
  the exact plan/apply/verify/rollback sequence, canonical flags, receipt and
  recovery handling, non-Git limitations, and aggregate evidence.
- `AGENTS.md.generated` remains merge-only. Active `AGENTS.md`, divergent
  candidates, non-symlink Skill targets, custom official Skills, legacy
  `.codex/skills`, hook/agent artifacts, and historical planning data are never
  silently adopted, overwritten, or deleted.
- The isolated legacy inspector is integrated as redacted report/manual
  evidence and now rejects symlinked parent ancestry before reading candidate
  files or traversing hook roots.
- Root guidance, maintained templates, engineering/review policy, planning
  Skills, README, and ledger now require a Project Refresh Impact disposition
  for project-facing changes.

## Tasks 5.1–5.5 — Executable Future-Update Gate

- Manifest schema `2.0` separates plugin version, engine schema `2.0`, project
  schema range `0..1`, and refresh-contract revision `1`. The immutable v1
  target and fixture matrix cover current, three safe legacy shapes, and one
  ambiguous/manual-only shape.
- The final tracked-input digest is
  `6a6e6a4afcc4896e41d0311708be997da4c59e68b727574fb788484f2e207c22`;
  the JSON schema accepts only a 64-character lowercase SHA-256, with no
  source-verification placeholder.
- `analyze_project_refresh_impact` reports `changed_covered`, binds evidence to
  `add-versioned-devflow-project-refresh`, and proves migration coverage
  `0 -> legacy-selection-v0-to-v1 -> 1`. It fails closed for stale/missing
  evidence, required-owner omissions, immutable config mutation/removal,
  config-sensitive changes without schema advance, and tracked drift without
  refresh-revision advance.
- Pre-promotion and release verification pass the active change ID and retain
  baseline parsing errors. Runtime Doctor/updater output now includes
  structured source/release/active-cache refresh identities; registration-only
  success cannot satisfy freshness.
- Packaging tests prove the manifest, schemas, config target, fixtures,
  CLI/runtime, Skill/reference, and migration registry form one release unit.
  The checked-in generated release was intentionally not updated at this
  source gate.

## Task 6.3 — Review Disposition

- Two independent read-only code-review passes covered correctness, security,
  compatibility, transaction/rollback, release-gate completeness, and test
  quality. Every blocking finding was reproduced and resolved in the approved
  source write set.
- The final manual review found no second refresh writer, no secret-bearing
  rollback payload, no executable migration loaded from the manifest, no
  active AGENTS overwrite, and no cleanup/network/release/cache/consumer side
  effect.
- Goal Gate correction: after implementation resumed, a repository-bound goal
  was created for source implementation and source verification through the
  release-sync stop boundary. The earlier `skipped_with_reason` entry above is
  retained as the truthful pre-edit baseline, not the final goal disposition.
- No new incidental finding remains deferred or blocked. The unrelated
  Git-transport evidence diff still hashes to
  `156697b2fda831afd5ac23a2e5ce8ffc98d18836f345535915bded204d812ba6`.

## Task 9.1 — Pre-submit Review Reopen and Goal Binding

- Timestamp: `2026-08-07T11:02:41+08:00`.
- User decision: proceed with the recommended systemic repair before any
  staging, push, or plugin refresh.
- Active Goal: thread `019fda1b-d564-7c40-9d8a-e1fc47c2fe93`; its objective
  binds the four review corrections, fresh source/release proof, exact direct-
  main submission, and targeted `dev-flow@cy-codex-skills` refresh.
- Canonical route: `add-versioned-devflow-project-refresh` is reopened at
  37/45; `repair-devflow-goal-gate-lifecycle` remains paused with its artifacts
  unchanged.
- Public TDD seams: migration CLI `plan/apply/verify` JSON plus filesystem
  outcome; Project Refresh Impact/release-gate result; published receipt JSON
  schema.
- Required corrections: future-head/target derivation, configuration/state
  ambiguity, manifest-only impact drift, and independently complete
  verification receipts.
- Capability diagnosis: implementation planning, test-first execution, root-
  cause diagnosis, change review, and completion proof are ready; no dependency
  action is required.
- Unrelated work remains excluded: the Git-transport evidence diff is still
  SHA-256
  `156697b2fda831afd5ac23a2e5ce8ffc98d18836f345535915bded204d812ba6`.
- Authorized later effects remain dependency ordered: generate only the
  DevFlow release after source proof, submit exact intended paths directly to
  `origin/main`, then refresh/read back only the named DevFlow cache. Consumer
  projects, broad updater actions, cleanup, archive, PR, and publication remain
  closed.

## Tasks 9.2 and 9.4 — Public-seam RED Evidence

- Future-head/config-state command:
  `PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -B dev/plugins/dev-flow/tests/test_project_refresh.py ProjectRefreshTests.test_future_contract_head_drives_current_detection_and_create_target_bytes ProjectRefreshTests.test_trusted_configuration_and_state_schema_disagreement_is_ambiguous ProjectRefreshTests.test_contract_plan_and_receipt_match_their_published_json_schemas`.
  Result: RED, 3 tests run and 3 expected failures. The public plan reported
  observed schema `1` for a v2 target, trusted v0 config plus recorded v1 state
  still produced a migration action, and the verification receipt lacked
  `actionSetSha256`, `actions`, `applyReceiptPath`, `authorizations`,
  `migrationPath`, `preservedPaths`, `projectSchema`, `rollbackStatus`, and
  `stateBeforeFingerprint`.
- Manifest-only command:
  `PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -B dev/plugins/dev-flow/tests/test_release_sync.py ProjectRefreshImpactTests.test_impact_gate_rejects_manifest_only_adapter_changes_without_revision_advance`.
  Result: RED for both `projectLocalSkills` and `managedFiles` subcases because
  the public impact result had no `manifestChanged` field and did not enforce a
  refresh-contract revision for those adapter-only changes.
- These failures reproduce the four review findings without private-helper
  assertions and establish the GREEN contract for tasks 9.3 and 9.5.

## Task 9.3 — Future-head and Conflicting-evidence GREEN

- The contract loader now validates and materializes every declared immutable
  JSON configuration target. Current-schema detection matches those targets in
  descending version order while allowing unrelated user-owned settings, so it
  does not infer schema `1` merely from `workflow.mode`.
- Create-if-absent action fingerprints and staged bytes now share the validated
  manifest head target. A head-2 fixture applies, verifies, records schema `2`,
  and replans `current` without a v1 loop.
- Trusted migration state exposes its recorded project schema and receipt trust.
  When it disagrees with configuration evidence, the plan is
  `baseline_ambiguous`, removes the configuration action, suppresses state
  sync, and preserves the path for manual resolution.
- Fresh command:
  `PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -B dev/plugins/dev-flow/tests/test_project_refresh.py`.
  Result: GREEN, 41 tests run.

## Task 9.5 — Manifest Impact and Receipt GREEN

- The impact analyzer now compares a canonical adapter-manifest identity for
  schema, targets, migration steps, managed files, project-local Skills, and
  AGENTS ownership, and separately exposes source/baseline refresh-contract
  digests. Manifest-only drift requires a revision advance; manifest config
  structure still requires a schema advance.
- A revision-advanced `managed-refresh` decision may retain the compatible
  schema head only when project schema/targets/steps and immutable target bytes
  are unchanged. This permits the reviewed runtime correction without
  weakening the existing RED guard for a changed config reader that lacks that
  explicit decision.
- Verification receipts now independently bind the project schema, migration
  path, complete selected actions and fingerprints, authorizations, changed and
  preserved paths, before/after state fingerprints, action-set digest,
  verification result, rollback status, and both receipt paths. The published
  JSON schema requires the fields for both apply and verification receipts.
- Project Refresh Impact advanced from revision `1` to `2` with
  `schemaDecision: managed-refresh`, project schema head `1`, canonical manifest
  identity `22821cc08ce984b8e38e088f6abb69e8a0073b169fa3d30f95ff84a32170d61e`,
  and tracked-input digest
  `8e3d13227704ba0c13d24c103682e3b0bca23c381acf81a5168c252c3fece8d8`.
- Fresh focused results: project-refresh 41/41 GREEN; impact 10/10 GREEN;
  complete release-sync 44/44 GREEN before the final digest-only manifest
  update. The real source-versus-release analyzer now reports
  `changed_covered`, `managedRefreshWithoutSchemaChange: true`, no errors, and
  `refreshContractDigestChanged: true`.

### Independent-review rejection of the first task 9.3–9.5 GREEN

The first GREEN claim above is retained as chronological evidence but is
superseded. Independent Standards and Spec reviews found three blockers before
release generation:

- a head-2 contract detected supported v1 but rendered no executable migration
  action, and a v0 plan advertised two steps while executing only v0-to-v1;
- the temporary generic `managed-refresh` exception allowed a tracked
  configuration-sensitive planner change to bypass the durable schema-advance
  rule;
- receipt field presence passed JSON Schema, but runtime verification accepted
  a tampered `stateBeforeFingerprint` and did not accept/validate the standalone
  verification receipt.

Tasks 9.3–9.5 are reopened. Release generation remains blocked until public-
seam v1/v0-to-head2 execution, an actual immutable target/schema/step/fixture
advance, and standalone apply/verification receipt tamper checks are GREEN.

## Corrected Tasks 9.3–9.5 GREEN

- Corrective RED: the public future-head test initially planned no executable
  v1-to-v2 action, and public `verify` rejected the generated standalone
  verification receipt by kind before it could validate its evidence. The
  tamper fixture also demonstrated that an invalid
  `stateBeforeFingerprint` was not inspected at runtime.
- The planner now renders one atomic configuration action whose sealed source
  carries the complete ordered migration path. Apply executes every registered
  pure step in order, records every applied step ID, preserves unrelated JSON,
  and reaches the manifest head for both v1 and v0 inputs.
- The real contract advances to project schema head `2`, retains immutable
  target v1, adds immutable target v2 and the unique
  `full-openspec-v1-to-v2` merge step, updates new-project scaffolding and the
  read-only legacy inspector to the v2 target, and covers current-v2, v1, v0,
  and manual-only fixtures.
- The configuration-sensitive schema check is unconditional; the superseded
  `managed-refresh` bypass and its output/stale-evidence field were removed.
  The source-versus-release analyzer now reports `changed_covered`,
  `schemaDecision: advanced`, head `2`, revision `2`, migration coverage
  `1 -> full-openspec-v1-to-v2 -> 2`, no errors, canonical manifest identity
  `cc56f6723882b4b0fe3da0a9ac96f97b49b57085a3c19d012a2640eef291333e`,
  tracked-input digest
  `ee6817cc798f64d1976c815accbad39cc2966e6244b1eeb019778ba8d9d597d1`,
  and refresh-contract digest
  `sha256:416b5119328c16202a3fc719179d79e34763ff929dee8afb340ef9c1ea79b6d1`.
- Apply and verification receipts now carry a canonical
  `receiptEvidenceSha256` over the complete receipt evidence. Runtime validation
  checks both state fingerprints, action-set/state binding, receipt path/kind,
  full evidence digest, verification payload, and rollback status. The public
  `verify` seam accepts either receipt kind without reading or trusting the
  apply receipt when a verification receipt is supplied. A dedicated public
  RED proved an intact verification receipt initially became incomplete after
  apply-receipt tampering; the corrected verifier permits only that exact
  receipt-bound state-sync condition after all content, recovery, action,
  state, and evidence checks pass. Tampering either supplied receipt fails
  closed.
- Final review strengthened the anchor beyond the self-recomputable receipt
  digest. The state-persisted verified action-set digest now also binds the
  before-state fingerprint, complete verification result, rollback status,
  apply and verification receipt paths, and completion status. Public tests
  reseal syntactically valid apply and verification receipts after changing
  each before fingerprint, verification result, or rollback status; every
  case fails against the state anchor.
- An explicit `projectContract` marker is treated as owned schema evidence.
  Known markers must match their exact declared target; an unknown/future
  marker such as `3` is `baseline_unsupported`, blocks planning, and produces
  zero configuration action instead of being downgraded through the unmarked
  v1 subset. Unrelated user-owned settings without that marker remain
  preserved.
- Fresh focused GREEN: project-refresh 42/42 and Project Refresh Impact 10/10.
  Release generation remains blocked pending task 9.6 complete source checks
  and renewed independent Standards/Spec review.
