# OpenSpec 1.7 Implementation, Submission, and Refresh Evidence

## Authorization and Scope

- On 2026-08-04 the user explicitly authorized committing the reviewed upgrade
  to the remote and completing the local refresh.
- Authorized effects: scoped commits on verified `main`, native Git push to
  `origin/main`, refresh of only `dev-flow@cy-codex-skills`, and refresh of this
  project's exact six OpenSpec skills.
- Excluded effects: PR, GitHub Release publication, archive, broad updater
  apply, project migration, legacy cleanup, force-push, unrelated plugin/project
  mutation, and the separate `DF-IFL-010` repair.
- The pre-existing 40-line edit in
  `openspec/changes/separate-git-transport-from-github-auth/evidence/implementation.md`
  is user WIP and is excluded from every commit in this change.

## Verified Implementation Baseline

- OpenSpec change implementation: 25/25 tasks complete before submission
  follow-through; four authorized submission/refresh tasks were then appended.
- OpenSpec CLI: exact `1.7.0`; Node: `24.13.0`; six current-project skills:
  exact 1.7 batch; Codex command files: none.
- Release runtime before implementation commit: verified across 132 source
  records, archive SHA-256
  `fed5629637f0a11df36426b9efd9cf99e5d5e5de97cb4d27a65df7dad0e34470`,
  source receipt `29384ef094035c932ed85ef068ba09b9f05d4638`.
- Release-target Plugin Eval: 86/B, zero failures, three established static
  token-budget warnings covered by `DF-IFL-001`.

## Fresh Commit Gate

```text
PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest discover -s dev/plugins/dev-flow/tests -q
444 run / 444 passed

PYTHONDONTWRITEBYTECODE=1 python3.12 dev/scripts/run_devflow_prepromotion_tests.py
408 run / 408 passed across 22 modules; zero skips

OPENSPEC_TELEMETRY=0 openspec validate --all --strict --json
58 items / 58 passed

python3.12 dev/plugins/dev-flow/scripts/lint_ai_plan.py openspec/changes/upgrade-devflow-openspec-1-7/design.md
pass

python3.12 -B plugins/dev-flow/scripts/verify_release_runtime.py --plugin-root plugins/dev-flow --repo-root . --json
verified; 132 source records

git diff --check
pass
```

## Native Git Transport Preflight

- Remote: `origin`, `git@github.com:cYz26/cy-codex-skills.git`, SSH transport.
- Local `main`: `29384ef094035c932ed85ef068ba09b9f05d4638`.
- Remote `origin/main`: `29384ef094035c932ed85ef068ba09b9f05d4638`.
- Divergence: 0 ahead / 0 behind before commit.
- `git_transport_preflight.py`: `GIT_TRANSPORT_READY`; no `gh` dependency and
  no push attempted by the probe.

## Submission Receipts

- Reviewed staged set: 22 paths; scoped root/source/release assets, 86% test
  rename, canonical change, and ledger only. `git diff --cached --check`
  passed; `.planning/**`, the unrelated Git-transport evidence edit, and the
  four deterministic runtime outputs were absent. Task 8.1 passed.
- Implementation commit: `7059c06` (`feat(devflow): upgrade OpenSpec
  integration to 1.7`), 22 reviewed paths, task 8.2 passed.
- Generated runtime gate: the fresh source receipt recorded SHA-256
  `668cc7193f5e4bd79118905ebac14c85d83d83ce7336fddb18bbb9b4935ce219`;
  one target-bound authorization was consumed and reset closed.
- Generated runtime readback: source commit
  `7059c06d7fcb2a94ee659c7657fc9aa17a7061d2`, archive SHA-256
  `fed5629637f0a11df36426b9efd9cf99e5d5e5de97cb4d27a65df7dad0e34470`,
  290/290 runtime checks, packaged 6/6, release discovery 66/66, release sync
  `current`, and Plugin Eval 86/B with zero failures. Receipt commit and native
  push remain pending task 8.3.
- Targeted local refresh and closeout push/readback: pending task 8.4.

## Residual Findings

- `DF-IFL-001`: established whole-plugin static token budgets remain
  `DEFER_AND_CONTINUE` and do not block this release compatibility change.
- `DF-IFL-010`: separate self-hosting root-identity repair remains
  `DEFER_AND_CONTINUE`; no follow-up work is authorized here.
