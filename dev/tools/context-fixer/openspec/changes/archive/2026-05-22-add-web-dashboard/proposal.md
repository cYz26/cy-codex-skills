## Why

The complete product requires a Web dashboard for overview, history, baseline,
timeline, offenders, recommendations, and data-source health. A local browser UI
is sufficient; the user explicitly does not need a Tauri desktop wrapper.

## What Changes

- Add dashboard projection and local Web API.
- Add `dashboard serve`, `dashboard data`, and `dashboard export` commands.
- Add a local Web dashboard shell without Tauri; use a no-dependency frontend
  for this implementation to avoid adding Node dependencies.
- Serve only sanitized report and history data.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `current-system`: add local Web dashboard behavior over sanitized report and
  history data.

## Impact

- Affected code: `src/context_fixer/dashboard.py`,
  `src/context_fixer/web.py`, `src/context_fixer/cli.py`, store integration,
  `web/dashboard/`, and tests.
- Public CLI: additive dashboard subcommands.
- Dependencies: Python server and current dashboard shell use the standard
  library only; React/Vite can replace the shell later if explicitly desired.
- Privacy: dashboard API and export use sanitized report/history schema only.
