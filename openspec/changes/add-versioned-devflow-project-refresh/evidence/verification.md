# Source Verification Evidence

- Timestamp: `2026-08-06T16:51:30+08:00`
- Boundary: development source verified; generated release, installed cache,
  consumer projects, archive, Git submission, and publication not changed.
- Project Refresh Impact: `changed_covered`.
- Contract identity: engine schema `2.0`, project schema `0..1`, refresh
  revision `1`, tracked-input SHA-256
  `6a6e6a4afcc4896e41d0311708be997da4c59e68b727574fb788484f2e207c22`.
- Migration coverage: `0 -> legacy-selection-v0-to-v1 -> 1`.

## Focused Development Checks

1. Project refresh, compatibility migration, legacy inspector, and
   orchestrator:

   ```bash
   PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -B -m unittest \
     dev/plugins/dev-flow/tests/test_project_refresh.py \
     dev/plugins/dev-flow/tests/test_plugin_project_migration.py \
     dev/plugins/dev-flow/tests/test_legacy_workflow_config.py \
     dev/plugins/dev-flow/tests/test_project_orchestrator.py -q
   ```

   Result: `113 tests`, pass.

2. Release impact, temporary packaged runtime, and release smoke:

   ```bash
   PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -B -m unittest \
     dev/plugins/dev-flow/tests/test_release_sync.py \
     dev/plugins/dev-flow/tests/test_packaged_runtime.py \
     dev/plugins/dev-flow/tests/test_release_smoke.py -q
   ```

   Result: `79 tests`, pass. These tests use temporary packages and do not
   mutate checked-in `plugins/dev-flow/**`.

3. Published JSON schemas plus Project Refresh Impact unit matrix: `9 tests`,
   pass. Final live analyzer result against the checked-in release is
   `changed_covered`, with no errors and the expected change ID.

4. Skill validation:

   ```bash
   PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -B \
     /Users/cY/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
     dev/plugins/dev-flow/skills/dev-flow-refresh
   PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -B \
     /Users/cY/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
     dev/plugins/dev-flow/skills/plugin-project-migration
   ```

   Result: both Skills valid.

## Broad Source and Specification Checks

- Complete DevFlow development suite:

  ```bash
  PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -B -m unittest \
    discover -s dev/plugins/dev-flow/tests -p 'test_*.py' -q
  ```

  Result: `499 tests`, pass in `48.987s`.
- `lint_ai_plan.py openspec/changes/add-versioned-devflow-project-refresh/design.md`:
  pass.
- `validate_workflow_state.py --repo . --json`: pass with no issues or
  warnings before source-gate state promotion; rerun after the state/checkpoint
  update is recorded below.
- `openspec validate add-versioned-devflow-project-refresh --strict`: pass.
- `openspec validate --all --strict --no-interactive`: `60 passed, 0 failed`.
- `git diff --check`: pass.
- Full changed-path review: all task-owned edits are within the approved
  development write set. The only path outside it is the pre-existing unrelated
  `separate-git-transport-from-github-auth` evidence edit; its diff digest
  remains exactly
  `156697b2fda831afd5ac23a2e5ce8ffc98d18836f345535915bded204d812ba6`.
- Final readback after tasks, evidence, checkpoint, and state promotion:
  workflow validation passes with no issues or warnings; the current change and
  all 60 OpenSpec items still pass strict validation; `git diff --check` and the
  unrelated-diff digest assertion pass.

## Security and Failure Proof

- Planning is deterministic and read-only; unrelated worktree changes do not
  enter `planSha256`, while every managed input and source identity does.
- Real overlap and symlink-parent preflight tests make zero repository and
  external writes.
- Promotion and verification fault injection restores project paths and state;
  restore failure retains a transaction contract and backup, and later plans
  block on recovery.
- Receipts reject cross-repository replay, fabricated state/action sets,
  arbitrary paths, post-apply edits, and missing/untrusted files without a
  traceback or destructive fallback.
- Plans, receipts, inspector output, errors, and migration history contain no
  legacy config values or secret-bearing preimages.

## Task 7.1 — Generated Release Gate

Read-only release planning command:

```bash
PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -B \
  dev/plugins/dev-flow/scripts/sync_release_assets.py \
  --repo . --target dev-flow --json
```

Result: `pending`, no selection errors, no writes. The exact source-copy drift
under `plugins/dev-flow/` is:

- `.codex-plugin/project-migration.json`
- `.codex-plugin/release-sync.json`
- `README.md`
- `assets/project-refresh/config-v1.json`
- `assets/templates/AGENTS.md.template`
- `assets/templates/ENGINEERING_POLICY.md.template`
- `assets/templates/EVIDENCE_TEMPLATE.md.template`
- `assets/templates/OPENSPEC_DESIGN.md.template`
- `assets/templates/OPENSPEC_TASKS.md.template`
- `assets/templates/REVIEW_CHECKLIST.md.template`
- `fixtures/project-refresh/current.json`
- `fixtures/project-refresh/legacy-conflicting-aliases.json`
- `fixtures/project-refresh/legacy-preserve-settings.json`
- `fixtures/project-refresh/legacy-root-selection.json`
- `fixtures/project-refresh/legacy-workflow-selection.json`
- `fixtures/project-refresh/manifest.json`
- `schemas/project-refresh-contract.schema.json`
- `schemas/project-refresh-plan.schema.json`
- `schemas/project-refresh-receipt.schema.json`
- `skills/ai-native-tech-plan/SKILL.md`
- `skills/change-plan/SKILL.md`
- `skills/dev-flow-refresh/SKILL.md`
- `skills/dev-flow-refresh/references/project-refresh.md`
- `skills/execute-task/SKILL.md`
- `skills/plugin-project-migration/SKILL.md`
- `skills/verify-and-archive/SKILL.md`

The same authorized release transaction may regenerate exactly the 50
`plugins/dev-flow/scripts/**` managed outputs declared by
`dev/plugins/dev-flow/.codex-plugin/release-sync.json` (file SHA-256
`0587b5164a913cab7751720aae84b9b78395a4e9b3a7ee285e312960c2f1f596`),
including the runtime archive, manifest, source-commit marker, and SHA-256
record. The dry run currently reports only
`scripts/devflow_runtime.MANIFEST.json` as stale before running the build.
This declaration plus the exact source-copy list above is the complete
generated write set; no path outside `plugins/dev-flow/**` is a release target.

If separately authorized, the exact promotion command is:

```bash
PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -B \
  dev/plugins/dev-flow/scripts/release_promotion_gate.py \
  --repo . --target dev-flow --apply --json
```

The read-only gate check correctly refuses promotion while
`release_allowed=false` and a fresh complete release-verification receipt is
absent. Its remaining blockers are exactly `current_change_verified` and
`fresh_complete_release_verification`; both belong to the separately authorized
release continuation. Formal generated-release parity, release-target Plugin Eval, local
reference drift, cache refresh, and consumer-project apply remain pending tasks
7.2–7.4 and require their stated authorization boundaries.

## Task 7.2 — Authorized Generated Release Synchronization

The user explicitly authorized the recommended generated-release continuation
on 2026-08-06. The authorization was durably narrowed to target `dev-flow` and
write root `plugins/dev-flow/**` by setting `gates.release_allowed: true`; it did
not authorize installed-cache refresh, consumer-project migration, archive, Git,
or publication.

Fresh pre-promotion proof before the write:

- `PYTHONDONTWRITEBYTECODE=1 python3.12 dev/scripts/run_devflow_prepromotion_tests.py`:
  463/463 source-only tests passed across 23 modules with zero skips; Project
  Refresh Impact passed.
- `OPENSPEC_TELEMETRY=0 openspec validate --all --strict --no-interactive`:
  60 passed, 0 failed.
- `git diff --check`: pass.
- `.planning/devflow/release-verification/dev-flow.json` recorded the exact
  canonical commands and source snapshot SHA-256
  `9575171af5e71c2b0594797fa8ea99ec6380ac7d5a1ce67a6c3f56ffdc10cb67`.
- The read-only promotion gate reported `ready: true`, no blockers, the same
  source digest, and durable target-bound authorization.

Authorized generation command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3.12 -B \
  dev/plugins/dev-flow/scripts/release_promotion_gate.py \
  --repo . --target dev-flow --apply --json
```

Result: `synced`. The repository packager completed with exit 0, the one-time
repo-and-target-bound authorization was consumed, all 26 declared source-copy
paths were promoted, and the four generated runtime provenance outputs were
regenerated. No deletion or write outside `plugins/dev-flow/**` was reported.
Release provenance hashes immediately after generation were:

- `scripts/devflow_runtime.pyz`:
  `68417903f2fe1d3b470fb866930d031465f9159b1bad9c905f78e1651b1223ba`
- `scripts/devflow_runtime.MANIFEST.json`:
  `2148e4352b913c24a01c7907d04ef792b13388da258ac066ac15c567b46550d9`
- `scripts/devflow_runtime.sha256`:
  `02affb2c2b128d820a97cf2aca36ceacec836365512c70f2bbf4676d0b5bc53e`
- `.codex-plugin/project-migration.json`:
  `be0d7637c92fcc7f77dfec23b5c26ea5ad9d202ab6ca40a7dc035e3a719784b8`

An immediate read-only `sync_release_assets.py --repo . --target dev-flow
--json` readback returned `status: current` with empty `changedFiles`,
`changedOutputs`, `missingOutputs`, `staleFiles`, and `staleOutputs`. Formal
runtime parity and release quality gates continue in task 7.3.

## Task 7.3 — Post-Promotion Verification

The first post-promotion full suite correctly exposed one release-only
allowlist gap: `test_manifest_marketplace_assets_and_hooks_are_declared`
expected only the historical generated-artifact fixture after the six newly
packaged Project Refresh JSON fixtures became present. This was classified
`CONTINUE_WITH_MINIMAL_GUARD` because it directly blocked the authorized
release Completion Contract and fit the existing test write set. The explicit
expected release fixture set was extended; the focused 48-test orchestrator
module then passed.

Fresh final task 7.3 results after that guard:

- focused project/refresh/migration/orchestrator suite: 113/113 passed;
- focused release-sync/packaged-runtime/release-smoke suite: 79/79 passed;
- complete DevFlow suite: 499/499 passed in 49.290s;
- generated release runtime verification: `status: verified`, archive SHA-256
  `68417903f2fe1d3b470fb866930d031465f9159b1bad9c905f78e1651b1223ba`,
  source/release Project Refresh identities both valid, tracked-input digest
  `6a6e6a4afcc4896e41d0311708be997da4c59e68b727574fb788484f2e207c22`;
- `dev-flow-refresh` and `plugin-project-migration` quick validation: valid for
  both development source and generated release copies;
- AI-native plan lint: pass;
- workflow-state validation: exit 0 with no issues;
- strict current-change validation: pass;
- repository-wide strict OpenSpec validation: 60 passed, 0 failed;
- release sync readback: `current` with no changed, missing, or stale files or
  outputs;
- `git diff --check`: pass.

Release-target Plugin Eval evidence is recorded separately in
`evidence/plugin-eval.md`: 86/B, medium static risk, zero failures, three known
plugin-wide token-budget warnings, and no new change-specific actionable
finding. Those warnings retain the existing `DF-IFL-001`
`DEFER_AND_CONTINUE` disposition and do not authorize a plugin-wide budget
refactor inside this Project Refresh change.

## Task 7.4 — Read-Only Local Reference Check

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3.12 -B \
  dev/scripts/codex_auto_update_plugins_skills.py --json
```

Result: exit 0 with `apply: false`; no updater, plugin installation, cache
refresh, project migration, or other write was attempted. The DevFlow-specific
readback reported:

- release source: `plugins/dev-flow`;
- named installed cache:
  `/Users/cY/.codex/plugins/cache/cy-codex-skills/dev-flow/0.3.0+codex.20260529145038`;
- cache verification: `matches-source`;
- Project Refresh parity across development source, generated release, and the
  named cache: `verified`, with matching contract schema `2.0`, engine schema
  `2.0`, project head `1`, refresh revision `1`, refresh digest
  `sha256:a9d4701c9b3668bc4fbcc0b15c7a89bc45c621b98fc98e72567da5f0bf3af1d6`,
  and tracked-input digest
  `6a6e6a4afcc4896e41d0311708be997da4c59e68b727574fb788484f2e207c22`;
- this repository's project migration and project-local Skill layout:
  `current`;
- `registrationOnlySatisfiesFreshness: false`, so the independent byte-level
  cache verification—not the generic `would-refresh` install plan—is the
  freshness evidence.

The report also exposed unrelated global updater candidates and one mirror
without an upstream, but no such action belongs to this change. No consumer
project, including `/Users/cY/dev/game-dev`, was inspected for apply or mutated.

## Task 9.6 — Corrective Source Verification and Independent Review

- Stable source snapshot at `2026-08-07T11:59:29+08:00`: Project Refresh
  42/42, Project Refresh Impact 10/10, and the complete pre-promotion suite
  468/468 across 23 source modules, with no skipped test and the real impact
  gate covered.
- The real source-versus-release analyzer reports `changed_covered`,
  `schemaDecision: advanced`, project head `2`, revision `2`, migration
  coverage `1 -> full-openspec-v1-to-v2 -> 2`, and `errors: []`. Recorded and
  recomputed tracked-input SHA-256 are both
  `ee6817cc798f64d1976c815accbad39cc2966e6244b1eeb019778ba8d9d597d1`;
  refresh-contract digest is
  `sha256:416b5119328c16202a3fc719179d79e34763ff929dee8afb340ef9c1ea79b6d1`.
- Corrective public tests prove v0/v1 reach head 2, an unknown future
  `projectContract` marker blocks with zero configuration action, an intact
  standalone verification receipt survives apply-receipt tampering, and both
  apply/verification receipts reject legally shaped resealed changes to the
  before-state fingerprint, verification result, or rollback status.
- `openspec validate add-versioned-devflow-project-refresh --strict` and
  `openspec validate --all --strict --no-interactive` pass 61/61 items.
  Workflow state validation has no issues or warnings; AI-native plan lint,
  both source Skill validations, and `git diff --check` pass.
- Standards review: DONE/PASS after personally replaying every prior P1 and
  superseding its stale child-review intermediate result. Spec/Completion
  Contract review: DONE with no task 9.3–9.6 blocker. Both reviews were
  read-only and confirmed the exact write set, release default-deny boundary,
  schema-advance contract, receipt state anchor, and future-marker guard.
- The unrelated Git-transport evidence diff remains excluded and byte-stable
  at SHA-256
  `156697b2fda831afd5ac23a2e5ce8ffc98d18836f345535915bded204d812ba6`.
  Generated release, runtime parity, and release-target Plugin Eval remain
  task 9.7 and were not claimed by this source gate.

## Task 9.7 — Corrective Generated Release and Quality Gates

- At `2026-08-07T12:09:46+08:00`, the target-bound promotion gate consumed the
  user's task 9.7 authorization and regenerated only `plugins/dev-flow/**`.
  The packager exited 0, release sync then read back `current` with no changed,
  missing, stale, or deleted path. The runtime archive SHA-256 is
  `1d793be3ec3d345daeea1fdc520fb7486babae89a1d171633bdedcf13b66dc95`.
- The first 504-test packaged run exposed one stale fixture allowlist assertion:
  the release correctly contained `fixtures/project-refresh/current-v2.json`,
  while the assertion still listed only v1 fixtures. The existing source test
  was corrected, passed independently, and release sync remained `current`
  because test sources are not release-copy inputs.
- Fresh proof after that correction: pre-promotion 468/468 across 23 modules;
  strict OpenSpec 61/61; complete packaged/release-dependent suite 504/504;
  release runtime `verified`; source/release/named-cache Project Refresh parity
  `verified` with `errors: []`; all four source/release validations for
  `dev-flow-refresh` and `plugin-project-migration` passed; `git diff --check`
  passed. The refreshed source receipt SHA-256 is
  `71700f9f5f174f6423a3163a796fb834d6e0925bb115a5c50607508f5ace04d7`.
- Release-target Plugin Eval exited 0 at 86/100, grade B, medium risk, with
  0 failures, 3 known plugin-wide static budget warnings, and 2 informational
  observations. The warnings retain `DF-IFL-001 / DEFER_AND_CONTINUE`; changing
  the 16-Skill architecture or running paid measurement is outside this write
  set and is not required by the Project Refresh Completion Contract.
- The read-only local updater reports release and installed named-cache bytes
  already `matches-source`, Project Refresh parity `verified`, and project-local
  skill layout `current`. It also lists unrelated broad updater candidates;
  none was applied. The explicitly authorized named refresh still remains task
  9.8 and will run only after the exact `origin/main` submission.
- The unrelated Git-transport diff remains excluded and byte-stable at diff
  SHA-256
  `156697b2fda831afd5ac23a2e5ce8ffc98d18836f345535915bded204d812ba6`.

## Task 9.8 — Exact Submission and Named Cache Refresh

- The reviewed index contained 96 approved Project Refresh source, generated
  release, OpenSpec, and DevFlow control-plane paths. It contained neither
  `openspec/changes/separate-git-transport-from-github-auth/**` nor any
  `repair-devflow-goal-gate-lifecycle` artifact; `git diff --cached --check`
  passed. The intended commit was created directly on `main` as
  `ceb08a23a375685dc2a91afc0a3ff47a4ea36ff7` with subject
  `feat(devflow): add versioned project refresh`.
- Native Git transport preflight reported `GIT_TRANSPORT_READY`, SSH origin,
  remote baseline `187c81cb25a13cde58b9c972a9ed050311f82775`, and no `gh` dependency.
  `git push origin main` advanced `origin/main` to `ceb08a23…a36ff7`; both
  `git ls-remote --heads origin refs/heads/main` and local `HEAD` read back the
  exact full commit. No force-push, PR, tag, release publication, or GitHub
  control-plane write occurred.
- After the remote readback, the only cache mutation was
  `codex plugin add dev-flow@cy-codex-skills --json`. It installed version
  `0.3.0+codex.20260529145038` at
  `/Users/cY/.codex/plugins/cache/cy-codex-skills/dev-flow/0.3.0+codex.20260529145038`
  and exited 0. No broad updater apply was run.
- Post-refresh readback reports the installed cache `matches-source`, project
  migration/Skill layout `current`, and source/release/cache Project Refresh
  parity `verified` with `errors: []`. All three tracked-input SHA-256 values
  are exactly
  `ee6817cc798f64d1976c815accbad39cc2966e6244b1eeb019778ba8d9d597d1`;
  all three identities are head 2, revision 2, digest
  `sha256:416b5119328c16202a3fc719179d79e34763ff929dee8afb340ef9c1ea79b6d1`.
- The working tree after delivery contains only the pre-existing unrelated
  Git-transport evidence diff, still excluded at diff SHA-256
  `156697b2fda831afd5ac23a2e5ce8ffc98d18836f345535915bded204d812ba6`.
  Consumer migration, `AGENTS.md.generated` merge, cleanup, archive, PR, and
  publication remain unperformed and unauthorized.

## Task 8.1 — Final Diff and Two-Axis Review

Completion dependencies for `change-review` and `completion-proof` reported
`ready_with_recommendations`: OpenSpec 1.7.0, the adapted project-local
`code-review` primitive, and `verify-and-archive` were all ready. Because this
side conversation prohibits subagents, the main agent performed the required
Standards and Spec axes directly against the current worktree, the approved
OpenSpec artifacts, and the exact generated-release output.

### Standards axis

No actionable finding. Production release files were generated only through
the repository promotion gate; source/release/runtime parity is executable;
the late release-fixture guard is an explicit allowlist assertion in the
existing test module; no direct cache, project, dependency, archive, Git, or
publication mutation occurred. `git diff --check` passes.

### Spec axis

No actionable finding. OpenSpec apply instructions show 34/37 tasks complete
before this closeout slice, with only 8.1–8.3 pending. Every required
Project Refresh behavior, versioned migration fixture, release parity check,
authorization boundary, and evidence route is implemented and verified. The
late test guard covers required packaged fixtures and adds no product behavior.

### Scope and unrelated work

All task-owned tracked and untracked paths are within the approved development
write set, generated `plugins/dev-flow/**`, or canonical OpenSpec/DevFlow
evidence and state. The sole pre-existing path outside that set remains
`openspec/changes/separate-git-transport-from-github-auth/evidence/implementation.md`;
its diff SHA-256 is still exactly
`156697b2fda831afd5ac23a2e5ce8ffc98d18836f345535915bded204d812ba6`.
No byte on that path was changed by this continuation.

### Receipts, residuals, rollback, and restart

- source-bound pre-promotion receipt:
  `.planning/devflow/release-verification/dev-flow.json`, source SHA-256
  `9575171af5e71c2b0594797fa8ea99ec6380ac7d5a1ce67a6c3f56ffdc10cb67`;
- promotion result: `synced`, followed by two read-only `current` readbacks;
- release runtime archive SHA-256:
  `68417903f2fe1d3b470fb866930d031465f9159b1bad9c905f78e1651b1223ba`;
- residual `DF-IFL-001`: known plugin-wide static token-budget cost, non-blocking
  and separately scoped; no `BLOCKED_AWAITING_HUMAN` disposition exists inside
  this Completion Contract;
- failed promotion automatically restores the previous release tree. A later
  intentional rollback must first restore the approved source/release bytes
  from the reviewed Git baseline, then rerun the same promotion and complete
  parity checks; this task did not execute such a destructive rollback;
- no restart is required to complete the repository change. Any later plugin
  installation/registration or running-client reload remains a separately
  authorized operational step even though the named cache currently verifies
  byte-equivalent in read-only inspection.

## Task 8.2 — Completion Contract Claim

Implementation and verification are complete for the authorized Project
Refresh change. All source tasks and authorized generated-release tasks through
8.1 are checked; focused, broad, runtime, release, Skill, strict OpenSpec,
workflow, diff, Plugin Eval, and reference-readback evidence is fresh; no
unresolved `BLOCKED_AWAITING_HUMAN` finding exists in the approved scope. The
known static budget residual remains non-blocking and separately scoped.

This claim does not include archive, spec sync, commit, push, PR, publication,
consumer-project migration, AGENTS merge, legacy cleanup, dependency update, or
new cache mutation.

## Task 8.3 — State and Checkpoint Closeout

Created
`.planning/devflow/checkpoints/2026-08-06-verification_passed-add-versioned-devflow-project-refresh.md`
with the verified outcome, exact validation evidence, decisions, residuals,
changed-file inventory, and `feature_intake` continuation route. Updated
`.planning/devflow/STATE.md` to 37/37 verified, closed the consumed
`release_allowed` gate, retained `archive_allowed: false`, and recorded the
completed Goal disposition. Compact remains an advisory `pending`
recommendation at this durable boundary; the checkpoint is sufficient for
recovery and does not block the already approved next intake.

No cache refresh, consumer-project apply, AGENTS merge, legacy cleanup, archive,
commit, push, PR, or publication was performed.
