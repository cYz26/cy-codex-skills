## Why

Recommendations are useful, but a complete governance loop needs reviewable
plans and explicit apply commands. The system should help users implement
AGENTS, Skills, MCP, hook, and command-output improvements without silently
mutating configuration.

## What Changes

- Add `remediate plan` to generate sanitized dry-run remediation plans.
- Add `remediate apply` to apply known operations only after explicit command
  invocation.
- Create backups before file writes.
- Refuse unknown operations and unsafe paths.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `current-system`: add explicit guided governance remediation behavior.

## Impact

- Affected code: `src/context_fixer/remediation.py`,
  `src/context_fixer/cli.py`, governance integration, and tests.
- Public CLI: additive `remediate plan` and `remediate apply`.
- Dependencies: no new production dependency.
- Safety: apply requires explicit plan file and creates backups.
