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
  follow-through; the four authorized submission/refresh tasks are now also
  complete, for 29/29 total.
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
  `current`, and Plugin Eval 86/B with zero failures.
- Runtime receipt commit: `49bb13f` (`chore(devflow): bind OpenSpec 1.7 runtime
  receipt`). Native SSH push advanced `origin/main` from `29384ef` through
  `49bb13f`; `git ls-remote`, fetch, and divergence readback proved local and
  remote `main` equal at 0 ahead / 0 behind. Task 8.3 passed.
- The verified ChatGPT.app Codex CLI refreshed only
  `dev-flow@cy-codex-skills` version `0.3.0+codex.20260529145038` under
  `/Users/cY/.codex`. Cache and release runtime archives byte-match at SHA-256
  `fed5629637f0a11df36426b9efd9cf99e5d5e5de97cb4d27a65df7dad0e34470`;
  both source receipts equal `7059c06d7fcb2a94ee659c7657fc9aa17a7061d2`.
- Current-project activation dry-run selected only the exact six OpenSpec copy
  refreshes. Apply regenerated them in isolated temporary Codex/XDG homes,
  verified exact OpenSpec `1.7.0`, and returned `current` because every project
  copy was already byte-current. All 16 DevFlow skills remained linked; no
  command file, migration, legacy cleanup, or unrelated project write ran.
- Post-refresh readback: OpenSpec `1.7.0`, Node `24.13.0`, six project skills
  stamped `generatedBy: "1.7.0"`, `.codex/commands/openspec` absent, project
  migration and official skill layout `current`, workflow validation clean,
  Doctor healthy, and remote/local parity 0/0 at `49bb13f` before this final
  closeout receipt.
- Global OpenSpec configuration stayed byte-identical at SHA-256
  `1cfa273ff52c007ed07478ebfd47942ce005324b08776b8c00b16a6e5271cb5b`.
  The tracked project `openspec/config.yaml` also equals HEAD at SHA-256
  `7f64d2448e1c83ffa6f2f3398b742fb5f2d4d3ea47b2c540a9076484977026b4`.
  The authorized named `codex plugin add` rewrote `/Users/cY/.codex/config.toml`
  from its pre-refresh byte hash to
  `031f405defb3f8e9d4ef68e959e2fb6bff6378b496ed7a47bfbeb6c7329af5d3`;
  this is recorded as the plugin-registration side effect, not misreported as
  an OpenSpec generator or project-config mutation.
- Task 8.4 is complete. This tasks/evidence/ledger update is the scoped final
  closeout receipt; its immutable commit and post-push remote readback are
  reported in the operator handoff to avoid a self-referential receipt chain.

## Residual Findings

- `DF-IFL-001`: established whole-plugin static token budgets remain
  `DEFER_AND_CONTINUE` and do not block this release compatibility change.
- `DF-IFL-010`: separate self-hosting root-identity repair remains
  `DEFER_AND_CONTINUE`; no follow-up work is authorized here.
