# Standing Goal Execution Authority System Repair Verification

- recorded_at: `2026-08-09T19:12:23Z`
- change: `centralize-devflow-authority-delta`
- scope: separate durable Goal-level model execution authority from ephemeral
  attempt receipts; record actual monetary cost without a repeated currency
  gate; automatically repair, refreeze, review, and retry within unchanged
  authority; defer non-blocking related optimization.
- external_effects: none. The canonical local source-to-release writer refreshed
  the generated `plugins/dev-flow` mirror inside this worktree. No model call,
  credential use, install, cache refresh, project refresh, migration, Git index
  mutation, commit, push, tag, public release/publication, archive, or cleanup
  ran.

## TDD and implementation evidence

- RED evidence covered standing model execution, stable-authority mismatch,
  consumed/stale attempt evidence, new same-authority attempts, malformed
  execution identity, contextual side-effect policy, unbound legacy tokens,
  public guidance, and Project Refresh revision 11.
- Focused GREEN suites passed 67 core/methodology tests and 57
  authority/continuous-execution tests before broad verification.
- The stable envelope binds `taskId`, provider, model, credential policy, cost
  policy, and serial execution policy. `attemptId` remains receipt-only and
  does not consume the human grant.
- A stable provider/model/account/credential-privilege or acceptance-boundary
  change returns one concrete `AWAIT_HUMAN`; malformed/stale attempt evidence
  returns technical repair, and safe optional work returns
  `DEFER_AND_CONTINUE`.

## Fresh task 7.7 verification

| Check | Result |
|---|---|
| `PYTHONDONTWRITEBYTECODE=1 python3.12 dev/scripts/run_devflow_prepromotion_tests.py` | PASS, 739/739 |
| `PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_*.py'` | PASS, 801/801 |
| `PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest discover -s plugins/dev-flow/tests -p 'test_*.py'` | PASS, 60/60 |
| bundle and asset-expectation focused discovery | PASS, 32/32 |
| `openspec validate --all --strict` | PASS, 34/34 |
| workflow state validator | PASS, zero issues/warnings |
| workflow doctor | PASS, `healthy`, no repair needed |
| release runtime verifier | PASS, 321/321 checks |
| release runtime archive | `sha256:34a9e36a2760b9edfec35f789caa0f6829c942fab2074a350216d70475a8ce81` |
| source/release dry-run | `current`, zero changed/missing/stale/deleted paths |
| Project Refresh Impact | PASS, revision 11/schema head 8, `managed-refresh`, source/release digest `sha256:f481fa1ce3ac31f266f3309f1f990f38270d59a94c3154ae6b38353b355f4066`, tracked-input `sha256:57bfaaf0373fdfc7cfa73e31d8318d91779c40cd0a8288a5fd2faa10a824f727` |
| deterministic bundle build | PASS, exactly seven assets, asset-set `sha256:ecf9ee542bd49d13736f0fca12e0418b36d92e5ae2f54eed0736b77c1a149db0` |
| secret scan | PASS, 158 files scanned, zero findings |
| Stop/continuation decision | `CONTINUE_NEXT_ITEM`, zero `missingAuthority`, no `gateKey` |
| `git diff --check` | PASS |

## Plugin Eval disposition

- Release target: `plugins/dev-flow`
- Result: 86/B, medium static risk, zero failures, three warnings and two
  informational findings.
- Static estimates: trigger 436, invoke 17,093, deferred 57,124, active
  17,529 tokens; no observed-usage sample.
- Every skill remains in the evaluator's good line-count range. The findings
  are confined to whole-plugin static token budget and optional coverage data;
  there is no reported behavior, runtime, structural, or security failure.
- Disposition: the three whole-plugin static budget warnings are
  `DEFER_AND_CONTINUE` under `DF-IFL-001`; one bounded reduction to the already
  authorized `project-orchestrator` brought invoke cost below the excessive
  threshold. A broader portfolio rewrite or observed-usage benchmark would
  expand this milestone. No P0/P1, runtime, security, or publication-safety
  finding remains.

## Task 7.8 amended review and exact freeze

- The prior frozen candidate, validation, review, and standing digests are
  historical and authorize no mutation.
- The standing contract now names the complete intended amended write set,
  including `TASK_LEDGER.md`, both revision-11 fixtures, and this verification
  record. Source/release parity and the new seven-asset set are exact; the old
  receipt-directory asset set was preserved under its historical sibling path.
- Both validated read-only reviewer contracts independently matched the exact
  amended `155 present + 1 deletion` snapshot
  `sha256:92311258eae1b59721bd25b0cfb036a4b5968240856803d35a85bb0ca04f200c`.
  Spec and Standards axes both returned P0=0 and P1=0 with no repository write
  or external effect.
- The refrozen candidate payload digest was
  `sha256:a6995284984fe8adf78973a49e7a9e9dc47dcb2a263c5966988b368cdd55a40e`.
  Its canonical acyclic projection digests matched STATE exactly: candidate
  `7192967ce66b4fe12c738b95b8544b27c9a20027d4d893e9f148555f537477cf`,
  validation `dc9e7bd4e7b38d8b08c374dd4bb948c4a7554a32ddfab9cada07d392dd892738`,
  and review `8ae85f1379fd7a5bb2f3fa6ffb5c74462ff7527f0b7c681d90c86f4fab2958b0`.
- The public milestone plan returned `READY` with plan digest
  `sha256:06d5bfdaefe1341f44ab43d33ccf734652847fbbfa801e75d46ac3157ab1c99b`;
  the central resolver returned `CONTINUE` for exact effect `git.commit` and
  target `origin:refs/heads/main`, with no missing authority or gate key.

## Fail-closed transport boundary

- Before any index mutation, native Git transport readback returned
  `GIT_TRANSPORT_BLOCKED/remote_commit_mismatch`: the standing contract expected
  `f8f42cd208a6b15ab415025f6fd62f003178d77e`, while both local `main` and
  `origin/main` resolve to `9366e8ae63752a9ce86bd52a814233ca74edc16e`.
- The upstream range changes 34 paths and overlaps the frozen candidate on ten
  paths, including STATE, release verification, the task ledger, migration
  metadata/tests, release smoke tests, and runtime provenance. That invalidates
  the reviewed base and requires a new exact rebaseline, validation, review,
  freeze, preflight, and resolver pass.
- The now-stale candidate/validation/review/standing digests are retained only
  as historical evidence. STATE disables standing authority and
  `release_allowed`; no awaiting marker was written because this is evidence
  drift, not fabricated missing authority. No stage, commit, push, tag,
  publication, refresh, migration, archive, or other external mutation ran.

## Exact-base authority promotion

- Gate `sha256:ffae4a986d53a71919fef19cfcc9ec35bc651220ca78b109b30c949b4c7bbb18`
  identified the concrete missing authority `standing_milestone.contract` after
  the reviewed base changed. The user approved decision
  `HG-BASELINE-9366E8A-001`, which replaces only `repository.expectedBase` with
  `9366e8ae63752a9ce86bd52a814233ca74edc16e` and requires exact reconciliation,
  Task 7.7 validation, both Task 7.8 review axes, refreeze, and pre-mutation
  readback. Merge, rebase, force-push, PR, archive, and unnamed refresh remain
  excluded.
- The DevFlow project-migration read-only plan is
  `sha256:23d8ba4a2f61a545f97b46ebf62d2da6a857612f6f38c38b593b5af337beb109`:
  `migration_pending`, schema 8/8, zero planned actions and empty write set.
  No migration apply ran; the named project refresh remains downstream of
  verified publication as declared by the milestone contract.

## Exact-base Task 7.7 revalidation

- HEAD and index base are exactly
  `9366e8ae63752a9ce86bd52a814233ca74edc16e`; no merge, rebase, reset,
  stash, force, or index mutation was used to reconcile the approved overlap.
- Fresh exact-base suites passed: milestone 79/79, pre-promotion 739/739,
  development 801/801, release 60/60, bundle 26/26, and milestone-contract
  6/6. OpenSpec strict validation passed 34/34; validator/doctor, runtime
  321/321, source/release parity, release asset verification, and
  `git diff --check` all passed.
- Release-target Plugin Eval returned 86/B with zero failures. The three token
  budget warnings and two informational findings retain the bounded
  dispositions above; release invoke cost is 17,093 and no P0/P1, runtime,
  security, or publication-safety finding remains.
- Project Refresh revision 11 is current at schema head 8 with contract digest
  `sha256:f4a68a8e345f058955633af474ff1ced0e3c1bbd1ce90e1edb38d828473cf9aa`
  and tracked-input digest
  `sha256:d150af3690a925d75373b97f4c21d595afbf83357ce6c7bc15b6fd543b663c5a`.
  The deterministic seven-asset set is
  `sha256:ed304161de2dc7bd3364a7f38aff562de962dac75fa5d5910018ea95757e5d50`;
  runtime remains
  `sha256:34a9e36a2760b9edfec35f789caa0f6829c942fab2074a350216d70475a8ce81`.
- Task 7.8 review found that source/release `codex-updater/SKILL.md` were outside
  the exact ten-path rebaseline grant. Both were restored to the approved base
  and removed from the standing write set. A focused RED/GREEN guard now
  preserves the exact remote-advancement authority phrase; the bounded token
  repair touched only the already-authorized source/release
  `project-orchestrator/SKILL.md` paths.
- The standing contract remains `declared`; all prior candidate, validation,
  review, and standing digests are historical until the repeated Task 7.8
  review and exact refreeze complete.

## Final Task 7.8 dual-axis review

- The validated read-only reviewer contracts independently matched snapshot
  `sha256:edb456f1424325105434e1b97d80151f02b8f667e49e6b1912f8ed4aa5cd6df5`
  with 156 present files and the exact packaged-runtime deletion. Both Spec
  and Standards axes returned P0=0 and P1=0.
- Candidate payload `335dfd5e5de9e63f35f633e06bf66f91859c3951ce7b92ddb5620983b6fdaefb`,
  evidence references, standing write set, ten-path rebaseline overlap, and
  seven-asset set were exact. Reviewer before/after status SHA was
  `e814c9940130a1d6633c3d5cbc5c3e1bcca19cedb3ba28bef949d2e7ed728843`
  with no writes, credentials, network access, or external effects.
- Task 7.9 is complete. The primary agent may now perform only the deterministic
  exact refreeze and central resolver readback; Task 8 remains the next
  dependency boundary and no external effect has run in this verification step.
