# Verification: DevFlow Release Runtime Packaging

created_at: 2026-06-02T11:41:03+08:00

## Scope

Prepared the local DevFlow release runtime packaging changes for commit.

## Summary

- Release runtime scripts are packaged into `plugins/dev-flow/scripts/devflow_runtime.pyz`.
- Release entrypoint scripts load modules through `devflow_launcher.py`.
- The runtime archive was regenerated from `dev/plugins/dev-flow/scripts` and
  verified to match all 96 development source scripts byte-for-byte.
- `plugins/dev-flow/hooks.json` was normalized back to the same formatted
  content as `dev/plugins/dev-flow/hooks.json` so hook formatting is not part
  of this commit.

## Validation Commands

```text
python3 dev/scripts/package_devflow_release_runtime.py
result: pass

python3 - <<'PY'
from pathlib import Path
import zipfile
root=Path.cwd(); dev=root/'dev/plugins/dev-flow/scripts'; archive=root/'plugins/dev-flow/scripts/devflow_runtime.pyz'
with zipfile.ZipFile(archive) as z:
    names=set(z.namelist())
    missing=[p.name for p in sorted(dev.glob('*.py')) if p.name not in names]
    diff=[p.name for p in sorted(dev.glob('*.py')) if p.name in names and p.read_bytes()!=z.read(p.name)]
    extra=sorted(n for n in names if not (dev/n).exists())
print({'archive_entries': len(names), 'missing': missing, 'different': diff, 'extra': extra})
PY
result: pass; archive_entries=96, missing=[], different=[], extra=[]

python3 -m py_compile dev/scripts/package_devflow_release_runtime.py plugins/dev-flow/scripts/devflow_launcher.py
result: pass

python3 -m unittest discover -s dev/plugins/dev-flow/tests
result: pass, 108 tests

python3 -m unittest discover -s plugins/dev-flow/tests
result: pass, 4 tests

python3 plugins/dev-flow/scripts/plugin_project_migration.py --repo /Users/cY/dev/skills/cy-codex-skills --json
result: pass; status=current

python3 plugins/dev-flow/scripts/validate_workflow_state.py --repo /Users/cY/dev/skills/cy-codex-skills --json
result: pass

openspec validate --all --strict
result: pass, 31 items

git diff --check
result: pass
```

## Plugin Eval

- `node /Users/cY/.codex/plugins/cache/openai-curated/plugin-eval/45fe2bdd/scripts/plugin-eval.js analyze plugins/dev-flow --format markdown`
  - result: exit 0, score 91/100, grade B, risk medium
  - findings: 0 fail, 2 warn, 2 info
  - remaining warnings: `invoke_cost_tokens` and `deferred_cost_tokens` are
    still heavy relative to baseline; coverage artifacts are unavailable.
- `node /Users/cY/.codex/plugins/cache/openai-curated/plugin-eval/45fe2bdd/scripts/plugin-eval.js analyze dev/plugins/dev-flow --format markdown`
  - result: exit 0, score 77/100, grade C, risk high
  - findings: 1 fail, 2 warn, 2 info
  - remaining findings: development tree deferred token budget is excessive,
    invoke budget is heavy, and Python complexity remains high.

## Deferrals

- Development-tree Plugin Eval findings are deferred because
  `dev/plugins/dev-flow` intentionally contains full source, tests, and support
  files. The commit prepares the optimized release package under
  `plugins/dev-flow`, which now evaluates at 91/100.
- Release package token-budget warnings remain and should be handled by a
  dedicated follow-up if further budget reduction is required.
- No coverage artifact was generated for Plugin Eval coverage scoring.

## Residual Risks

- OpenSpec archive gate remains closed in `.planning/STATE.md`.
- External callers that imported non-entrypoint files directly from
  `plugins/dev-flow/scripts` must move to CLI entrypoints or the packaged
  runtime behavior.
