# OpenSpec 1.6 DevFlow Upgrade Execution Contract

## Target State

DevFlow requires the released OpenSpec CLI `1.6.0`, generates the official six
core Codex skills through an isolated staging environment, installs verified
copies only into project-local `.agents/skills`, routes planning revisions to
`openspec-update-change`, and never changes a user's global OpenSpec profile,
delivery mode, telemetry configuration, or `$CODEX_HOME/prompts` during project
activation.

## Scope / Non-Goals

- Scope: DevFlow source/release dependency policy, updater, project activation,
  generated skill installation, diagnostics, migration, routing guidance,
  tests, release assets, local CLI/plugin/project refresh, and evidence.
- Non-goals: OpenSpec stores/custom-schema product adoption, unreleased main,
  unrelated dependencies, global OPSX prompt enablement, and OpenSpec archive.

## Completion Contract

- [x] OpenSpec `1.6.0` and Node `>=20.19.0` are the verified dependency contract.
- [x] All six official core skills are generated and copied project-locally.
- [x] Real global OpenSpec/Codex configuration remains byte-for-byte unchanged during activation.
- [x] Dry-run is write-free; stale generated copies refresh; custom content is preserved.
- [x] Source, packaged, OpenSpec, runtime, cache, and project diagnostics pass or record an expected policy block with no stale project state.

## 1. Capability Evidence and Plan

- [x] 1.1 Compare official `v1.5.0`, released `v1.6.0`, npm metadata/package, generated Codex artifacts, CLI help, and current `main`.
- [x] 1.2 Reproduce global-delivery leakage and verify isolated `XDG_CONFIG_HOME` plus `CODEX_HOME` generates six 1.6 project skills.
- [x] 1.3 Record proposal, design, capability spec, Skill Routing Ledger, rollback, and zero Open Questions.
- [x] 1.4 Run strict OpenSpec 1.6 validation before implementation.

## 2. Test-First Dependency and Generation Contract

- [x] 2.1 Add RED tests for pinned provenance/updater version, Node engine metadata, and six-workflow catalog including `openspec-update-change`.
- [x] 2.2 Add RED tests proving dry-run performs no invocation/write and apply uses isolated staging environment instead of the real repo/global homes.
- [x] 2.3 Add RED tests for exact-set/generatedBy verification, ephemeral-source copy semantics, stale generated refresh, custom target preservation, command failure, and cleanup.
- [x] 2.4 Record failing commands and expected failures in verification evidence.

## 3. Isolated OpenSpec 1.6 Integration

- [x] 3.1 Update dependency provenance and apply updater to pinned `@fission-ai/openspec@1.6.0` with Node `>=20.19.0` metadata.
- [x] 3.2 Implement temporary isolated OpenSpec generation with telemetry disabled and real global paths excluded.
- [x] 3.3 Verify the six official skills and materialize copies transactionally into `.agents/skills` without persistent `.codex/skills` staging.
- [x] 3.4 Preserve custom targets, refresh verified generated targets, fail closed on output drift, and clean staging on every result.

## 4. Routing, Diagnostics, and Guidance

- [x] 4.1 Add `openspec-update-change` to catalogs, migration, test fixtures, updater discovery, and project diagnostics.
- [x] 4.2 Replace misleading direct-init remediation with DevFlow activation guidance and document global delivery/command boundaries.
- [x] 4.3 Align planning guidance with OpenSpec 1.6 status/instructions `artifactPaths` and `actionContext`, validation, and archive failure semantics.
- [x] 4.4 Update DevFlow README, templates, and active AGENTS rules only where durable routing changed.

## 5. Verification and Release

- [x] 5.1 Run focused dependency, activation, provider, routing, migration, and updater tests.
- [x] 5.2 Run complete development test discovery and strict OpenSpec 1.6 validation.
- [x] 5.3 Resolve release target, run Plugin Eval, synchronize release assets through the authorized release gate, and prove the second dry-run is current.
- [x] 5.4 Run packaged discovery and runtime archive verification; record hashes and results.

## 6. Local Rollout and Final Evidence

- [x] 6.1 Install pinned OpenSpec CLI `1.6.0` and verify Node/CLI smoke output.
- [x] 6.2 Refresh `dev-flow@cy-codex-skills`, activate current-project official skills through the isolated path, and verify six local 1.6 copies.
- [x] 6.3 Rerun workflow validation, doctor/cache drift, project migration, dependency diagnosis, scaffold dry-run, and Git status.
- [x] 6.4 Update root `TASK_LEDGER.md`, `.planning/devflow/STATE.md`, change tasks, and final verification evidence with remaining risks.

## Execution Ledger

| Slice | Owner | Write Set | Evidence | Human Gate | Status |
|---|---|---|---|---|---|
| Evidence and plan | main agent | this OpenSpec change | official source/tag/package/CLI/local reproduction | none | done |
| RED contract tests | main agent | DevFlow tests | failing focused tests | none | done |
| Integration implementation | main agent | DevFlow docs/scripts/skills/templates | GREEN focused tests | dependency install remains explicit | done |
| Release synchronization | main agent | `plugins/dev-flow/**` | release gate/package/runtime/Eval | release apply authorized by implementation request | done |
| Local rollout | main agent | installed CLI/cache and current project links | version/cache/project diagnostics | OpenSpec install and named refresh authorized by upgrade request | done |

## Validation Commands

```bash
python3.12 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_dependencies.py'
python3.12 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_provider_profiles.py'
python3.12 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_plugin_project_migration.py'
python3.12 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_provider_guidance.py'
python3.12 -m unittest discover -s dev/plugins/dev-flow/tests
OPENSPEC_TELEMETRY=0 npx -y @fission-ai/openspec@1.6.0 validate upgrade-devflow-openspec-1-6 --strict --no-interactive
python3.12 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo . --json
python3.12 dev/plugins/dev-flow/scripts/doctor_workflow.py --repo . --check-cache-drift --json
python3.12 dev/plugins/dev-flow/scripts/plugin_project_migration.py --repo . --json
git diff --check
```

## Risks / Rollback / Stop Conditions

- Stop before project writes if generated skills are not the exact six-skill
  `1.6.0` contract or if global path isolation cannot be proven.
- Stop and preserve custom skill content on any target provenance conflict.
- Do not bypass a failing test, release gate, OpenSpec validation, or archive
  gate.
- Roll back the CLI with the pinned `1.5.0` install only if 1.6 smoke/runtime
  validation fails; otherwise revert DevFlow changes and restore generated
  project copies from recorded evidence.

## Final Verification

- [x] Required behavior matches every scenario in `devflow-openspec-integration`.
- [x] Exact commands/results, changed files, cache paths, risks, and rollback evidence are recorded.
- [x] No generated global OPSX prompt remains from testing or activation.
- [x] OpenSpec archive remains unperformed without separate authorization.
