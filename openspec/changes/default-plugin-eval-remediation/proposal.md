## Why

The existing Plugin Eval gate requires evaluation and decision evidence, but it
still treats remediation and deferral as equal options. The user wants Plugin
Eval findings to become actionable by default so plugin and skill quality issues
are fixed during the same work unless there is a concrete reason not to.

## What Changes

- Strengthen the repository Plugin Eval Gate so failures, warnings, and
  fix-first recommendations are automatically remediated by default.
- Limit deferral to explicit exception cases: out-of-scope work, destructive or
  risky changes, dependency or architecture decisions, or user approval needs.
- Require any deferred finding to record the reason, residual risk, and a
  concrete follow-up path.
- Update DevFlow AGENTS templates so generated projects inherit the same
  remediation-first behavior.
- Add regression tests so the policy cannot quietly degrade back to
  evaluate-only behavior.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `devflow-plugin-quality`: Plugin Eval findings are remediated by default after
  plugin or skill evaluation, with deferral treated as an explicit exception.

## Impact

- Updates root `AGENTS.md`.
- Updates DevFlow development and release `AGENTS.md` templates.
- Updates OpenSpec delta for DevFlow plugin quality policy.
- Updates focused tests that validate the Plugin Eval Gate wording.
