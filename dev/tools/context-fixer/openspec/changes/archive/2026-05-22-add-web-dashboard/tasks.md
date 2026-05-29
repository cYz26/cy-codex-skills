## 1. Dashboard Projection Tests

- [x] 1.1 Add failing tests for dashboard JSON projection sections.
- [x] 1.2 Add failing tests for sensitive-body omission.
- [x] 1.3 Add failing tests for dashboard CLI data/export commands.

## 2. Python Dashboard Backend

- [x] 2.1 Create `src/context_fixer/dashboard.py`.
- [x] 2.2 Create `src/context_fixer/web.py`.
- [x] 2.3 Add `dashboard data`, `dashboard export`, and `dashboard serve`.

## 3. Web Frontend

- [x] 3.1 Avoid new React/Vite dependencies for this implementation; use a
  no-dependency Web shell.
- [x] 3.2 Create `web/dashboard` app shell.
- [x] 3.3 Implement overview, baseline, history, timeline, offenders,
  recommendations, data-source, and settings views.
- [x] 3.4 Build frontend assets and wire serving.

## 4. Documentation

- [x] 4.1 Document Web dashboard commands.
- [x] 4.2 Document local-only and privacy boundaries.

## 5. Verification

- [x] 5.1 Run Python dashboard tests.
- [x] 5.2 Run Web dashboard build/static asset check.
- [x] 5.3 Run CLI smoke checks.
