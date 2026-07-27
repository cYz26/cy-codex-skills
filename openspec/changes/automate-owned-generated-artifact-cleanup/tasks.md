## 1. Planning and Characterization

- [x] 1.1 Validate this change strictly, read apply instructions, and record
  the current DevFlow source/release/cache state plus unrelated dirty files
  that must be preserved.
- [x] 1.2 Add characterization tests proving existing tasks without a
  Generated Artifact Contract retain their current Human Gate behavior and no
  filename, extension, ignore rule, or apparent cache directory grants
  ownership.
- [x] 1.3 Record the implementation write set, source/release overlap strategy,
  exact validation commands, rollback, and the already approved named
  DevFlow-cache/game-dev integration boundary.

## 2. Contract, Manifest, and Read-Only Classification

- [x] 2.1 RED: add schema and policy tests for pre-creation registration,
  isolated roots, adjacent output scopes, repository/task/run/owner/command
  binding, persisted contract-file identity/ctime, baseline absence,
  retention, and malformed contracts.
- [x] 2.2 Implement and validate
  `generated-artifact-contract/v1`,
  `generated-artifact-manifest/v1`, and
  `generated-artifact-cleanup-receipt/v1` schemas.
- [x] 2.3 RED: add the complete decision matrix for `AUTO_CLEAN`,
  `WAIT_OWNER`, `RETAIN`, and `HUMAN_GATE`, including unregistered,
  pre-existing, tracked, protected, shared, external, occupied, escaped,
  symlink, hardlink, and identity/membership-drift cases.
- [x] 2.4 Implement the deep read-only lifecycle module with exact contract
  loading, before/after observation, protected-path and Git-state checks,
  ownership/lease validation, candidate expansion, and deterministic decision
  reasons.

## 3. Exact Cleanup and Recovery

- [x] 3.1 RED: add tests for all-or-nothing preflight, exact no-follow removal,
  deepest-first empty-directory cleanup, no wildcard/recursive deletion,
  zero-unlisted mutation, leaf-replacement races, idempotent success replay,
  and simulated partial operating-system failure.
- [x] 3.2 Implement the explicit cleanup apply path so it revalidates every
  invariant immediately before mutation, quarantines and verifies each moved
  inode before final deletion, restores mismatched replacements, records exact
  completed/remaining entries, and never reports success after uncertainty or
  partial failure.
- [x] 3.3 Implement the compact lifecycle CLI with read-only `prepare`,
  `observe`, and `plan` operations plus explicit `cleanup --apply`, structured
  JSON output, stable exit codes, and no network/configuration/Git effects.
- [x] 3.4 Prove regular files, nested directories, logs, build output, cache
  entries, lock/PID files, Unix sockets, and spool content use the same
  ownership rules without extension-specific production branches.

## 4. Task and Agent Integration

- [x] 4.1 RED/GREEN optional Generated Artifact Contract references in Agent
  Task Contracts, validation manifests, worker results, and G41 post-validation
  without breaking existing contracts.
- [x] 4.2 Integrate main-task execution records and `execute-task` guidance so
  the orchestrator may apply only a fresh `AUTO_CLEAN` plan after the owning
  process exits and must retain the cleanup receipt as evidence.
- [x] 4.3 Keep hooks, stop policies, doctors, workflow validation, and review
  surfaces read-only while reporting unresolved lifecycle decisions and exact
  next actions.
- [x] 4.4 Add compatibility tests proving no contract means no automatic
  authority and a post-creation or self-authored contract cannot legitimize
  existing residue.

## 5. Durable Guidance and Policy

- [x] 5.1 Update DevFlow source templates for `AGENTS.md`,
  `ENGINEERING_POLICY.md`, Agent Task Contracts, technical plans, task ledgers,
  and review checklists with the registration-only automatic-reclamation rule.
- [x] 5.2 Update DevFlow README/hook/runtime documentation to distinguish
  `WAIT_OWNER`, automatic task-owned reclamation, retained evidence, and
  genuine destructive Human Gates.
- [x] 5.3 Add static consistency tests across source guidance, generated
  templates, schemas, and CLI help without introducing a second task queue or
  automatic canonical writer.

## 6. Source, Release, and Plugin Verification

- [x] 6.1 Run focused lifecycle, Agent Task Contract, orchestration, runtime,
  release-smoke, and packaged-runtime tests with Python 3.12 and bytecode
  disabled.
- [x] 6.2 Run the complete DevFlow pre-promotion suite, strict change and
  repository-wide OpenSpec validation, workflow validation, and
  `git diff --check`.
- [x] 6.3 Regenerate the DevFlow release runtime from the combined current
  source state, preserving the unrelated stop-hook work, then prove managed
  source/release parity including the complete lifecycle test module and
  packaged smoke coverage.
- [x] 6.4 Run release-target Plugin Eval, record score/findings/remediation,
  and leave any unresolved actionable failure as a blocker rather than
  weakening the contract.

## 7. Named Refresh and First Consumer Evidence

- [x] 7.1 Run the read-only local-reference updater and DevFlow doctor to prove
  exact source/release/cache drift before applying any refresh.
- [x] 7.2 Refresh only `dev-flow@cy-codex-skills` through the verified
  ChatGPT.app Codex CLI, then prove recursive cache/source parity without
  legacy cleanup or unrelated updater actions.
- [x] 7.3 Run `game-dev` read-only diagnostics and create its project-specific
  adapter through its own OpenSpec ownership only when doing so does not
  overlap the active main-task control plane; existing unregistered residue
  remains outside automatic cleanup authority.
- [x] 7.4 Record focused and broad evidence, residual risks, exact consumer
  handoff, and completion status without commit, push, PR, archive,
  publication, configuration mutation, or deletion of pre-existing
  unregistered artifacts.

## 8. Post-Commit Independent Review Repairs

- [x] 8.1 RED: reproduce post-creation contract resealing, concurrent leaf
  replacement at the deletion boundary, missing release lifecycle tests, and
  the missing active-ledger evidence link.
- [x] 8.2 GREEN: bind classification to the canonical persisted contract file
  identity/ctime and replace verify-then-unlink with quarantine, moved-inode
  verification, and fail-closed restoration.
- [x] 8.3 GREEN: restore byte-equivalent lifecycle tests to the release sync
  contract and link the final verification record from the active ledger item.
- [ ] 8.4 Regenerate the source-bound release, rerun focused/broad/runtime and
  Plugin Eval gates, refresh only the two authorized DevFlow caches, complete
  a fresh two-axis review, and record final commit/cache evidence.

## Validation Commands

```bash
PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -B -m unittest \
  dev/plugins/dev-flow/tests/test_generated_artifact_lifecycle.py

PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -B -m unittest \
  dev/plugins/dev-flow/tests/test_agent_task_contract.py \
  dev/plugins/dev-flow/tests/test_project_orchestrator.py \
  dev/plugins/dev-flow/tests/test_runtime_gates.py \
  dev/plugins/dev-flow/tests/test_release_smoke.py \
  dev/plugins/dev-flow/tests/test_packaged_runtime.py

PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -B \
  dev/scripts/run_devflow_prepromotion_tests.py

openspec validate automate-owned-generated-artifact-cleanup --strict
openspec validate --all --strict

/opt/homebrew/bin/python3.12 -B \
  dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo . --json

/opt/homebrew/bin/python3.12 -B \
  dev/plugins/dev-flow/scripts/sync_release_assets.py \
  --repo . --target dev-flow --json

/opt/homebrew/bin/python3.12 -B \
  plugins/dev-flow/scripts/verify_release_runtime.py \
  --plugin-root plugins/dev-flow --repo-root . --json

plugin-eval analyze plugins/dev-flow --format markdown
git diff --check
```

## Human Gates and Exclusions

- The user approved the registration-only architecture and named
  DevFlow/cache/game-dev integration on 2026-07-27.
- This approval does not authorize deleting any artifact that predates a valid
  contract, including the currently recorded `game-dev` residue.
- `DF-IFL-004` records the non-DevFlow migration-reminder applicability gap as
  `DEFER_AND_CONTINUE`; it requires separate OpenSpec intake and does not add
  Hook-policy work to this change.
- `DF-IFL-005` records the pre-contract `workwork` Stop-hook workaround state;
  this change MUST NOT infer ownership or delete those external files.
- Commit, push, PR, archive, publication, broad updater actions, global
  configuration mutation, legacy cleanup, and unrelated project migration
  remain unauthorized.
