## 1. Contract and Baseline

- [x] 1.1 Record the approved single-path target, compatibility boundary, six-skill Matt pin, subagent ownership model, and no-apply/no-push/no-archive constraints in proposal, design, and delta specs.
- [x] 1.2 Inventory active Superpowers/GSD call chains and independently verify the Matt `v1.1.0` commit, skill hashes, installed copies, and excluded workflow skills.
- [x] 1.3 Add failing tests for the static methodology registry, minimal config, absence of provider selection, triggered project-local readiness, and disallowed Matt skills.
- [x] 1.4 Add failing tests for deterministic read-only legacy inspection, fail-closed active config, runtime import isolation, and preservation of ambiguous/history data.
- [x] 1.5 Add failing tests for bounded Agent Task Contracts, disjoint implementation write sets, primary ownership of shared artifacts, and incomplete worker evidence.
- [x] 1.6 Add failing development/release checks that reject active Superpowers/GSD modules, data, commands, fixtures, guidance, or packaged references outside the approved legacy/history allowlist.

## 2. Static Methodology and Readiness

- [x] 2.1 Implement `workflow_methodology.py` with fixed capability routes, the six approved Matt skills, stable tag/commit/hash provenance, and no profile or roadmap branch.
- [x] 2.2 Extract plugin-root and default-deny side-effect authorization into `workflow_side_effect_policy.py` and rename its checked-in policy data without changing authorization semantics.
- [x] 2.3 Simplify dependency catalog, dependency checks, and `check_dependencies.py` so triggered capabilities inspect only OpenSpec, DevFlow, required project-local Matt skills, and independently requested developer tooling.
- [x] 2.4 Simplify project skill planning/activation and `activate_project_dependencies.py` so it accepts capabilities but no provider/profile/roadmap/source-selection or provider-cleanup flags.
- [x] 2.5 Preserve source-pinned, resource-complete, project-local Matt link verification and explicit write/install authorization while removing global-install and unselected-provider readiness leakage.

## 3. Control Plane Simplification

- [x] 3.1 Replace provider-aware workflow config and scaffold output with minimal mode/hook config and a migration-required diagnostic for obsolete selection keys.
- [x] 3.2 Remove provider selection, persistence, Superpowers, and GSD branches from project activation, dependency update, updater, doctor, hook, and runtime verification call paths.
- [x] 3.3 Remove GSD roadmap binding, UAT, phase, state, verification, archive, and transition gates while retaining generic OpenSpec/DevFlow evidence and archive readiness.
- [x] 3.4 Update active DevFlow skills, root instructions, engineering policy, templates, and maintained docs to describe the single control plane, static Matt primitives, and bounded subagent strategy.
- [x] 3.5 Validate the Agent Task Contract before delegation and enforce one writer per path, explicit evidence, authority, stop conditions, and primary-agent integration ownership.

## 4. Legacy Isolation and Dead Surface Removal

- [x] 4.1 Implement `legacy_workflow_config.py` and `inspect_legacy_workflow_config.py` as deterministic filesystem-only reporting with no apply, cleanup, rollback, install, activation, or network mode.
- [x] 4.2 Recognize old config/lock fields and known provider artifacts, classify generated candidates versus preserved/history/conflict paths, and emit the canonical target plus manual next actions without mutation.
- [x] 4.3 Prove no active dependency, activation, updater, hook, scaffold, verification, archive, or release-readiness entrypoint imports the legacy inspector.
- [x] 4.4 Delete active provider registry/profile/activation/deactivation/persistence/migration modules, Superpowers gates, GSD roadmap modules/wrappers, and all now-unused import paths.
- [x] 4.5 Delete provider comparison benchmark runners/config, strict and lean provider fixtures made obsolete by the static pack, and provider-specific tests after equivalent target tests pass.
- [x] 4.6 Remove Superpowers/GSD sources and dependencies from active provenance/catalogs and remove tracked active provider/GSD configuration while preserving ignored local installations and historical/user evidence.

## 5. Development and Release Alignment

- [x] 5.1 Rewrite affected unit/integration tests around the single methodology, minimal config, generic verification/archive behavior, and explicit legacy inspector.
- [x] 5.2 Run the focused development suites for methodology, dependencies, activation, config/scaffold, legacy inspection, agent contracts, verification/archive, updater/hooks, and release packaging; fix all failures.
- [x] 5.3 Run the checked-in pre-promotion source suite (all development modules except exactly the two generated-release-dependent modules), strict repository-wide OpenSpec validation, and `git diff --check`; record a source-hash-bound release-verification receipt.
- [x] 5.4 After separate durable `release_allowed` authorization, promote verified development assets through the repository release-sync path, including wrappers, runtime pyz, manifest, source commit, skills, docs, templates, provenance, and packaged tests.
- [x] 5.5 Assert managed development/release counterparts are equivalent and a second promotion is idempotent.

## 6. Final Verification and Review

- [x] 6.1 Run the complete development test suite with Python 3.12 and no bytecode writes; record command, count, and result.
- [x] 6.2 Run the complete packaged release test suite and release runtime smoke/verification; record command, count, and result.
- [x] 6.3 Run strict validation for this change and all OpenSpec specs/changes, DevFlow workflow-state validation, forbidden-reference/import checks, and `git diff --check`.
- [x] 6.4 Resolve the release eval target and run Plugin Eval against the release plugin, fixing failures and recording score, warnings, evaluated path, and dispositions.
- [x] 6.5 Perform independent Standards and Spec code-review passes, resolve every actionable finding, and rerun affected checks.
- [x] 6.6 Update `TASK_LEDGER.md`, `.planning/devflow/STATE.md`, and the verification evidence record with changed files, exact validation results, residual installed-cache/project migration risk, and the next authorized action.
- [x] 6.7 Confirm no archive, push, installed-cache refresh, other-project migration, destructive legacy cleanup, or unrequested commit occurred.

## Acceptance Criteria

- All scenarios in `devflow-matt-native-methodology`, `devflow-legacy-provider-migration`, and the `devflow-plugin-quality` delta have passing automated or recorded verification.
- Normal active commands and packaged runtime contain no Superpowers/GSD provider result, source, install/update command, hook, skill/agent requirement, roadmap gate, or fallback.
- The only permitted legacy names are in the explicit inspector/tests, the current change, and source-only historical evidence that is not imported or packaged as active guidance.
- Active configuration and scaffold output have no provider-selection state; stale selection state fails closed with the inspector command.
- Matt readiness is pinned to `v1.1.0` commit `d574778f94cf620fcc8ce741584093bc650a61d3`, exact hashes, and project-local skills.
- Subagent work is contract-first with disjoint writes and primary-agent integration ownership.
- Full development/package/runtime/OpenSpec/workflow/diff/eval/review gates pass with no unresolved blocker.

## Validation Commands

The exact focused test module list may be refined as obsolete provider tests are replaced, but final evidence SHALL include these layers:

```text
PYTHONDONTWRITEBYTECODE=1 python3.12 dev/scripts/run_devflow_prepromotion_tests.py
PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_*.py' -v
PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest discover -s plugins/dev-flow/tests -p 'test_*.py' -v
openspec validate simplify-devflow-matt-native --strict
openspec validate --all --strict
python3.12 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo . --json
python3.12 dev/plugins/dev-flow/scripts/sync_release_assets.py --eval-target dev/plugins/dev-flow --json
git diff --check
```

Release promotion, packaged runtime verification, forbidden-reference checks, and Plugin Eval SHALL use the checked-in script entrypoints discovered during implementation and be recorded verbatim in final evidence.
