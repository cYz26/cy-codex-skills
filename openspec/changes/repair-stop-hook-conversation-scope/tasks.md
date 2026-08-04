## 1. Capability Evidence and Approved Contract

- [x] 1.1 Reproduce the repeated Stop block with both
  `stop_hook_active: false` and `stop_hook_active: true`, and confirm the
  current entrypoint consumes only `cwd`.
- [x] 1.2 Confirm current official Stop fields, automatic-continuation
  semantics, ephemeral side-fork behavior, and the absence of a stable
  side/parent Hook field.
- [x] 1.3 Record the Full OpenSpec proposal, delta spec, design, Skill Routing
  Ledger, Goal Suitability Gate, test seam, write set, rollback, and zero Open
  Questions.

## 2. Public RED Contract

- [x] 2.1 Add public `devflow_stop_hook.main()` tests proving reentrant and
  explicitly ephemeral payloads currently emit an incorrect block and call
  repository checks.
- [x] 2.2 Add public entrypoint coverage proving durable and legacy payloads
  still enforce the current first-stop contract and `--json` remains an
  independent diagnostic surface.
- [x] 2.3 Add a Workflow Doctor contract test for a structured Stop-hook
  protocol report, run the focused command against old production code, and
  record the exact RED failures.

## 3. Scope Policy and Hook Integration

- [x] 3.1 Implement a pure Stop applicability classifier with precedence for
  already-continued turns, explicitly null transcript paths, durable paths,
  and legacy omitted fields.
- [x] 3.2 Integrate the classifier before repository inspection in normal Hook
  mode while preserving current response JSON, continuation precedence,
  read-only behavior, and manual `--json` diagnostics.
- [x] 3.3 Add the literal protocol invariant matrix to Workflow Doctor and make
  any failed invariant produce `needs repair` plus an actionable issue.
- [x] 3.4 Update DevFlow Hook contract and README guidance with the one-shot and
  durable-conversation applicability boundary.

## 4. Focused and Original-Reproduction Verification

- [x] 4.1 Run the public Stop/continuous-execution/Doctor tests to GREEN and
  prove repository checks are not called for reentrant or ephemeral payloads.
- [x] 4.2 Re-run the original synthetic payload pair and confirm the first
  durable Stop blocks once while a subsequent `stop_hook_active: true` Stop is
  silent.
- [x] 4.3 Run focused checkpoint and runtime-gate compatibility tests and
  inspect the implementation diff for scope or response-schema drift.

## 5. Integrated Source Proof and External-Effect Boundary

- [x] 5.1 Run the complete source-only DevFlow suite, strict change/repository
  OpenSpec validation, workflow validation, Doctor, and `git diff --check`.
- [x] 5.2 Run release-target Plugin Eval plus development-path diagnostics,
  classify findings, and run the read-only source/release/cache updater report.
- [x] 5.3 Record fresh verification evidence, review every changed path, update
  this checklist and `.planning/devflow/STATE.md`, and preserve the unrelated
  Git-transport evidence edit.
- [x] 5.4 Stop before generated release sync, installed-cache refresh, archive,
  commit, push, PR, publication, or unrelated mutation; report the exact
  separately authorized next action.

## Execution Ledger

| Slice | Owner | Write Set | Required Evidence | Human Gate | Status |
|---|---|---|---|---|---|
| Evidence and plan | main | this OpenSpec change | official/local capability ledger and valid artifacts | none | done |
| Public RED contract | main | focused DevFlow tests | observed entrypoint and Doctor RED | none | done |
| Scope policy and Doctor | main | development scripts, tests, README, hook contract | focused GREEN and unchanged response schema | schema/dependency/scope expansion only | done |
| Integrated source proof | main | source verification record, this change, DevFlow state | complete source suite, validators, Eval/drift report, diff review | release/cache/archive/commit/push remain separate | done |

Execution policy is `auto-until-terminal`. No subagent is authorized or needed;
the main agent owns all shared OpenSpec, runtime, test, documentation, evidence,
and state paths.
