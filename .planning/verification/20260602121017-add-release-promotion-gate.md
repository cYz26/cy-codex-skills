# Verification: Release Promotion Gate

created_at: 2026-06-02T12:10:17+08:00

## Scope

Implemented the DevFlow release promotion gate for dev-to-release plugin and
standalone skill sync, plus release-first Plugin Eval target resolution.

## Summary

- Added `workflow_release_sync.py` for release asset discovery, allowlist-based
  drift detection, apply-mode copying, custom build commands, managed outputs,
  and release-preferred eval target resolution.
- Added `sync_release_assets.py` for explicit dry-run/apply and eval-target
  resolution.
- Added `release_promotion_gate.py` and registered it in the DevFlow Stop hook
  after verification policy and before checkpoint policy.
- Added DevFlow `release-sync.json` metadata so release sync packages
  `devflow_runtime.pyz` instead of copying raw dev script modules.
- Updated release-isolation docs, development README files, and the AGENTS
  template with release-first Plugin Eval guidance.
- Regenerated the DevFlow release runtime archive and wrappers.

## Validation Commands

```text
python3 -m unittest dev/plugins/dev-flow/tests/test_release_sync.py
result: pass, 6 tests

python3 dev/plugins/dev-flow/scripts/sync_release_assets.py --json
result: pass, status=current after apply

python3 dev/plugins/dev-flow/scripts/sync_release_assets.py --apply --json
result: pass, status=synced, DevFlow build command exit 0

python3 dev/plugins/dev-flow/scripts/sync_release_assets.py --eval-target dev/plugins/dev-flow --json
result: pass, target=/Users/cY/dev/skills/cy-codex-skills/plugins/dev-flow, releasePreferred=true

python3 -m unittest discover -s dev/plugins/dev-flow/tests
result: pass, 114 tests

python3 -m unittest discover -s plugins/dev-flow/tests
result: pass, 4 tests

openspec validate add-release-promotion-gate --strict
result: pass

openspec validate --all --strict
result: pass, 32 items

git diff --check
result: pass
```

## Plugin Eval

- `node /Users/cY/.codex/plugins/cache/openai-curated/plugin-eval/45fe2bdd/scripts/plugin-eval.js analyze plugins/dev-flow --format markdown`
  - result: exit 0, score 91/100, grade B, risk medium
  - findings: 0 fail, 2 warn, 2 info
  - remaining warnings: `invoke_cost_tokens` and `deferred_cost_tokens` are
    still heavy relative to baseline; coverage artifacts are unavailable.

## Deferrals

- Release token-budget warnings are pre-existing and should be handled by a
  dedicated budget-reduction follow-up. They are not caused by the release
  promotion gate.
- Coverage artifacts were not generated for Plugin Eval coverage scoring.

## Residual Risks

- The release promotion gate syncs at verified stop boundaries and then asks
  for release validation; agents must still run release tests and Plugin Eval
  before commit readiness.
