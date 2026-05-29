## Why

Context Fixer already attributes context pressure, but the complete product must
turn that evidence into concrete governance actions for AGENTS, Skills, MCP,
hooks, profiles, and noisy shell output. Users need recommendations that are
specific enough to act on without exposing sensitive bodies or silently changing
their configuration.

## What Changes

- Add a governance recommendation model to the sanitized report.
- Generate profile, AGENTS, Skills, MCP, hook, and command-output suggestions
  from budget, activity, trace, and configuration evidence.
- Render governance recommendations in text, Markdown, JSON, HTML, and the Web
  dashboard data model.
- Keep recommendations advisory in this change; applying them is handled by the
  separate guided remediation change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `current-system`: add advisory governance recommendations derived from
  existing sanitized report evidence.

## Impact

- Affected code: `src/context_fixer/governance.py`,
  `src/context_fixer/analyzer.py`, `src/context_fixer/render.py`,
  `src/context_fixer/cli.py`, and `tests/test_context_fixer.py`.
- Affected docs: `README.md`, `skills/context-fixer/SKILL.md`.
- Public CLI: additive report fields and richer recommendation output.
- Dependencies: no new production dependency.
- Privacy: recommendations cite labels, sizes, paths, hashes, and categories;
  they never include prompt, message, argument, output, file, or trace bodies.
