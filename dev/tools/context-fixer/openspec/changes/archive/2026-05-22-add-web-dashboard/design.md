## Context

The existing HTML report is useful but static. The complete product needs a
local Web dashboard with history browsing and interactive views. The Python
analysis engine remains canonical; the frontend consumes sanitized JSON.

## Goals / Non-Goals

Goals:

- Provide dashboard JSON projection.
- Serve a local Web dashboard from `context-fixer dashboard serve`.
- Export a static dashboard artifact.
- Show overview, baseline, sessions/history, timeline, top offenders,
  recommendations, data-source health, and settings/privacy views.

Non-goals:

- Do not build a Tauri app.
- Do not expose a remote service by default.
- Do not render sensitive bodies.

## Decisions

1. **Python API boundary.** `web.py` serves sanitized JSON endpoints and static
   built assets.
2. **No-dependency Web shell.** `web/dashboard` owns the interactive UI without
   adding Node dependencies in this implementation. React/Vite can be adopted
   later against the same dashboard projection if explicitly requested.
3. **No mandatory server for export.** `dashboard export` writes a local HTML
   artifact.
4. **Localhost default.** `dashboard serve` binds to `127.0.0.1` unless the user
   explicitly chooses another host.

## Endpoints

- `GET /` serves the dashboard shell.
- `GET /api/dashboard` returns current sanitized dashboard data.
- `GET /api/history` returns sanitized snapshot summaries.
- `GET /api/snapshot/<id>` returns a sanitized saved report snapshot.

## Risks / Trade-offs

- A no-dependency shell is less componentized than React/Vite. Mitigation: keep
  the dashboard projection stable so a React frontend can replace it later.
- Frontend can drift from report schema. Mitigation: dashboard projection keeps
  a stable UI contract.

## Migration Plan

1. Add dashboard projection tests.
2. Implement Python dashboard API/export.
3. Add React/Vite dashboard after dependency approval.
4. Verify build and CLI smoke.
