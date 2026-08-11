## 1. Control Plane And RED Evidence

- [x] 1.1 Activate this change in the isolated worktree's DevFlow state and add
  the bounded execution entry to `TASK_LEDGER.md` without changing the frozen
  main-worktree milestone.
- [x] 1.2 Add a public-process regression that runs the migration reminder and
  aggregate Stop Hook with `tomllib` unavailable, then capture the pre-fix
  import failure.
- [x] 1.3 Add legacy-uninstall regressions proving parser absence requires
  manual review for GSD TOML and stays silent for unrelated TOML.

## 2. Runtime Repair

- [x] 2.1 Make the legacy-uninstall TOML capability optional and replace
  parser-specific exception coupling with a Python 3.9-compatible boundary.
- [x] 2.2 Preserve strict cleanup ownership by emitting no GSD config candidate
  when the parser is unavailable and returning the exact manual action instead.
- [x] 2.3 Run the focused tests GREEN and directly qualify both Hook entrypoints
  under system Python 3.9 and Python 3.12.
- [x] 2.4 Advance the source project-refresh contract to revision 12 with
  current evidence for this tracked runtime input, unchanged project schema 8,
  and no migration step.

## 3. Packaged Candidate Verification

- [x] 3.1 Build the corrected runtime into a fresh invocation-owned temporary
  release candidate without modifying canonical `plugins/dev-flow/`.
- [x] 3.2 Run both packaged Hook entrypoints under Python 3.9 and Python 3.12,
  verify generated runtime source identity, and inspect candidate parity.
- [x] 3.3 Run Plugin Eval against the isolated release candidate and record the
  score, findings, and warning dispositions.

## 4. Completion Proof

- [x] 4.1 Run the full DevFlow source suite, strict change/all OpenSpec
  validation, workflow validation, syntax checks, and `git diff --check`.
- [x] 4.2 Review the final diff for scope, Hook schema compatibility,
  fail-closed ownership, and absence of canonical release/cache/project effects.
- [x] 4.3 Record verification evidence, update state/ledger truthfully, and
  report the separately gated release and cache-refresh next action.

## 5. Patch Release Identity

- [x] 5.1 Update release contract tests to require immutable DevFlow `0.4.1`
  assets and the exact `dev-flow-v0.4.1` workflow, then record the RED result.
- [x] 5.2 Update source plugin/version templates, release policy, expected
  manifest, release notes, publication contract, exact asset expectation, and
  GitHub Actions workflow for `0.4.1`.
- [x] 5.3 Recompute revision-12 Project Refresh Impact for the final tracked
  source inputs while preserving project schema 8 and no migration step.

## 6. Generated Release And Verification

- [x] 6.1 Record a fresh source-bound release verification receipt and promote
  only `dev-flow` through `release_promotion_gate.py`.
- [x] 6.2 Run focused release tests, the complete development and generated
  release suites, strict OpenSpec, workflow validation, runtime verification,
  source/release parity, and `git diff --check`.
- [x] 6.3 Run Plugin Eval against `plugins/dev-flow`, record its score and
  dispositions, and freeze the exact release asset names, sizes, and hashes.

## 7. Main And Immutable Publication

- [ ] 7.1 Review and stage only the approved DevFlow/OpenSpec/control-plane
  paths, create one patch-release commit, and prove its tree matches the
  reviewed candidate.
- [ ] 7.2 Fetch and verify fast-forward ancestry, fast-forward local `main`,
  push `refs/heads/main`, and read back local/remote equality.
- [ ] 7.3 Create and push immutable `dev-flow-v0.4.1`, observe the tag-bound
  GitHub Actions publication, and verify published Release state plus every
  frozen asset hash before local activation.

## 8. Internal Cache Activation And Closeout

- [ ] 8.1 Refresh only
  `CODEX_HOME=/Users/cY/.codex-switch/homes/internal`
  `dev-flow@cy-codex-skills` using the verified absolute Codex CLI.
- [ ] 8.2 Prove source/release/cache version, revision, runtime archive, and
  repaired module identities match, then rerun migration and Stop Hooks under
  `/usr/bin/python3` 3.9.6.
- [ ] 8.3 Record final Git/tag/Release/cache evidence and state without
  archiving, migrating a consumer project, or modifying another plugin.
