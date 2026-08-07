## Target State

An established DevFlow project can be inspected, planned, explicitly refreshed,
verified, and rolled back through one versioned project-refresh engine. The
existing `dev-flow-refresh` Skill remains the human-facing orchestrator, while
the existing `plugin_project_migration.py` CLI becomes the only project writer.
Every future DevFlow release must prove whether project-refresh behavior changed
and package matching migration coverage before promotion.

## Scope / Non-Goals

The approved implementation scope is limited to DevFlow development source,
tests, project-control-plane guidance, this OpenSpec change, and DevFlow state.
Generated `plugins/dev-flow/**` becomes writable only after a separate release-
sync approval. Installed cache refresh, applying refresh to a consumer project,
merging `AGENTS.md.generated`, legacy cleanup, dependency changes, publication,
archive, commit, push, and PR creation remain separate Human Gates.

On 2026-08-07 the user resolved a narrower follow-through gate after pre-submit
review: source repair, generated `plugins/dev-flow/**`, exact direct
`origin/main` submission, and refresh/readback of only
`dev-flow@cy-codex-skills` are authorized in dependency order. Consumer-project
apply, broad updater actions, AGENTS merge, legacy cleanup, dependency changes,
archive, PR, publication, and force-push remain closed.

No second migration CLI, arbitrary migration code loaded from manifests,
automatic project discovery write, active `AGENTS.md` overwrite, secret-bearing
backup, or production dependency is in scope.

## Completion Contract

Completion requires all dependency-ordered tasks below, fresh focused and broad
source tests, strict OpenSpec and workflow validation, generated-release parity,
the supported-version fixture matrix, release-target Plugin Eval, diff review,
and durable evidence. A plan, partial safe-subset apply, development-path Plugin
Eval, command exit code alone, or unresolved manual action is not completion.

## Approved Development Write Set

Before the release-sync gate, implementation may modify only these exact
development paths (new files are marked `new`):

- contract and immutable fixtures:
  `dev/plugins/dev-flow/.codex-plugin/project-migration.json`,
  `dev/plugins/dev-flow/assets/project-refresh/config-v1.json` (new),
  `dev/plugins/dev-flow/assets/project-refresh/config-v2.json` (new),
  `dev/plugins/dev-flow/fixtures/project-refresh/manifest.json` (new),
  `dev/plugins/dev-flow/fixtures/project-refresh/current.json` (new),
  `dev/plugins/dev-flow/fixtures/project-refresh/current-v2.json` (new),
  `dev/plugins/dev-flow/fixtures/project-refresh/legacy-root-selection.json`
  (new),
  `dev/plugins/dev-flow/fixtures/project-refresh/legacy-workflow-selection.json`
  (new),
  `dev/plugins/dev-flow/fixtures/project-refresh/legacy-preserve-settings.json`
  (new), and
  `dev/plugins/dev-flow/fixtures/project-refresh/legacy-conflicting-aliases.json`
  (new);
- schemas: `dev/plugins/dev-flow/schemas/project-refresh-contract.schema.json`
  (new), `dev/plugins/dev-flow/schemas/project-refresh-plan.schema.json` (new),
  and `dev/plugins/dev-flow/schemas/project-refresh-receipt.schema.json` (new);
- project runtime and compatibility:
  `dev/plugins/dev-flow/scripts/workflow_project_refresh.py` (new),
  `dev/plugins/dev-flow/scripts/plugin_project_migration.py`,
  `dev/plugins/dev-flow/scripts/plugin_project_migration_check.py`,
  `dev/plugins/dev-flow/scripts/legacy_workflow_config.py`,
  `dev/plugins/dev-flow/scripts/inspect_legacy_workflow_config.py`,
  `dev/plugins/dev-flow/scripts/workflow_contract_control_plane.py`,
  `dev/plugins/dev-flow/scripts/workflow_project_skill_install.py`,
  `dev/plugins/dev-flow/scripts/workflow_project_skill_paths.py`,
  `dev/plugins/dev-flow/scripts/workflow_planning_paths.py`,
  `dev/plugins/dev-flow/scripts/workflow_scaffold.py`,
  `dev/plugins/dev-flow/scripts/scaffold_workflow.py`,
  `dev/plugins/dev-flow/scripts/workflow_validate.py`,
  `dev/plugins/dev-flow/scripts/workflow_doctor.py`, and
  `dev/plugins/dev-flow/scripts/doctor_workflow.py`;
- release and update gates:
  `dev/plugins/dev-flow/.codex-plugin/release-sync.json`,
  `dev/plugins/dev-flow/scripts/workflow_release_sync.py`,
  `dev/plugins/dev-flow/scripts/workflow_release_verification.py`,
  `dev/plugins/dev-flow/scripts/release_promotion_gate.py`,
  `dev/plugins/dev-flow/scripts/sync_release_assets.py`,
  `dev/plugins/dev-flow/scripts/verify_release_runtime.py`,
  `dev/plugins/dev-flow/scripts/codex_auto_update_plugins_skills.py`,
  `dev/scripts/run_devflow_prepromotion_tests.py`, and
  `dev/scripts/codex_auto_update_plugins_skills.py`;
- Skills and guidance:
  `dev/plugins/dev-flow/skills/dev-flow-refresh/SKILL.md`,
  `dev/plugins/dev-flow/skills/dev-flow-refresh/references/project-refresh.md`,
  `dev/plugins/dev-flow/skills/plugin-project-migration/SKILL.md`,
  `dev/plugins/dev-flow/skills/ai-native-tech-plan/SKILL.md`,
  `dev/plugins/dev-flow/skills/change-plan/SKILL.md`,
  `dev/plugins/dev-flow/skills/execute-task/SKILL.md`,
  `dev/plugins/dev-flow/skills/verify-and-archive/SKILL.md`,
  `dev/plugins/dev-flow/README.md`, root `AGENTS.md`,
  `ENGINEERING_POLICY.md`, `REVIEW_CHECKLIST.md`, and `TASK_LEDGER.md`;
- maintained templates:
  `dev/plugins/dev-flow/assets/templates/AGENTS.md.template`,
  `dev/plugins/dev-flow/assets/templates/ENGINEERING_POLICY.md.template`,
  `dev/plugins/dev-flow/assets/templates/EVIDENCE_TEMPLATE.md.template`,
  `dev/plugins/dev-flow/assets/templates/REVIEW_CHECKLIST.md.template`,
  `dev/plugins/dev-flow/assets/templates/OPENSPEC_DESIGN.md.template`, and
  `dev/plugins/dev-flow/assets/templates/OPENSPEC_TASKS.md.template`;
- tests: `dev/plugins/dev-flow/tests/test_project_refresh.py` (new),
  `dev/plugins/dev-flow/tests/test_legacy_workflow_config.py`,
  `dev/plugins/dev-flow/tests/test_methodology.py`,
  `dev/plugins/dev-flow/tests/test_plugin_project_migration.py`,
  `dev/plugins/dev-flow/tests/test_project_orchestrator.py`,
  `dev/plugins/dev-flow/tests/test_planning_ownership.py`,
  `dev/plugins/dev-flow/tests/test_release_promotion_targets.py`,
  `dev/plugins/dev-flow/tests/test_release_sync.py`,
  `dev/plugins/dev-flow/tests/test_release_smoke.py`,
  `dev/plugins/dev-flow/tests/test_packaged_runtime.py`, and
  `dev/plugins/dev-flow/tests/test_runtime_gates.py`;
- canonical planning and proof:
  `openspec/changes/add-versioned-devflow-project-refresh/.openspec.yaml`,
  `proposal.md`, `design.md`, `tasks.md`, both delta-spec files, and new
  `evidence/implementation.md`, `evidence/verification.md`, and
  `evidence/plugin-eval.md` below that change;
- DevFlow execution state: `.planning/devflow/STATE.md`,
  `.planning/devflow/checkpoints/2026-08-06-planned-add-versioned-devflow-project-refresh.md`,
  `.planning/devflow/checkpoints/2026-08-06-source-verified-add-versioned-devflow-project-refresh.md`
  (new), and
  `.planning/devflow/checkpoints/2026-08-06-verification_passed-add-versioned-devflow-project-refresh.md`
  (new), and
  `.planning/devflow/checkpoints/2026-08-07-reopened-add-versioned-devflow-project-refresh.md`
  (new),
  `.planning/devflow/checkpoints/2026-08-07-project-refresh-corrective-green.md`
  (new),
  `.planning/devflow/checkpoints/2026-08-07-delivered-add-versioned-devflow-project-refresh.md`
  (new), and
  `.planning/devflow/release-verification/dev-flow.json`.

The main agent owns all listed paths. Any required path outside this set,
dependency change, public contract expansion, ambiguous deletion, or external
effect stops at `BLOCKED_AWAITING_HUMAN` after read-only diagnosis.

## 1. Approval and RED Baseline

- [x] 1.1 After explicit plan approval, reread the approved OpenSpec artifacts and apply instructions; record source/release/cache identities, project and migration schema heads, the unrelated-worktree baseline, exact write set, Project Refresh Impact baseline, and Goal Gate disposition before production edits.
- [x] 1.2 Add RED planner tests for current projects, missing adoption markers, clean supported legacy configurations, conflicting legacy aliases, unknown-setting preservation, redaction, absent configuration in an adopted project, non-Git projects, and untracked, dirty, unreadable, symlinked, or non-regular configuration targets.
- [x] 1.3 Add RED registry and sealed-plan tests for unique version paths, gaps, forks, cycles, duplicate IDs, ambiguous baselines, deterministic digests, managed-input staleness, source/contract staleness, exact write sets, and unrelated WIP tolerance.
- [x] 1.4 Add RED transaction and compatibility tests proving conflict preflight performs zero writes, promotion or verification failure restores every path, state advances last, post-apply edits block rollback, ordinary legacy apply lacks configuration authority, and existing hook/updater/no-subcommand JSON remains compatible.
- [x] 1.5 Add RED release-gate tests for immutable configuration targets, required schema/migration/refresh-revision changes, source/release/cache contract mismatches, packaged CLI and Skill-reference drift, and the supported-version fixture matrix.

## 2. Versioned Contract and Pure Planner

- [x] 2.1 Upgrade `project-migration.json` to a validated versioned contract that separates plugin release, engine schema, project workflow schema, and refresh-contract identity while preserving reads of current v1 migration state.
- [x] 2.2 Implement the stable migration registry, trusted baseline detection, DevFlow adoption detection, unique-path resolution, and fail-closed validation without loading executable code from the manifest.
- [x] 2.3 Implement pure typed migration steps for recognized legacy `.dev-flow.json` shapes: remove only retired selectors, set `workflow.mode` to `full-openspec`, preserve every unrelated JSON value and type exactly, redact values, and classify unsafe inputs as manual-only.
- [x] 2.4 Build the deterministic one-project planner with normalized actions, dependencies, exact managed read/write sets, before fingerprints, named authorizations, preserved/manual paths, verification requirements, and canonical `planSha256`.
- [x] 2.5 Make current projects and non-adopted directories genuinely no-write, and ensure stale managed inputs invalidate a plan while unrelated worktree changes remain reported but do not invalidate it.

## 3. Transaction, Verification, Rollback, and CLI

- [x] 3.1 Implement a single finite-operation executor with complete preflight for path escape, duplicate or parent/child overlap, untrusted symlink ancestry, ownership ambiguity, before-fingerprint drift, dependency closure, staging, and rollback completeness before the first project write.
- [x] 3.2 Implement plan-bound explicit apply with named authorization, isolated staging, ordered promotion, state-last advancement, structured apply/verification receipts, and incomplete status for unresolved manual actions or safe-subset applies.
- [x] 3.3 Implement fresh post-apply verification across configuration schema, project migration sync, managed-path readback, workflow validation, cache-drift diagnosis, and AGENTS disposition; automatically restore the full selected transaction on promotion or verification failure.
- [x] 3.4 Implement explicit receipt-bound rollback, reverse-order restoration, after-fingerprint protection against overwriting later edits, rollback receipts, and distinct `verification_failed_rolled_back` and `rollback_failed` outcomes.
- [x] 3.5 Add `plan`, `apply`, `verify`, and `rollback` subcommands to the existing `plugin_project_migration.py` interface with stable JSON, status, next action, and exit classes; preserve read-only no-subcommand behavior and route legacy `--apply` through the same engine without workflow-configuration authority.
- [x] 3.6 Route existing managed-skill, missing-control-plane, and verified-tree writes through the central executor so there is no second project writer; retain read-only hook, updater, and operator summaries through compatibility adapters.

## 4. Skill, Guidance, and Protected Project Surfaces

- [x] 4.1 Update `dev-flow-refresh` and its project-refresh reference to orchestrate plugin/cache verification first, then per-project plan, explicit authorization, apply, fresh verify, rollback guidance, and aggregate evidence without duplicating engine logic.
- [x] 4.2 Implement semantic AGENTS guidance comparison: current guidance is unchanged, stale guidance can produce only a non-conflicting `AGENTS.md.generated` candidate, active `AGENTS.md` is never overwritten, and an existing divergent candidate blocks candidate creation without data loss.
- [x] 4.3 Keep legacy `.codex/skills`, custom official-skill copies, historical planning data, non-symlink managed targets, and ambiguous project content report-only; no refresh path deletes, overwrites, or silently adopts them.
- [x] 4.4 Update root and template workflow policy, engineering policy, review guidance, OpenSpec planning templates, README, CLI help, and examples so every project-facing DevFlow change records `changed`, `verified-unchanged`, or `not-applicable` Project Refresh Impact with evidence.
- [x] 4.5 Document the exact authorization boundaries, plan/apply/verify/rollback recovery prompts, non-Git limitations, receipt handling, restart-required reporting, and the rule that unresolved manual work prevents a refreshed/current claim.

## 5. Executable Future-Update Gate

- [x] 5.1 Implement a deterministic refresh-impact analyzer covering canonical config targets/readers, migration registry, project state, AGENTS guidance, control-plane templates, local-skill inventory, dependency layout, engine behavior, fixtures, and Skill contract.
- [x] 5.2 Integrate the analyzer into pre-promotion and release verification so stale or missing impact evidence, immutable-target mutation, a config-sensitive change without a schema migration, or tracked-byte drift without a refresh-contract revision fails closed.
- [x] 5.3 Package the manifest, registry, runtime, existing CLI wrapper, Skill/reference, contract metadata, and fixture matrix as one release unit and verify development/release identity and every supported schema-to-head path.
- [x] 5.4 Add structured source/release/cache readback fields to diagnostics and the updater without granting cache mutation; registration-only success must not satisfy freshness.
- [x] 5.5 Record the final Project Refresh Impact, inspected surfaces, schema decision, contract identity, migration path coverage, compatibility result, and residual risk in this change's evidence.

## 6. Source Verification and Review

- [x] 6.1 Run all focused legacy-config, project-refresh, project-migration, orchestrator, hook/updater, scaffold/config, dependency, release-impact, runtime, and packaging tests from the design's exact validation commands and record counts and outputs.
- [x] 6.2 Run the complete DevFlow development test suite, workflow-state validator, strict validation for this change and all OpenSpec items, AI-plan lint, and `git diff --check` from a fresh tree state.
- [x] 6.3 Perform correctness, scope, compatibility, security/redaction, transaction/rollback, test-quality, generated-artifact, and incidental-finding review; resolve all blocking findings and register every authorized deferral.
- [x] 6.4 Inspect the complete development diff against the approved write set, prove the unrelated Git-transport evidence edit remains untouched, and update tasks, evidence, state, and a source-verification checkpoint without claiming release parity.

## 7. Generated Release Human Gate and Verification

- [x] 7.1 After source verification passes, set both workflow statuses to `awaiting_human`, record the exact generated `plugins/dev-flow/**` write set and promotion command, and stop for separate release-sync authorization.
- [x] 7.2 If and only if release sync is authorized, generate `plugins/dev-flow/**` through the repository release tooling, never by direct edits, and record source-to-release file identity and manifest provenance.
- [x] 7.3 Rerun focused and broad tests against source and generated release, packaged-runtime verification, Skill validation, supported-version migration fixtures, strict OpenSpec/workflow checks, and release-target `plugin-eval analyze`; record score, findings, fixes, and any explicitly approved deferral.
- [x] 7.4 Run the local Codex reference updater in read-only JSON mode and report source/release drift, named installed-cache freshness, and project-local link drift; do not refresh a cache or apply a consumer-project migration without its own authorization.

## 8. Final Verification and Handoff

- [x] 8.1 Inspect final status and diff, verify only authorized paths changed, rerun any check invalidated by late edits, and record exact commands, results, receipts, residual risks, rollback instructions, and restart requirements.
- [x] 8.2 Mark implementation and verification complete only when every required source and authorized release task is checked, no unresolved `BLOCKED_AWAITING_HUMAN` finding remains inside the authorized scope, and fresh evidence satisfies the Completion Contract.
- [x] 8.3 Update `.planning/devflow/STATE.md` and create the final verification checkpoint; leave cache refresh, consumer-project apply, AGENTS merge, legacy cleanup, archive, commit, push, PR, and publication closed unless separately authorized.

## 9. Pre-submit Systemic Repair and Authorized Delivery

- [x] 9.1 Record the 2026-08-07 review findings, user authorization, active Goal binding, confirmed public TDD seams, exact repair write set, unrelated Git-transport diff digest, and paused Goal-lifecycle change; reopen this change and DevFlow state without deleting or rewriting the paused change's artifacts.
- [x] 9.2 Add public-seam RED tests proving a manifest head greater than 1 drives current-schema detection, create-if-absent target bytes, and staged verification, while trusted configuration/state schema disagreement returns `baseline_ambiguous` with zero configuration or state-sync actions.
- [x] 9.3 Implement the smallest complete planner/runtime correction that derives schema and target bytes from the validated contract, distinguishes configuration evidence from state evidence, executes every supported older-schema path through the current head while preserving unrelated settings, and makes task 9.2 GREEN.
- [x] 9.4 Add public-seam RED tests proving manifest-only adapter changes require a refresh-contract revision and proving both apply and verification receipts independently bind and runtime-validate project schema, migration path, actions/fingerprints, authorizations, changed/preserved paths, state fingerprints, action-set identity, verification, and rollback status.
- [x] 9.5 Implement the complete impact-analyzer, receipt, and published-schema corrections; because the planner change is configuration-sensitive, add immutable config target v2, advance project schema head to 2, add the unique v1-to-v2 pure step and supported fixtures, advance Project Refresh Impact revision/evidence as `advanced`, and make tasks 9.3–9.4 GREEN.
- [x] 9.6 Run focused and complete source verification, strict current/all OpenSpec, workflow validation, AI-plan lint, `git diff --check`, scope/digest checks, and independent Standards/Spec reviews; resolve every blocking finding and update durable evidence before release generation.
- [x] 9.7 Regenerate only `plugins/dev-flow/**` through the authorized promotion gate, then rerun source/release/runtime parity, packaged tests, supported fixtures, Skill validation, and release-target Plugin Eval with zero failures; record score and dispositions.
- [ ] 9.8 Force-add only this ignored OpenSpec change plus exact intended source/release/control-plane paths, exclude the unrelated Git-transport evidence and every paused Goal-lifecycle artifact, commit directly on `main`, push and read back `origin/main`, refresh only `dev-flow@cy-codex-skills`, prove byte-level source/release/cache parity, and close state without archive, PR, publication, consumer migration, cleanup, or broad update.
