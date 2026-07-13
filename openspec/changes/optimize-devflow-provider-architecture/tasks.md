# DevFlow Provider Architecture Implementation Plan

> **For agentic workers:** Execute one approved Capability Slice at a time.
> Use the selected profile's `test-first-execution` mapping for behavior
> changes, and run fresh `completion-proof` verification before checking any
> slice as done. Subagent work requires an approved Agent Task Contract and
> disjoint write sets.

**Goal:** Make DevFlow Core independently usable, add deterministic optional
methodology and roadmap providers, eliminate DevFlow/GSD planning-path
collisions, and establish measured quality/cost gates without changing the
default to Matt prematurely.

**Architecture:** A machine-readable provider registry feeds one deep
`resolve -> diagnose -> activate` facade. OpenSpec and DevFlow keep canonical
planning/evidence ownership, external methodology providers supply optional
capabilities, and GSD owns only its selected root roadmap namespace.

**Tech Stack:** Python 3.12 standard library, JSON, Markdown/OpenSpec, Codex
plugin manifests/skills/hooks, unittest, existing release runtime packaging,
Plugin Eval.

## Global Constraints

- Primary edits belong under `dev/plugins/dev-flow`; release files are generated
  through the existing sync/package flow.
- Do not add production dependencies or change the `dev-flow` plugin id.
- Do not install/update providers, trust hooks, mutate real projects, clean
  legacy files, archive, release, commit, push, or create a PR without explicit
  user authorization.
- OpenSpec, Task Ledger, DevFlow evidence, review, archive, and release gates
  remain canonical in every profile.
- `--strict` keeps its developer-helper meaning.
- `lean-matt` remains opt-in during this change.
- Every behavior task records RED and GREEN command evidence; every migration
  task proves dry-run zero-write and apply idempotence.

## Skill Routing Ledger

- kind: architecture / compatibility / workflow-repair
- workflow mode: Full OpenSpec
- artifact-status: final
- capability-research: used — upstream/local/runtime evidence is recorded in
  `proposal.md` and `design.md`
- decision-resolution: used — three architectures were compared and the
  provider/profile boundary was approved as the basis for this plan
- decision-grilling: skipped — Open Questions are empty
- implementation-planning: used — this file is the canonical implementation
  plan
- architecture-guidance: used — provider-local activation, capability routing,
  and cleanup ownership are resolved in `design.md`
- OpenSpec: required and used
- GSD planning: skipped — GSD is the optional provider being repaired and its
  current repository state is inconsistent

## Completion Contract

- [x] C.1 `core + none` is fully ready with Superpowers, Matt, and GSD absent.
- [x] C.2 Provider selection is deterministic, single-source, profile-scoped,
      and cannot mix cache roots or infer hooks from version alone.
- [x] C.3 Lean and strict adapters satisfy their declared capability maps while
      DevFlow retains native completion proof and canonical ownership.
- [x] C.4 GSD affects only roadmap readiness and writes no path also written by
      DevFlow.
- [x] C.5 Legacy inference, migration, switching, and rollback are dry-run-first,
      content-driven, idempotent, and non-destructive.
- [x] C.6 DevFlow instruction/static budget is at least 20% below the captured
      baseline or a quality-backed blocker and residual risk are recorded.
- [x] C.7 Dev/release tests, OpenSpec validation, runtime verification, release
      sync, release-target Plugin Eval, and local-reference dry-run pass.
- [x] C.8 The benchmark corpus exists and can reproduce profile comparisons;
      no default-switch claim is made without the full outcome gate.
- [x] C.9 Core gates, routing ledgers, generated guidance, and plan lint use
      stable capability ids rather than Superpowers or Matt skill names.
- [x] C.10 Unselected providers remain advisory and action-free in every
      summary, updater, activation, and fallback surface.
- [x] C.11 Lean Matt activation installs and resolves its allowlist from the
      current project's `.agents/skills/` tree.
- [x] C.12 Explicit provider cleanup is dry-run-first and removes only verified
      managed symlinks while preserving all other content.
- [x] C.13 Superpowers `6.1.1`, dev/release parity, installed cache freshness,
      and the current project's `core + none` state are freshly verified.

## 1. Baseline and Characterization

**Files:**

- Create: `dev/plugins/dev-flow/tests/test_provider_profiles.py`
- Modify: `dev/plugins/dev-flow/tests/dependency_support.py`
- Modify: `dev/plugins/dev-flow/tests/test_dependencies.py`
- Modify: `dev/plugins/dev-flow/tests/test_runtime_gates.py`
- Modify: `dev/plugins/dev-flow/tests/test_release_smoke.py`

**Produces:** failing tests for the new profile/readiness/source/hook contract,
plus characterization tests for current dry-run, user-file protection,
OpenSpec requirement, explicit authorization, and release-target behavior.

- [x] 1.1 Capture the current dependency JSON, provider roots, GSD probe output,
      state schemas, release Plugin Eval `86/B` budget metrics, and exact command
      versions in the change evidence record.
- [x] 1.2 Add fixture builders for profile config, hookless and hook-declaring
      Superpowers distributions, pinned Matt skill packs, multiple provider
      roots, GSD available/drifted/missing states, and mixed planning schemas.
- [x] 1.3 Write RED tests proving `core + none` must pass without external
      providers and must plan no external installer/link/update commands.
- [x] 1.4 Write RED tests for lean complete/partial/coexisting providers,
      strict hookless curated `6.1.1`, declared-hook trust, and ambiguous source
      behavior.
- [x] 1.5 Write RED tests separating `coreReady`, `methodologyReady`, and
      `roadmapReady`, including unselected GSD drift.
- [x] 1.6 Preserve GREEN characterization for OpenSpec-required behavior,
      dry-run zero-write, user-owned skills/conflicts, explicit apply gates,
      current `--strict` meaning, and release Eval target preference.
- [x] 1.7 Run the new tests and record the expected failing assertions before
      implementation.

**Validation:**

```bash
python3.12 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_provider_profiles.py' -v
python3.12 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_dependencies.py' -v
```

**Done when:** the intended new contract fails for specific missing behavior,
while preserved safety characterization remains green.

## 2. Provider Registry and Core Facade

**Files:**

- Create: `dev/plugins/dev-flow/docs/provider_profiles.json`
- Create: `dev/plugins/dev-flow/docs/provider_side_effect_policy.json`
- Create: `dev/plugins/dev-flow/scripts/workflow_provider_profiles.py`
- Create: `dev/plugins/dev-flow/scripts/workflow_provider_registry.py`
- Modify: `dev/plugins/dev-flow/scripts/workflow_mode_routing.py`
- Modify: `dev/plugins/dev-flow/scripts/workflow_lib.py`
- Modify: `dev/plugins/dev-flow/docs/dependency-provenance.json`
- Test: `dev/plugins/dev-flow/tests/test_provider_profiles.py`

**Interfaces:**

- Produces: `resolve_provider_selection(repo, codex_home, config) -> dict`
- Produces: `diagnose_provider_selection(selection, repo, codex_home) -> dict`
- Produces: `provider_activation_plan(selection, repo, codex_home) -> dict`
- Result fields include explicit/effective selection, selection source,
  capabilities, source identity, side effects, `coreReady`,
  `methodologyReady`, `roadmapReady`, conflicts, blockers, and dry-run actions.

- [x] 2.1 Add registry/schema validation tests for stable capability IDs,
      the complete trigger/requiredness/core-lean-strict mapping/evidence/
      side-effect/fallback table, allowed/excluded skills, source selectors,
      roadmap bindings, and invalid combinations.
- [x] 2.2 Implement `provider_profiles.json` for `core`, `lean-matt`,
      `strict-superpowers`, `none`, and `gsd` without embedding canonical
      evidence completion in provider availability.
- [x] 2.3 Implement the side-effect classes and default-deny authorization
      policy for DevFlow-controlled routes.
- [x] 2.4 Extend `.dev-flow.json` reading with canonical
      `methodology_profile`, `roadmap_provider`, `provider_selectors`, and
      `roadmap_bindings` keys plus documented aliases, keeping workflow mode and
      `--strict` semantics unchanged.
- [x] 2.5 Implement the provider facade and deterministic status schema.
- [x] 2.6 Add `devflow-native` mappings that preserve OpenSpec planning,
      TDD-evidence, review, completion-proof, archive, release, and goal routing
      without any external methodology dependency.
- [x] 2.7 Run registry/facade tests to GREEN and confirm no installer or
      workspace mutation occurs during resolution/diagnosis.

**Validation:**

```bash
python3.12 -m unittest dev/plugins/dev-flow/tests/test_provider_profiles.py -v
python3.12 -m unittest dev/plugins/dev-flow/tests/test_runtime_gates.py -v
```

## 3. Methodology Adapters and Source Binding

**Files:**

- Create: `dev/plugins/dev-flow/scripts/workflow_provider_activation.py`
- Modify: `dev/plugins/dev-flow/scripts/workflow_dependency_plugin_checks.py`
- Modify: `dev/plugins/dev-flow/scripts/workflow_project_skill_install.py`
- Modify: `dev/plugins/dev-flow/scripts/workflow_dependency_catalog.py`
- Modify: `dev/plugins/dev-flow/docs/superpowers_gate_matrix.json`
- Modify: `dev/plugins/dev-flow/docs/artifact-ownership.md`
- Test: `dev/plugins/dev-flow/tests/test_provider_profiles.py`
- Test: `dev/plugins/dev-flow/tests/test_dependencies.py`
- Test: `dev/plugins/dev-flow/tests/test_superpowers_artifact_mapping.py`

**Consumes:** provider registry and selected profile.

**Produces:** one bound source root/lock and profile-specific capability map.

- [x] 3.1 Write RED tests that reject mixed/multiple provider roots, unverifiable
      Matt sources, and version-only hook requirements.
- [x] 3.2 Implement strict Superpowers source precedence, manifest-driven hook
      checks, the design's exact brainstorming/planning/TDD/debugging/review/
      completion/execution/worktree/finish mappings and conditional rules, and
      compatibility status without auto-trust.
- [x] 3.3 Implement Matt source/ref/hash locking and only the approved
      `grilling`, `tdd`, `diagnosing-bugs`, `code-review`, `codebase-design`, and
      `domain-modeling` mappings.
- [x] 3.4 Assert that Matt control-plane skills are excluded from implicit
      routing and that `prototype` and `grill-with-docs` require their explicit
      DevFlow mode/write-set gates.
- [x] 3.5 Keep provider draft artifacts non-canonical and preserve the existing
      promotion contract through provider-neutral terminology and a compatible
      Superpowers shim.
- [x] 3.6 Persist generated provider source identity and selected skill hashes
      in `.planning/devflow/providers.lock.json` only during explicitly
      approved activation/migration; test selector -> matching lock -> unique
      discovery precedence, stale locks, `--provider-source`, and
      `--persist-provider-selection`; diagnosis remains read-only.
- [x] 3.7 Run adapter/source/hook/artifact tests to GREEN.

**Validation:**

```bash
python3.12 -m unittest dev/plugins/dev-flow/tests/test_provider_profiles.py dev/plugins/dev-flow/tests/test_dependencies.py dev/plugins/dev-flow/tests/test_superpowers_artifact_mapping.py -v
```

## 4. Profile-Scoped Dependency, Activation, Updater, and Goal Diagnostics

**Files:**

- Modify: `dev/plugins/dev-flow/scripts/workflow_dependencies.py`
- Modify: `dev/plugins/dev-flow/scripts/workflow_dependency_checks.py`
- Modify: `dev/plugins/dev-flow/scripts/workflow_dependency_provenance.py`
- Modify: `dev/plugins/dev-flow/scripts/workflow_project_activation.py`
- Modify: `dev/plugins/dev-flow/scripts/activate_project_dependencies.py`
- Modify: `dev/plugins/dev-flow/scripts/check_dependencies.py`
- Modify: `dev/plugins/dev-flow/scripts/codex_auto_update_plugins_skills.py`
- Modify: `dev/plugins/dev-flow/scripts/workflow_context_health_goal.py`
- Modify: `dev/plugins/dev-flow/docs/dependency-provenance.json`
- Test: `dev/plugins/dev-flow/tests/test_dependencies.py`

- [x] 4.1 Write RED profile-by-availability matrix tests covering all three
      methodology profiles, both roadmap providers, unselected installed
      providers, unknown config, partial skills, source ambiguity, GSD drift,
      and Plugin Eval release-only gating.
- [x] 4.2 Move requiredness from static provider identity to resolved
      capabilities while keeping OpenSpec core-required.
- [x] 4.3 Return separate core/methodology/roadmap/goal/release readiness and
      exact per-capability next actions in JSON and human output.
- [x] 4.4 Make activation and updater plan only selected dependencies; retain
      explicit options for separately maintaining an unselected component.
- [x] 4.5 Stop unconditional GSD installation and project skill activation.
- [x] 4.6 Add `define-goal` provenance and on-demand readiness without making it
      an ordinary core blocker or calling goal tools from scripts.
- [x] 4.7 Preserve `--strict` developer-helper compatibility and add a separate
      explicit methodology override plus repeated provider-source override;
      persistence requires both `--apply` and
      `--persist-provider-selection`.
- [x] 4.8 Prove every matrix cell has exact status, requiredness, selected
      provider, capabilities, next action, and zero unintended commands.

**Validation:**

```bash
python3.12 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_dependencies.py' -v
python3.12 dev/plugins/dev-flow/scripts/check_dependencies.py --plugin-root dev/plugins/dev-flow --repo . --codex-home "${CODEX_HOME:-$HOME/.codex}" --json
```

## 5. Roadmap Ownership, Namespaced State, and Reversible Migration

**Files:**

- Create: `dev/plugins/dev-flow/scripts/workflow_planning_paths.py`
- Create: `dev/plugins/dev-flow/scripts/workflow_roadmap_provider.py`
- Modify: `dev/plugins/dev-flow/scripts/workflow_state.py`
- Modify: `dev/plugins/dev-flow/scripts/workflow_verification.py`
- Modify: `dev/plugins/dev-flow/scripts/workflow_scaffold.py`
- Modify: `dev/plugins/dev-flow/scripts/workflow_validate.py`
- Modify: `dev/plugins/dev-flow/scripts/workflow_archive_policy.py`
- Modify: `dev/plugins/dev-flow/scripts/workflow_detect.py`
- Modify: `dev/plugins/dev-flow/scripts/workflow_hooks.py`
- Modify: `dev/plugins/dev-flow/scripts/workflow_checkpoint_create.py`
- Modify: `dev/plugins/dev-flow/scripts/workflow_checkpoint_validate.py`
- Modify: `dev/plugins/dev-flow/scripts/workflow_compact_resolve.py`
- Modify: `dev/plugins/dev-flow/scripts/workflow_compact_result.py`
- Modify: `dev/plugins/dev-flow/scripts/record_context_health_disposition.py`
- Modify: `dev/plugins/dev-flow/scripts/workflow_context_health_repo.py`
- Modify: `dev/plugins/dev-flow/scripts/workflow_context_health_report.py`
- Modify: `dev/plugins/dev-flow/scripts/workflow_context_health_sessions.py`
- Modify: `dev/plugins/dev-flow/scripts/workflow_inspect.py`
- Modify: `dev/plugins/dev-flow/scripts/record_task_evidence.py`
- Modify: `dev/plugins/dev-flow/scripts/plugin_project_migration.py`
- Modify: `dev/plugins/dev-flow/.codex-plugin/project-migration.json`
- Test: `dev/plugins/dev-flow/tests/test_plugin_project_migration.py`
- Test: `dev/plugins/dev-flow/tests/test_archive_policy.py`
- Test: `dev/plugins/dev-flow/tests/test_checkpoint_compact_contract.py`
- Test: `dev/plugins/dev-flow/tests/test_compact_recovery.py`
- Test: `dev/plugins/dev-flow/tests/test_context_health.py`

**Produces:** `.planning/devflow/**` sole-writer paths, read-only GSD adapter,
content-driven inference, dry-run migration report, snapshot, and rollback.

- [x] 5.1 Write RED tests for namespaced state/evidence/checkpoint/context/codebase
      paths, GSD-root write refusal, case-insensitive collision prevention,
      phase binding, tracking-policy diagnostics, and core setup without fake
      roadmap/phase artifacts.
- [x] 5.2 Implement one central DevFlow planning path/ownership resolver and
      remove direct hard-coded DevFlow writes to root GSD namespaces.
- [x] 5.3 Move new DevFlow state, verification, checkpoint, compact,
      context-health, and brownfield-map output under `.planning/devflow/**`.
- [x] 5.4 Implement root state marker guards: namespaced first, bounded legacy
      `workflow_version` read-only compatibility, `migration_required` before
      any new write, post-sunset no-read/no-write behavior, never parse/write
      `gsd_state_version`, and stop on mixed markers.
- [x] 5.5 Implement content-driven GSD inference; installed runtime/skills/agents
      alone are never selection evidence.
- [x] 5.6 Make OpenSpec verification the behavior truth and require GSD
      verification only for an active `.dev-flow.json` change-to-phase binding;
      test create/update/inactivate/archive, missing/renamed phase, provider
      switch, and blocked phase transition lifecycle.
- [x] 5.7 Extend migration dry-run with hashes, owners, action classes,
      conflicts, tracked/partially-tracked/local-only status, a planned (not
      created) snapshot/rollback plan, and separate file vs dependency
      approvals.
- [x] 5.8 Implement explicit apply using snapshot, atomic writes, persisted
      config/lock under `.planning/devflow/providers.lock.json`, migration
      records under `.planning/devflow/provider-migration/**`, no user-file
      overwrite, no cleanup, and second-run no-op.
- [x] 5.9 Add rollback tests that restore hashes, profile, ownership, and
      readiness; prove apply failure has no partial state and post-migration
      user hash changes stop rollback; add GSD-to-core switch tests that preserve
      all GSD artifacts.
- [x] 5.10 Make partial/local tracking advisory for core and GSD
      `commit_docs: false`, but set `roadmapReady: false` when selected GSD has
      `commit_docs: true` and its required paths cannot be committed.
- [x] 5.11 Run state, checkpoint, context-health, migration, scaffold, and doctor
      tests to GREEN on both case-sensitive and simulated case-insensitive
      fixtures.

**Validation:**

```bash
python3.12 -m unittest dev/plugins/dev-flow/tests/test_plugin_project_migration.py dev/plugins/dev-flow/tests/test_checkpoint_compact_contract.py dev/plugins/dev-flow/tests/test_context_health.py -v
python3.12 dev/plugins/dev-flow/scripts/plugin_project_migration.py --repo . --plugin-root dev/plugins/dev-flow --json
python3.12 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo . --json
```

## 6. Routing, Guidance, and Context-Budget Cleanup

**Files:**

- Modify: `dev/plugins/dev-flow/docs/routing.matrix.json`
- Create: `dev/plugins/dev-flow/docs/provider-profile-migration.md`
- Modify: `dev/plugins/dev-flow/README.md`
- Modify: `dev/plugins/dev-flow/assets/templates/AGENTS.md.template`
- Modify: `dev/plugins/dev-flow/assets/templates/ENGINEERING_POLICY.md.template`
- Modify: `dev/plugins/dev-flow/assets/templates/TASK_LEDGER.md.template`
- Modify: `dev/plugins/dev-flow/skills/project-orchestrator/SKILL.md`
- Modify: `dev/plugins/dev-flow/skills/feature-intake/SKILL.md`
- Modify: `dev/plugins/dev-flow/skills/ai-native-tech-plan/SKILL.md`
- Modify: `dev/plugins/dev-flow/skills/change-plan/SKILL.md`
- Modify: `dev/plugins/dev-flow/skills/execute-task/SKILL.md`
- Modify: `dev/plugins/dev-flow/skills/verify-and-archive/SKILL.md`
- Modify: `dev/plugins/dev-flow/skills/project-setup/SKILL.md`
- Modify: `dev/plugins/dev-flow/skills/workflow-doctor/SKILL.md`
- Test: `dev/plugins/dev-flow/tests/test_project_orchestrator.py`
- Test: `dev/plugins/dev-flow/tests/test_runtime_gates.py`

- [x] 6.1 Write RED tests that route stable capability IDs rather than
      hard-coded provider names and keep canonical ownership/side-effect rules
      intact in every profile.
- [x] 6.2 Replace duplicated Superpowers/GSD prose with concise core contracts
      and deferred provider references generated from the registry.
- [x] 6.3 Update project setup and AGENTS guidance for new `core + none`,
      profile selection, GSD suitability, `.planning/devflow/**` ownership,
      local-only tracking risk, and merge-only generated guidance.
- [x] 6.4 Preserve provider-specific details only inside adapters/reference
      docs; retain compatibility aliases where existing hooks/tests consume the
      old Superpowers matrix.
- [x] 6.5 Reassess implicit vs explicit-only skill eligibility using observed
      routing needs, then make only changes that preserve natural-language
      discovery and pass the task outcome corpus.
- [x] 6.6 Run Plugin Eval budget analysis and reduce both active and deferred
      release-target estimates at least 20% from the captured baseline, or
      record the quality-backed blocker and residual risk.
- [x] 6.7 Run routing/template/skill tests to GREEN and scan for stale universal
      `Superpowers required` / `GSD required` wording.

**Validation:**

```bash
python3.12 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py dev/plugins/dev-flow/tests/test_runtime_gates.py -v
rg -n "required.*Superpowers|required.*GSD|REQUIRED_SUPERPOWERS|REQUIRED_GSD" dev/plugins/dev-flow
```

## 7. Provider Outcome Benchmark and Quality Gate

**Files:**

- Create: `dev/plugins/dev-flow/evals/provider-profiles/README.md`
- Create: `dev/plugins/dev-flow/evals/provider-profiles/benchmark.strict-superpowers.json`
- Create: `dev/plugins/dev-flow/evals/provider-profiles/benchmark.lean-matt.json`
- Create: `dev/plugins/dev-flow/evals/provider-profiles/rubric.md`
- Create: `dev/plugins/dev-flow/evals/provider-profiles/fixtures/strict-superpowers/**`
- Create: `dev/plugins/dev-flow/evals/provider-profiles/fixtures/lean-matt/**`
- Create: `dev/plugins/dev-flow/evals/provider-profiles/results/README.md`
- Create: `dev/plugins/dev-flow/scripts/run_provider_benchmark.py`
- Create: `dev/plugins/dev-flow/scripts/aggregate_provider_benchmark.py`
- Create: `dev/plugins/dev-flow/tests/test_provider_benchmark.py`

- [x] 7.1 Generate separate strict and lean Plugin Eval configs with the ten
      fixed task IDs and machine verifier commands; mark compatibility, known
      bug, risky refactor, and premature completion as high-risk.
- [x] 7.2 Create isolated fixtures with minimal Codex config and pinned provider
      skills; add a parity test requiring identical base hashes outside the
      allowlisted provider config/skills/lock paths; do not inherit unrelated
      global plugins/skills or live user configuration.
- [x] 7.3 Record neutral prompts, repository/prompt/provider hashes, randomized
      order, resource controls, mandatory actual-route evidence, and frozen
      plugin/config/fixture/oracle/Codex-binary identities rechecked around
      every model invocation.
- [x] 7.4 Implement a standard-library aggregate checker for repetitions,
      invalid runs, machine success, canonical compliance, side effects,
      telemetry coverage, paired median total-token improvement, per-class token
      degradation, aggregate tool/elapsed non-inferiority, blind review, and
      correction counts.
- [x] 7.5 Unit-test every default-switch threshold and failure reason, including
      missing telemetry and a provider installed but not routed.
- [x] 7.6 Run benchmark configuration and verifier dry-runs locally without
      spending external model budget or claiming outcome equivalence; the runner
      must show both Plugin Eval commands and three repetitions.
- [x] 7.7 Record the paid/live comparison as `skipped_with_reason` for this
      architecture release. The dry-run proves a valid randomized 60-run plan,
      zero model calls, and zero writes; `core` remains the default and
      `lean-matt` remains opt-in. A later default-switch proposal must obtain
      separate spend and blind-review authorization, execute three runs per
      profile/class, and retain hash-addressed raw evidence. Missing or
      unverifiable raw evidence continues to fail that later gate.

**Validation:**

```bash
python3.12 -m unittest dev/plugins/dev-flow/tests/test_provider_benchmark.py -v
python3.12 dev/plugins/dev-flow/scripts/run_provider_benchmark.py --plugin-root plugins/dev-flow --strict-config dev/plugins/dev-flow/evals/provider-profiles/benchmark.strict-superpowers.json --lean-config dev/plugins/dev-flow/evals/provider-profiles/benchmark.lean-matt.json --repetitions 3 --output-root .planning/devflow/evals/dry-run --dry-run
python3.12 dev/plugins/dev-flow/scripts/aggregate_provider_benchmark.py --help
```

## 8. Release, Runtime, and Local Reference Verification

**Files:**

- Modify: `dev/plugins/dev-flow/tests/test_release_sync.py`
- Modify: `dev/plugins/dev-flow/tests/test_release_smoke.py`
- Create: `plugins/dev-flow/tests/test_packaged_runtime.py` through release sync
- Modify: `dev/plugins/dev-flow/.codex-plugin/release-sync.json` only if new
  non-default assets require explicit sync rules
- Update: `openspec/changes/optimize-devflow-provider-architecture/tasks.md`
- Evidence: `.planning/devflow/verification/**`

- [x] 8.1 Run all focused dev suites and then the complete development suite
      with zero failures, skips, or expected failures in the profile matrix.
- [x] 8.2 Resolve the release-preferred Plugin Eval target and inspect release
      sync dry-run JSON; parse `status` rather than relying on exit code alone,
      require a static packager-complete output list, and prove diagnostics
      execute no dynamic managed-output command.
- [x] 8.3 Stop for explicit approval before release sync apply; after apply,
      require a second dry-run with `status: current`.
- [x] 8.4 Run packaged release smoke tests for all profile/roadmap combinations
      and verify the runtime archive contains every new facade/support module.
- [x] 8.5 Run release runtime verification and require `ok: true`, valid archive
      digest, manifest/source hashes, and no unconditional external provider;
      source hashes/archive digest are the truth gate rather than requiring a
      self-referential generated `SOURCE_COMMIT` to equal the final commit.
- [x] 8.6 Run release-target Plugin Eval; require zero failures, score at least
      `86/B`, no new warning IDs, risk no higher than medium, and disposition of
      every remaining finding. Use dev-path evaluation only diagnostically.
- [x] 8.7 Validate OpenSpec and workflow state, run `git diff --check`, inspect
      exact changed files, and record residual risks/rollback.
- [x] 8.8 Run the local-reference updater in dry-run-only mode and report release
      sync, cache freshness, selected-provider skill links, project migration,
      and any conflict. Resolve PATH binary, running app-server path, active
      profile, and active Codex home first; pass that home explicitly and do not
      apply real refresh without separate approval.
- [x] 8.9 Obtain human review of the final Completion Contract before archive,
      release, commit, push, or real-project migration actions. The user's
      repeated instruction to complete and submit authorizes repository release
      sync, commit, and push only; archive, installed-cache refresh, and
      real-project migration remain separate actions.

**Validation:**

```bash
python3.12 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_*.py' -v
python3.12 -m unittest discover -s plugins/dev-flow/tests -p 'test_*.py' -v
openspec validate optimize-devflow-provider-architecture --type change --strict

# Resolve the release-preferred evaluation target, then run the actual release
# sync dry-run and parse its status rather than relying on exit code alone.
python3.12 dev/plugins/dev-flow/scripts/sync_release_assets.py --repo . --eval-target dev/plugins/dev-flow --json
RELEASE_SYNC_JSON="$(python3.12 dev/plugins/dev-flow/scripts/sync_release_assets.py --repo . --target dev-flow --json)"
printf '%s\n' "$RELEASE_SYNC_JSON"
printf '%s\n' "$RELEASE_SYNC_JSON" | jq -e '.status == "pending" or .status == "current"'

# HUMAN GATE: record fresh verification state, then use the only supported
# release apply entrypoint after explicit release-sync approval.
python3.12 dev/plugins/dev-flow/scripts/release_promotion_gate.py --repo . --apply --json
POST_SYNC_JSON="$(python3.12 dev/plugins/dev-flow/scripts/sync_release_assets.py --repo . --target dev-flow --json)"
printf '%s\n' "$POST_SYNC_JSON"
printf '%s\n' "$POST_SYNC_JSON" | jq -e '.status == "current"'

python3.12 plugins/dev-flow/scripts/verify_release_runtime.py --plugin-root plugins/dev-flow --repo-root . --json

# Resolve the enabled Plugin Eval selector from the active Codex home. Fail on
# zero or multiple enabled selectors instead of choosing an arbitrary cache.
ACTIVE_CODEX_HOME="$(codex-switch --skip-self-update status 2>/dev/null | sed -n 's/^Active CODEX_HOME: //p')"
test -n "$ACTIVE_CODEX_HOME"
PLUGIN_EVAL_SELECTOR="$(python3.12 - "$ACTIVE_CODEX_HOME/config.toml" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as config_file:
    plugins = tomllib.load(config_file).get("plugins", {})
matches = [
    key.split("@", 1)[1]
    for key, value in plugins.items()
    if key.startswith("plugin-eval@") and value.get("enabled", True)
]
if len(matches) != 1:
    raise SystemExit(f"expected exactly one enabled Plugin Eval selector: {matches}")
print(matches[0])
PY
)"
PLUGIN_EVAL_JS="$(find "$ACTIVE_CODEX_HOME/plugins/cache/$PLUGIN_EVAL_SELECTOR/plugin-eval" -path '*/scripts/plugin-eval.js' -type f -print | sort | tail -1)"
test -n "$PLUGIN_EVAL_JS"
PLUGIN_EVAL_SHA256="$(shasum -a 256 "$PLUGIN_EVAL_JS" | awk '{print $1}')"
printf 'plugin_eval_selector=%s\nplugin_eval_path=%s\nplugin_eval_sha256=%s\n' \
  "$PLUGIN_EVAL_SELECTOR" "$PLUGIN_EVAL_JS" "$PLUGIN_EVAL_SHA256"
node "$PLUGIN_EVAL_JS" analyze plugins/dev-flow --format markdown

python3.12 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo . --json
command -v codex
ps -axo command | rg 'codex.*app-server' || true
codex-switch --skip-self-update status
python3.12 dev/scripts/codex_auto_update_plugins_skills.py --repo "$PWD" --codex-home "$ACTIVE_CODEX_HOME" --skip-codex-update --skip-openai-curated-cache --skip-external-updaters --json
git diff --check
```

The apply command is documented for the approved execution path but remains
unauthorized at plan-review time. Final evidence must show release sync
`current`, Plugin Eval score/warning IDs/risk/finding dispositions, and updater
JSON `codex_home` matching the resolved active runtime.

## 9. Provider-Neutral Hardening and Local Runtime Refresh

**Files:**

- Modify: `dev/plugins/dev-flow/docs/decision_grilling_matrix.json`
- Modify: `dev/plugins/dev-flow/scripts/workflow_decision_grilling.py`
- Modify: `dev/plugins/dev-flow/scripts/lint_ai_plan.py`
- Modify: `dev/plugins/dev-flow/scripts/devflow_stop_hook.py`
- Modify: provider diagnostics, activation, provenance, and compatibility files
- Modify: DevFlow AGENTS/task-ledger templates, provider-boundary docs/skills,
  and focused tests
- Create: `.planning/agent-tasks/20260713-devflow-provider-hardening.md`
- Evidence: `.planning/devflow/verification/provider-hardening-20260713.md`

- [x] 9.1 Add RED tests proving stable core surfaces contain no provider skill
      identity and unresolved questions require `decision-resolution`.
- [x] 9.2 Replace `methodGate`, `brainstorming`, and `writing-plans` contracts
      with provider-neutral capability ids in runtime outputs, linters,
      templates, Stop-hook payloads, and durable repository guidance. Preserve
      legacy callable adapters only where they do not leak into stable output.
- [x] 9.3 Add RED tests proving `available_unselected` and
      `absent_unselected` never become a missing-provider summary or install
      action; report globally exposed Matt control-plane skills only as
      non-blocking pollution advisories.
- [x] 9.4 Make explicit provider deactivation dry-run-first and symlink-only,
      with provider-identity verification, apply authorization, preservation
      results, and idempotence tests.
- [x] 9.5 Remove Matt's global install flag, resolve the six allowlisted skills
      project-locally, and reject global-only content as satisfaction of a
      selected lean profile.
- [x] 9.6 Align current strict compatibility metadata with Superpowers `6.1.1`
      and retain manifest-driven hook behavior plus deterministic legacy source
      discovery.
- [x] 9.7 Synchronize the release package and pass focused RED/GREEN tests,
      complete dev and packaged discovery, strict OpenSpec validation, runtime
      verification, release-target Plugin Eval, and `git diff --check`.
- [x] 9.8 Refresh the named installed DevFlow plugin/cache, run project
      diagnostics, persist explicit `core + none`, and apply cleanup only to
      enumerated verified legacy provider symlinks. Preserve global Matt packs,
      provider caches, copied skills, and unknown content for manual review.
- [x] 9.9 Record exact evidence, obtain an independent final review, update all
      control-plane status, then commit and push the authorized repository
      branch.

**Validation:**

```bash
python3.12 -m unittest dev.plugins.dev-flow.tests.test_project_orchestrator -v
python3.12 -m unittest dev.plugins.dev-flow.tests.test_dependencies -v
python3.12 -m unittest dev.plugins.dev-flow.tests.test_provider_profiles -v
python3.12 -m unittest dev.plugins.dev-flow.tests.test_runtime_gates -v
python3.12 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_*.py' -v
python3.12 dev/plugins/dev-flow/scripts/release_promotion_gate.py --repo . --apply --json
python3.12 dev/plugins/dev-flow/scripts/sync_release_assets.py --repo . --target dev-flow --json | jq -e '.status == "current"'
python3.12 -m unittest discover -s plugins/dev-flow/tests -p 'test_*.py' -v
python3.12 plugins/dev-flow/scripts/verify_release_runtime.py --plugin-root plugins/dev-flow --repo-root . --json
openspec validate optimize-devflow-provider-architecture --type change --strict

# Refresh the named DevFlow plugin using the verified active runtime binary,
# then confirm source/cache parity before changing project-local state.
"$ACTIVE_CODEX_BIN" plugin add dev-flow@cy-codex-skills --json
python3.12 dev/plugins/dev-flow/scripts/doctor_workflow.py --repo . --codex-home "$ACTIVE_CODEX_HOME" --check-cache-drift --json
python3.12 dev/plugins/dev-flow/scripts/plugin_project_migration.py --repo . --codex-home "$ACTIVE_CODEX_HOME" --json
python3.12 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo . --json
python3.12 dev/plugins/dev-flow/scripts/scaffold_workflow.py --repo . --dry-run --json

# Save and review the exact cleanup plan before authorizing the same digest.
python3.12 dev/plugins/dev-flow/scripts/activate_project_dependencies.py --repo . --codex-home "$ACTIVE_CODEX_HOME" --skip-official-installs --deactivate-provider superpowers --json > .planning/devflow/verification/provider-cleanup-plan.json
CLEANUP_PLAN_DIGEST="$(jq -r '.provider_deactivation.planDigest' .planning/devflow/verification/provider-cleanup-plan.json)"
test -n "$CLEANUP_PLAN_DIGEST" && test "$CLEANUP_PLAN_DIGEST" != null
python3.12 dev/plugins/dev-flow/scripts/activate_project_dependencies.py --repo . --codex-home "$ACTIVE_CODEX_HOME" --skip-official-installs --apply --deactivate-provider superpowers --authorize-provider-cleanup superpowers --provider-cleanup-plan "$CLEANUP_PLAN_DIGEST" --json > .planning/devflow/verification/provider-cleanup-apply.json
python3.12 dev/plugins/dev-flow/scripts/activate_project_dependencies.py --repo . --codex-home "$ACTIVE_CODEX_HOME" --skip-official-installs --deactivate-provider superpowers --json | jq -e '.provider_deactivation.status == "current" or .provider_deactivation.status == "current_with_preserved_paths"'

python3.12 dev/scripts/codex_auto_update_plugins_skills.py --repo "$PWD" --codex-home "$ACTIVE_CODEX_HOME" --skip-codex-update --skip-openai-curated-cache --skip-external-updaters --json
git diff --check
```

## Execution Ledger

| Slice | Status | Owner | Required evidence | Human gate |
|---|---|---|---|---|
| 1 Baseline/characterization | done | main agent | `evidence/slice-1-baseline.md`; 218 baseline tests pass; 11 expected RED failures; 94 preserved characterization tests pass | approved by user |
| 2 Registry/core facade | done | main agent | `evidence/slice-2-provider-core.md`; 31 focused/runtime tests pass | capability schema approved in OpenSpec |
| 3 Methodology adapters | done | main agent | `evidence/slices-3-4-adapters-readiness.md`; source/lock/hook/artifact tests pass | source records approved by existing plan; no real activation |
| 4 Dependency/activation | done | main agent | same evidence; 3x2 matrix and selection-scoped command tests pass | apply remains unauthorized outside isolated tests |
| 5 Roadmap/migration | done | main agent + reviewer | `evidence/slice-5-roadmap-migration.md`; path ownership, checkpoint, snapshot, idempotence, rollback | real-project apply remains separately gated |
| 6 Routing/context cost | done | main agent | `evidence/slice-6-routing-context.md`; routing tests + diagnostic Eval disposition | release-target Eval awaits sync approval |
| 7 Outcome benchmark | skipped_with_reason | unassigned | `evidence/slice-7-benchmark-framework.md`; valid 60-run dry-run with zero model calls/writes | later default-switch change requires spend + blind review |
| 8a Release packaging | done | main agent | `evidence/slice-8-release-pending.md`; sync current; packaged matrix/runtime/Eval pass | repository release/commit/push approved by user |
| 8b Local cache/project refresh | done | main agent | named cache matches release; project migration and skill layout are current | authorized by the user's continuation request |
| 9a Provider-neutral core gates | done | provider_neutral | RED/GREEN routing, lint, template, release-smoke tests | independent review passed |
| 9b Diagnostics and safe deactivation | done | provider_diagnostics + main agent | action-free summaries; digest/auth/persistence/dirfd/rollback tests; real-project idempotence | cleanup limited to eight verified links and then current |
| 9c Matt locality and strict compatibility | done | matt_local_version + main agent | project-local lock/unique-source bootstrap, ambiguity rejection, and `6.1.1` manifest/version tests | no Matt install performed by the implementation workflow |
| 9d Release/runtime/local refresh | done | main agent | `evidence/slice-9-provider-hardening.md`; 438 dev tests; 8 packaged tests; 277 runtime checks; cache/project current | release and local refresh authorized; independent review passed |

Valid statuses: `todo`, `in_progress`, `blocked`, `done`,
`skipped_with_reason`. Mark `done` only after the listed evidence passes.

## Acceptance Criteria

- [x] A.1 All requirements and scenarios in the three new capability specs and
      the plugin-quality delta have corresponding tests/tasks.
- [x] A.2 No external provider identity is a universal required dependency.
- [x] A.3 No DevFlow writer targets a GSD-owned root planning path.
- [x] A.4 No unselected provider contributes a command, skill link, fallback,
      updater action, or blocking readiness result.
- [x] A.5 No provider skill or draft artifact can satisfy canonical completion
      evidence merely by existing or being invoked.
- [x] A.6 Legacy inference and migration report evidence/confidence and never
      delete or overwrite ambiguous/user-owned state.
- [x] A.7 Release source, generated package, runtime archive, tests, docs, and
      provider matrices are synchronized and verifiable.
- [x] A.8 Lean default remains unchanged unless a later approved change cites a
      fully passing benchmark result.
- [x] A.9 Core routing and planning contracts use stable capability ids and are
      independent of installed provider identity.
- [x] A.10 Matt allowlist activation is project-local and global alternate
      control-plane skills remain unselected advisory content.
- [x] A.11 Verified-link deactivation, current provider compatibility metadata,
      release/runtime parity, and local DevFlow refresh have fresh evidence.

## Review Checklist

- [x] Target State is complete and does not use MVP/future-work boundaries for
      required behavior.
- [x] Capability registry remains a focused seam rather than a general plugin
      framework.
- [x] Core preserves TDD evidence, completion proof, review, and canonical
      ownership after Superpowers becomes optional.
- [x] Matt excludes alternate control-plane and implicit mutating skills.
- [x] Superpowers source/hook policy is manifest-driven and single-root.
- [x] GSD suitability, readiness, single-writer, binding, migration, and
      rollback rules are explicit.
- [x] Side-effect enforcement claims match what DevFlow can actually enforce.
- [x] Validation commands are runnable and every apply/external-action gate is
      explicit.
- [x] Local reference update begins with dry-run and does not clean legacy
      conflicts automatically.

## Final Result

The provider architecture and hardening work are complete. `core + none` is the
independent default; `lean-matt` is a project-local six-skill opt-in;
`strict-superpowers` is an optional manifest-bound strict profile; and GSD is
roadmap-only when explicitly selected. Unselected providers are action-free,
cleanup is digest/persistence/dirfd guarded, dev and release runtime are in
sync, the named installed cache matches source, and independent review passed.
The live outcome benchmark remains a separately authorized prerequisite only
for a future default-switch proposal. Archive remains a separate approval.
