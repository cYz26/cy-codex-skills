## Context

Governance recommendations should become actionable, but automatic mutation is
risky. This change introduces a two-step remediation workflow: generate a
dry-run plan, then explicitly apply known operations with backups.

## Goals / Non-Goals

Goals:

- Generate remediation plans from governance recommendations.
- Apply only known operation types.
- Create backups before writes.
- Keep plan and apply output sanitized.

Non-goals:

- Do not silently apply recommendations.
- Do not edit files outside the project or approved Codex locations.
- Do not move large content automatically without explicit plan operations.

## Decisions

1. **Plan first.** `remediate plan` is always dry-run and writes operations.
2. **Explicit apply.** `remediate apply <plan>` is the only mutating command.
3. **Allowlisted operations.** Supported types include `hook_install`,
   `mcp_profile_toggle`, `agents_extract_section`, `skill_locality`, and
   `command_policy`.
4. **Backups required.** Apply refuses to write unless backup creation succeeds.

## Risks / Trade-offs

- Automated edits can break workflows. Mitigation: dry-run plan, explicit apply,
  operation allowlist, backups, and changed-file summary.
- Content extraction can be imprecise. Mitigation: prefer safe snippets and
  proposal files unless exact boundaries are known.

## Migration Plan

1. Add dry-run plan tests.
2. Add safe apply tests.
3. Implement remediation module and CLI.
4. Update docs and verify.
