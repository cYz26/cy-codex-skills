## 1. Capability Evidence and Approved Contract

- [x] 1.1 Confirm npm `latest`, package integrity/engines, upstream `v1.7.0`
  tag/changelog, and reject mutable `latest` or unreleased `main` as the runtime
  dependency contract.
- [x] 1.2 Compare isolated OpenSpec 1.6 and 1.7 Codex core generation; prove the
  existing DevFlow command still emits the exact six skills and no 1.7 command
  files.
- [x] 1.3 Run OpenSpec 1.7 strict repository validation plus representative
  status/instructions commands against the current project.
- [x] 1.4 Record proposal, design, capability spec, Skill Routing Ledger,
  Completion Contract, write/external-effect boundaries, rollback, and zero
  Open Questions.

## 2. Test-First 1.7 Contract

- [x] 2.1 Rename the version-specific OpenSpec integration regression module
  from 1.6 to 1.7 and update its expected version, package command, metadata,
  generated skill, and compatibility assertions without changing generic
  isolation/transaction coverage.
- [x] 2.2 Add or update assertions that 1.7 remains Codex skills-only, generates
  the exact six core skills, exposes current context/operation guidance without
  changing canonical ownership, and treats 1.6 as dependency drift.
- [x] 2.3 Run the focused 1.7/dependency tests against the old source contract,
  record the expected RED failures, and confirm no unrelated baseline failure.

## 3. Source Adoption

- [x] 3.1 Update dependency provenance, exact npm install/update commands,
  expected generated version, and Node runtime contract to OpenSpec 1.7.0.
- [x] 3.2 Update OpenSpec generation/materialization defaults, updater reporting,
  diagnostics, and version-specific test fixtures to the exact 1.7 contract.
- [x] 3.3 Update DevFlow README, AGENTS template, and current-version guidance to
  describe the OpenSpec 1.7 boundary while preserving six-skill/OpenSpec/DevFlow
  ownership rules.
- [x] 3.4 Review every active-source `1.6.0` reference; update only live
  contracts and keep historical OpenSpec changes/evidence unchanged.

## 4. Source and Upstream Compatibility Verification

- [x] 4.1 Run the focused OpenSpec 1.7, dependency, activation, updater,
  migration, routing, and guidance tests to GREEN.
- [x] 4.2 Generate 1.7 skills in isolated temporary homes and verify exact names,
  `generatedBy`, allowed tools, no commands/global writes, and cleanup.
- [x] 4.3 Run complete DevFlow source discovery and OpenSpec 1.7 strict validation
  for this change and the complete repository.
- [x] 4.4 Run workflow validation, doctor, dependency diagnosis, updater dry-run,
  and diff checks; classify any incidental finding before expanding work.

## 5. Generated Release Counterpart

- [x] 5.1 Resolve and verify the generated `plugins/dev-flow` release target,
  then run release sync dry-run and record the exact candidate write set.
- [x] 5.2 Synchronize only the DevFlow release counterpart and regenerate its
  source-bound runtime manifest/archive from the verified 1.7 source.
- [x] 5.3 Run packaged discovery, release/runtime verification, source-release
  parity, and release-target `plugin-eval analyze ... --format markdown`;
  remediate failures/actionable warnings or record an allowed deferral.

## 6. Explicitly Named Local Rollout

- [x] 6.1 Capture the OpenSpec CLI, six project skills, DevFlow installed cache,
  global config, and unrelated worktree prestate; stop if rollback cannot be
  bounded.
- [x] 6.2 Install exact `@fission-ai/openspec@1.7.0`, verify the binary/version and
  Node smoke, and restore 1.6.0 if the installed runtime fails.
- [x] 6.3 Refresh the current project's exact six OpenSpec skills through the
  isolated transactional activation path and verify no mixed version, custom
  overwrite, command file, or global config change.
- [x] 6.4 Refresh only `dev-flow@cy-codex-skills` if cache parity requires it,
  then read back release/cache hashes and project migration/skill-layout state;
  do not run a broad updater apply.

## 7. Integrated Evidence and Stop Boundary

- [x] 7.1 Rerun focused, complete source, packaged, runtime, strict OpenSpec,
  workflow, doctor, dependency, cache, Plugin Eval, and `git diff --check`
  validation against the final state.
- [x] 7.2 Review the complete diff, preserve the unrelated Git-transport evidence
  edit, and record changed files, command results, hashes, risks, rollback, and
  residual findings in this change and `TASK_LEDGER.md`.
- [x] 7.3 Update `.planning/devflow/STATE.md` with the verified status and exact
  next action, then stop before commit, push, PR, publication, archive, legacy
  cleanup, or unrelated project/plugin mutation.

## 8. Authorized Submission and Final Local Refresh

- [x] 8.1 Record the user's explicit commit/push/current-project refresh
  authorization, confirm local `main` equals `origin/main`, validate native Git
  transport, and review an exact staged write set that excludes the unrelated
  Git-transport evidence edit.
- [x] 8.2 Commit the reviewed OpenSpec 1.7 source, release assets, tests,
  canonical change, and ledger on `main`; preserve all unrelated WIP and record
  the implementation commit identity.
- [ ] 8.3 Rebuild and verify the deterministic DevFlow runtime so its source
  receipt binds the implementation commit, commit that generated counterpart,
  push native Git to `origin/main`, and prove a fast-forward remote readback.
- [ ] 8.4 Refresh only `dev-flow@cy-codex-skills` and this project's exact six
  OpenSpec skills, rerun cache/project/workflow diagnostics, record final
  local/remote parity, and push the scoped closeout receipt without archive,
  PR, GitHub Release, broad updater apply, migration, or legacy cleanup.

## Execution Ledger

| Slice | Owner | Write Set | Evidence | Human Gate | Status |
|---|---|---|---|---|---|
| Evidence and plan | main | this OpenSpec change | official release and local compatibility evidence | none | done |
| RED/GREEN source contract | main | `dev/plugins/dev-flow/**`, focused root tests/docs | focused and complete tests | none | done |
| Generated release | main | `plugins/dev-flow/**` | sync receipt, package/runtime checks, Plugin Eval | no publication | done |
| Named local rollout | main | exact OpenSpec CLI, six current-project skills, named DevFlow cache | prestate and readback | named dependency update only | done |
| Final proof | main | this change, `TASK_LEDGER.md`, `.planning/devflow/**` | integrated evidence and diff | stop before commit/push/archive | done |
| Submission and final refresh | main | explicit Git index/`main`, generated runtime receipt, named DevFlow cache, current project skills, closeout evidence | transport/staged review, commits, remote ref readback, cache/project diagnostics | commit, native push, and targeted refresh explicitly authorized 2026-08-04 | pending |
