# Checkpoint: default-plugin-eval-remediation verification passed

Date: 2026-06-01

## Scope

Added a remediation-first Plugin Eval policy for plugin and skill work.

Completed behavior:

- Root `AGENTS.md` now says Plugin Eval findings default to fixing or
  optimization before completion.
- DevFlow development and release `AGENTS.md` templates carry the same policy.
- Deferral is documented as an exception for out-of-scope, destructive/risky,
  dependency or architecture decision, or explicit user-approval cases.
- Deferred findings must record reason, residual risk, and follow-up path.
- OpenSpec `default-plugin-eval-remediation` records the policy contract.

## Changed Files

- `AGENTS.md`
- `.planning/STATE.md`
- `.planning/checkpoints/2026-06-01-verification_passed-default-plugin-eval-remediation.md`
- `.planning/phases/01-foundation/VERIFICATION.md`
- `.planning/verification/20260601081108-default-plugin-eval-remediation.md`
- `dev/plugins/dev-flow/assets/templates/AGENTS.md.template`
- `plugins/dev-flow/assets/templates/AGENTS.md.template`
- `dev/plugins/dev-flow/tests/test_project_orchestrator.py`
- `openspec/changes/default-plugin-eval-remediation/`

## Verification

- Focused Plugin Eval gate test: failed before instruction updates, passed
  after updates.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s dev/plugins/dev-flow/tests`: pass, 72 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s plugins/dev-flow/tests`: pass, 22 tests.
- `openspec validate --all --strict`: pass, 17 items.
- Dev and release plugin preflight checks: pass.
- `git diff --check`: pass.
- Plugin Eval for release and dev plugin roots: score 77/100, grade C, risk high.

## Remaining Risks

- Full-plugin deferred token budget and invoke token budget remain high.
- Python complexity remains high.
- These are deferred because fixing them requires a separate packaging and
  helper-script refactor outside this policy change.

## Next Action

Review and archive `default-plugin-eval-remediation` if the deferred packaging
and complexity findings are accepted as follow-up work.
