# Slice 1 Baseline Evidence

Captured: 2026-07-10 (Asia/Shanghai)

## Toolchain

```text
Python 3.12.13
OpenSpec 1.5.0
Node v24.13.0
git 2.50.1 (Apple Git-155)
source commit 63b4c0995ac9c4fcf56e8a690f674290d8d1a394
```

## Development Test Baseline

Command:

```bash
python3.12 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_*.py' -v
```

Result: `Ran 218 tests in 29.169s` and `OK`.

## Dependency and Provider Baseline

Command:

```bash
python3.12 dev/plugins/dev-flow/scripts/check_dependencies.py \
  --plugin-root dev/plugins/dev-flow --repo . \
  --codex-home /Users/cY/.codex \
  --config /Users/cY/.codex/config.toml --json
```

Current JSON status summary:

```json
{
  "ok": false,
  "status": "missing_required",
  "openspec": {
    "expectedVersion": "1.5.0",
    "installedVersion": "1.5.0",
    "status": "verified"
  },
  "gsd-core": {
    "expectedVersion": "1.6.1",
    "installedVersion": "1.6.0",
    "status": "dependency_drift",
    "required": true
  },
  "superpowers": {
    "version": "6.1.1",
    "sourceChannel": "openai-curated-remote",
    "status": "superpowers_hook_missing",
    "sessionStartHookPresent": false
  }
}
```

The report currently makes GSD drift a required failure and infers a missing
Superpowers SessionStart hook from version rather than the selected manifest.
Both are intended RED behaviors for this change.

The local GSD runtime smoke command succeeds, but `.codex/gsd-core/VERSION` is
`1.6.0`. Root planning markers include `.planning/STATE.md` and
`.planning/ROADMAP.md`. The DevFlow state frontmatter currently contains
`workflow_version`, `project_mode`, `current_stage`, `current_phase`,
`current_change`, `gates`, `context_management`, `goal_gate`, and
`context_health`, demonstrating the root-state ownership collision described
in the design.

## Release Plugin Eval Baseline

Resolved target: `plugins/dev-flow` (`releasePreferred: true`).

Resolved evaluator:

```text
selector=openai-curated
script=/Users/cY/.codex/plugins/cache/openai-curated/plugin-eval/bd2122cb/scripts/plugin-eval.js
sha256=6013d9b280e3ca76de00f6269937650867d991ae6455fdd8d853b38c2382c563
```

Result:

```text
Score: 86/100
Grade: B
Risk: medium
Checks: 0 fail, 3 warn, 2 info
trigger_cost_tokens: 332
invoke_cost_tokens: 14202
deferred_cost_tokens: 20260
explicit_only_invoke_cost_tokens: 784
total_tokens: 34794
observed usage: not supplied
```

All three warnings are static token-budget warnings. Observed-use benchmarking
remains unverified and is handled by Slice 7; no external benchmark was run.

Warning identifiers captured before release changes:

- `trigger_cost_tokens-budget-high`
- `invoke_cost_tokens-budget-high`
- `deferred_cost_tokens-budget-high`

## RED Evidence

Command:

```bash
python3.12 -m unittest dev/plugins/dev-flow/tests/test_provider_profiles.py -v
```

Result: 11 tests ran and all 11 failed with the expected assertion
`provider facade module must exist`. There were no syntax, import-time, or
fixture errors. The failures cover core/none independence, strict/roadmap
orthogonality, manifest-driven hooks, ambiguous sources, lean Matt mappings,
selection-scoped GSD readiness, activation side effects, goal on-demand
readiness, and evidence/readiness separation.

Preserved characterization command:

```bash
python3.12 -m unittest \
  dev/plugins/dev-flow/tests/test_dependencies.py \
  dev/plugins/dev-flow/tests/test_runtime_gates.py \
  dev/plugins/dev-flow/tests/test_release_smoke.py -v
```

Result: `Ran 94 tests in 19.182s` and `OK` after the new test fixtures were
added. Existing OpenSpec, dry-run, user-file protection, strict developer gate,
and packaged behavior remain green at the RED boundary.
