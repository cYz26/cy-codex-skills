## Execution Ledger Contract

All items are owned by the primary agent unless an item explicitly names an independently validated read-only reviewer. Write sets, evidence classes, and the standing Human-Gate boundary are defined in `design.md`; every item records its fresh command/result in the change evidence and updates this checklist only after verification. A task boundary, RED test, technical drift, generated-artifact refresh, review, commit, push, publication, or named refresh does not create a Human Gate. Stop only for a concrete material authority delta listed in the design; persist it through the single gate recorder. OpenSpec archive is excluded.

## 1. Restore exact project-local readiness and freeze the baseline

- [x] 1.1 Run the canonical project dependency activation dry-run for this worktree, verify that only the exact missing `.agents/skills` links are proposed, apply that sealed plan, and rerun dependency checks without touching cache, global configuration, or another project.
- [x] 1.2 Update `.planning/devflow/STATE.md` and a planning checkpoint to bind the Goal, active change, approved write sets, `implementation_readiness.required: false`, and the Standing Milestone External Effects Contract while preserving matching executable stage/status markers.
- [x] 1.3 Run and record characterization tests for continuation, side effects, state, runtime gates, generated artifacts, Git preflight, release sync, project refresh, and refresh-impact validation before production edits.
- [x] 1.4 Record the current source/release/runtime/marketplace/version/remote/project identities and the known absolute-build-command and legacy-parent-provenance limitations as baseline evidence.

## 2. Centralize authority-delta resolution test-first

- [x] 2.1 Add RED resolver fixtures/tests for all seven mutually exclusive decisions, deterministic precedence, bound identities, normal continuation, minimal guard, derived refresh, active owner, exact task-owned cleanup, ambiguity, technical repair, true missing authority, standing milestone coverage, invalidation, and legacy default-deny.
- [x] 2.2 Implement the pure versioned `workflow_authority_delta.py` resolver and schema so every result has stable reasons/digests and only `AWAIT_HUMAN` can contain non-empty concrete `missingAuthority` and `gateKey`; make the RED matrix GREEN.
- [x] 2.3 Adapt `workflow_side_effect_policy.py` and its policy data as a backward-compatible facade over the resolver, separating local release promotion, formal publication, Git effects, refresh, and archive without weakening existing default-deny behavior.
- [x] 2.4 Add RED state tests for atomic dual-marker writes, mismatched-marker rejection, missing-authority rejection, gate-key replay, authority grant/clear, and technical-failure non-persistence.
- [x] 2.5 Implement the single authority-gate recorder/CLI and state parser/render/validator support; make atomicity and deduplication tests GREEN.
- [x] 2.6 Add RED continuation tests proving invalid canonical evidence and implementation-readiness repair route to `FAIL_CLOSED_REPAIR`, while a current standing milestone routes declared downstream effects without another gate.
- [x] 2.7 Integrate the resolver into continuation/orchestrator decisions while preserving compatibility keys/actions, and make the focused continuation suite GREEN.
- [x] 2.8 Update Stop, doctor, hooks, review gate, pre-edit policy, and Agent Task Contract validation to consume read-only resolutions and reject fabricated Human Gates; prove those entry points make no state or external-effect writes.
- [x] 2.9 Make the sole gate recorder recover exactly one interrupted receipt-to-STATE transition through a bound write-ahead intent; reject state, Goal/change, resolver, gate-key, and receipt drift without duplicating or bypassing the gate.
- [x] 2.10 Add RED public-resolver tests for standing model execution, stable-authority mismatch, consumed/stale attempt evidence, a new same-authority attempt, actual-cost recording without a currency gate, and malformed execution identity.
- [x] 2.11 Implement stable `standingExecution` authority and ephemeral `attemptId` classification in `workflow_authority_delta.py`; preserve release-oriented standing-milestone requirements and make the new RED matrix GREEN.
- [x] 2.12 Add continuation/guidance regression coverage proving same-authority repair, refreeze, review, and retry continue automatically while a changed provider/model/account/credential privilege or acceptance boundary produces one concrete Human Gate.

## 3. Remove false cleanup and local-repair gates

- [x] 3.1 Add RED tests that an owner-exited exact task-owned candidate returns `AUTO_CLEAN`, orchestration automatically supplies the existing apply safeguard, and the terminal receipt verifies with zero `awaiting_human` writes.
- [x] 3.2 Add RED negative tests for active owners, identity/membership/plan drift, tracked/source/user/history/persistent evidence, ambiguous ownership, and non-exact or recursive deletion targets.
- [x] 3.3 Integrate authority resolution with Generated Artifact Lifecycle orchestration/CLI so safe `AUTO_CLEAN` is automatic and every ambiguous or protected case remains fail-closed; make the lifecycle matrix GREEN.
- [x] 3.4 Replace blanket deletion/technical-deviation Human-Gate wording in cleanup docs and related runtime guidance with the resolver vocabulary and exact lifecycle preconditions.

## 4. Implement the recoverable milestone and Git state machine test-first

- [x] 4.1 Add milestone standing-contract, candidate-manifest, review, effect-receipt, and terminal-receipt schemas plus RED validation tests for exact Goal/change/write-set/remote/ref/tag/channel/assets/refresh-target/exclusion binding.
- [x] 4.2 Add RED Git tests using temporary repositories and a bare remote for expected-base equality, ancestry/fast-forward proof, remote divergence, exact literal-path staging, contaminated index, reviewed-diff drift, one commit, push/readback mismatch, and no force/rebase/merge/alternate ref.
- [x] 4.3 Extend `workflow_git.py` and its CLI to expose the bound fast-forward/readback evidence and make the Git matrix GREEN without adding a broad standalone push command.
- [x] 4.4 Add RED milestone plan/advance/verify tests for ordered transitions, before/after receipts, technical stop versus missing authority, and same-identity recovery after interruption at commit and branch push.
- [x] 4.5 Implement candidate verification, exact index/commit, push preflight/push/readback, durable step receipts, and first-incomplete-step reentry in `workflow_milestone_external_effects.py` and its CLI.
- [x] 4.6 Add RED publication-boundary tests for existing identical tag/release reuse, tag collision, tag-push success with release failure, incomplete/mismatched release readback, asset SHA mismatch, one bounded remediation, and no retag/delete/overwrite/fallback.
- [x] 4.7 Implement a narrow GitHub publication adapter interface and publication readback composer; keep real GitHub mutation behind the tag-bound workflow and make the hermetic publication matrix GREEN.
- [x] 4.8 Add RED named-refresh tests for exact `dev-flow@cy-codex-skills` cache targeting, unnamed plugin/consumer refusal, project plan drift, source/release/published/cache/project mismatch, and receipt replay.
- [x] 4.9 Implement the target-specific cache plan/apply/verify adapter and five-layer receipt composer by reusing release sync and project refresh seams; make the named-refresh matrix GREEN.
- [x] 4.10 Add a dependency-ordered long-run fixture with more than 20 transitions and crash injection after each completed external step; prove zero false `AWAIT_HUMAN`, no duplicate effects, and 100% pre-mutation failure for injected ambiguity, drift, collision, or undeclared targets.
- [x] 4.11 Bind strict candidate-referenced validation/review provenance, re-read the real receipt-directory release assets at plan/reentry/verify, and classify malformed requested-effect evidence as technical repair rather than a synthetic Human Gate.
- [x] 4.12 Read candidate-contained validation and review evidence from the same trusted worktree/commit tree, require exact acyclic receipt projections, and reject duplicate-key, forged result, or non-canonical command evidence before index mutation.
- [x] 4.13 Centralize strict milestone-contract shape/evidence validation across the standing resolver and executor so malformed requested effects, refs, or unavailable declared targets stop as technical repair; reserve `AWAIT_HUMAN` for a well-formed concrete undeclared authority delta.
- [x] 4.14 Bind exact tracked deletions as first-class candidate records so the candidate payload, contract write set, literal-path index, commit tree, and reentry readback all prove the same absent paths; reject overlap, undeclared deletion, resurrection, or deletion drift as technical repair.
- [x] 4.15 Recover a cache-refresh PENDING intent that failed before the effect by revalidating and retrying only the same sealed plan, while current authoritative readback remains verify-only and duplicate-free.

## 5. Make DevFlow 0.4.0 reproducibly publishable

- [x] 5.1 Add the checked-in stable DevFlow release policy resolving non-breaking `0.3.x` capability work to version `0.4.0`, tag `dev-flow-v0.4.0`, stable channel, `origin/main`, the semantic commit message, exact assets, named refresh targets, failure/reentry policy, and exclusions.
- [x] 5.2 Update development/release plugin metadata and compatible workflow/template version surfaces to `0.4.0` without changing project schema 8 or granting existing projects standing authority.
- [x] 5.3 Add RED reproducibility tests for normalized repository-relative runtime build metadata, additive source-tree digest provenance, legacy manifest compatibility, fixed archive ordering/timestamps/modes, and byte-identical rebuilds across different Python executable paths.
- [x] 5.4 Update the runtime packager/verifier and add a deterministic full-plugin release bundle builder producing the exact declared assets; make local reproducibility and tamper tests GREEN.
- [x] 5.5 Write reviewed `dev-flow-v0.4.0.md` release notes and an exact release manifest/checksum contract that avoids self-hash and containing-commit cycles.
- [x] 5.6 Add a least-privilege, immutable-tag-bound `.github/workflows/publish-dev-flow.yml` using commit-pinned actions and only checked-in validators/packagers; reject manual version/tag/asset widening and overwrite behavior in workflow tests.
- [x] 5.7 Add publication contract tests that locally rebuilt assets match the checked-in expected manifest and that downloaded Release assets can be verified by name, size, version, tag, commit, and SHA-256.
- [x] 5.8 Make bundle cleanup validate the exact invocation-owned staging member inventory and preserve the directory on any injected, replaced, linked, or otherwise unregistered member drift.
- [x] 5.9 Remove zlib/toolchain-dependent archive bytes, bind the exact locally reviewed asset records into a checked-in non-cyclic expectation receipt, and make the tag-bound Action verify every rebuilt name/size/SHA-256 before immutable Release creation.
- [x] 5.10 Bind staging member link count and change identity so a newly added hard link is detected before cleanup and preserves the invocation-owned tree fail-closed.

## 6. Unify guidance, generated artifacts, and refresh compatibility

- [x] 6.1 Update root `AGENTS.md` and `ENGINEERING_POLICY.md` so material authority delta—not phase/action labels—triggers Human Gate, while the sealed milestone instance covers its declared commit/push/publication/refresh chain and archive remains separate.
- [x] 6.2 Update DevFlow templates for AGENTS, ENGINEERING_POLICY, STATE, OpenSpec design/tasks, task ledger, evidence, review, and Agent Task Contracts to use the centralized resolver, technical repair stop, exact `AUTO_CLEAN`, gate receipt, and milestone contract.
- [x] 6.3 Update the minimally applicable DevFlow skills and references—feature intake, technical/change planning, execute task, orchestrator, doctor, verify, refresh, project migration, and updater—without creating another planner, queue, or mutation path.
- [x] 6.4 Update Git/release/side-effect/cleanup documentation and correct stale repository/state paths while preserving compatibility aliases and Actions-first routing.
- [x] 6.5 Advance Project Refresh Impact to revision 10 with `impact: changed`, schema decision `managed-refresh`, schema head 8, immutable authority/milestone compatibility fixtures, generated-guidance markers, required-input digests, and legacy default-deny/no-history-cleanup coverage.
- [x] 6.6 Regenerate the DevFlow runtime and promote the entire allowlisted development plugin to `plugins/dev-flow/` through the canonical release writer before candidate freeze; verify source/release/runtime parity and that no post-push sync would write bytes.
- [x] 6.7 Update root policy, generated templates, and the minimally applicable execution/orchestration skills so model cost is recorded rather than repeatedly confirmed and non-blocking related improvements are deferred and summarized without leaving the critical path.
- [x] 6.8 Advance Project Refresh Impact to revision 11 for the changed generated guidance/runtime, regenerate the release through the canonical writer, and verify source/release/runtime parity without installing or refreshing any project.

## 7. Integrated verification and independent review

- [x] 7.1 Run all focused resolver, state, continuation, runtime-gate, cleanup, Git, milestone, publication, release, project-refresh, and refresh-impact suites from source and generated release; resolve every required failure within the approved write set.
- [x] 7.2 Run fresh broad DevFlow unit discovery, pre-promotion tests, release runtime verification, strict change/all OpenSpec validation, workflow validator/doctor checks, and `git diff --check`; record exact commands, exit codes, and digests.
- [x] 7.3 Run release-target Plugin Eval against `plugins/dev-flow`, record score/findings/decisions, fix all P0/P1 and required actionable plugin findings, and rerun until the declared gate passes.
- [x] 7.4 Run source/release parity, refresh-impact validation, long-run simulation, secret scan, unexpected/untracked candidate scan, and candidate payload manifest generation; prove the candidate exactly equals the intended write set.
- [x] 7.5 Validate a read-only independent reviewer Agent Task Contract bound to the exact candidate/review digest, obtain the review receipt, resolve all P0/P1 findings, and repeat validation/review until P0=0 and P1=0 with no diff drift.
- [x] 7.6 Freeze the final candidate manifest, release assets, notes, validation receipts, Plugin Eval result, independent review receipt, exact index expectation, and standing contract; rerun the no-drift preflight immediately before mutation.
- [x] 7.7 Run fresh focused and broad tests, strict OpenSpec validation, workflow validator/doctor, parity, refresh-impact validation, Plugin Eval, secret/unexpected-file checks, and `git diff --check` for the amended candidate.
- [x] 7.8 Obtain a new independent read-only P0/P1 review and refreeze the amended exact candidate; the prior candidate/review/standing digests remain historical and MUST NOT authorize mutation.
- [x] 7.9 Apply decision `HG-BASELINE-9366E8A-001`: reconstruct the candidate on exact base `9366e8ae63752a9ce86bd52a814233ca74edc16e` without merge/rebase/force, reconcile the ten overlapping paths, rerun all Task 7.7 evidence and both Task 7.8 review axes, then refreeze and re-read the replacement standing identity before any index mutation.

## 8. Execute the preauthorized milestone external effects

- [x] 8.1 Stage only the frozen candidate, verify the index manifest is exact and secret/blocker-free, create one `feat(dev-flow): centralize authority-delta execution` commit, and record commit/tree readback.
- [x] 8.2 Revalidate `origin`, `refs/heads/main`, expected base, and fast-forward ancestry; push exactly the candidate commit without force and require remote branch readback to equal it.
- [x] 8.3 Verify the tagged commit contains the reviewed publication workflow/assets contract, prove no conflicting tag/release exists, create/push immutable `dev-flow-v0.4.0`, and read back its exact commit.
- [x] 8.4 Observe the canonical GitHub Actions publication, perform at most the contract's one same-identity diagnosis/remediation if needed, and require public Release/tag/version/state/asset name/size/SHA-256 readback before any refresh.
- [x] 8.5 Fast-forward only the named clean DevFlow source checkout to the published commit, refresh only `dev-flow@cy-codex-skills`, and record target-specific marketplace/cache plan/apply/verify receipts.
- [x] 8.6 Run project migration plan/apply/verify only for `/Users/cy/Dev/agents-dev/cy-codex-skills`, then prove source/release/published/cache/project five-layer identity and terminal milestone receipt consistency.

## 9. Completion evidence without archive

- [x] 9.1 Freeze tracked workflow state before the reviewed commit with matching `external_effects` stage/status and current standing/evidence digests; after commit, treat the verified terminal receipt as authoritative completion evidence without creating a second tracked diff/commit. Prove zero unresolved blockers, zero false Human Gates, and no duplicate effects.
- [x] 9.2 Report the milestone commit, remote branch/tag readbacks, GitHub Release and asset hashes, cache/project refresh receipts, five-layer identities, validation/Plugin Eval/review results, compatibility impact, and residual risks; do not create a PR, merge, force-push, archive the change, or refresh an unnamed consumer.
