## ADDED Requirements

### Requirement: Local Web Dashboard
Context Fixer SHALL provide a local Web dashboard over sanitized report and
history data.

#### Scenario: Dashboard serves sanitized audit data
- **WHEN** `context-fixer dashboard serve --project <repo> --session-only --port <port>` is run
- **THEN** a local Web dashboard is available with overview, baseline, session
  timeline, top offenders, recommendations, data-source health, and history
  views
- **AND** every API response is derived from sanitized report/history schema

#### Scenario: Dashboard data command returns projection
- **WHEN** `context-fixer dashboard data --project <repo> --session-only --format json` is run
- **THEN** the output includes overview, baseline, session growth, timeline,
  top offenders, recommendations, data sources, history, and privacy sections

#### Scenario: Static dashboard can be exported
- **WHEN** `context-fixer dashboard export --project <repo> --session-only --output dashboard.html` is run
- **THEN** a local HTML artifact is written for sharing or archiving
- **AND** the artifact omits all sensitive bodies

#### Scenario: Dashboard stays local by default
- **WHEN** dashboard serve starts without a host override
- **THEN** it binds to localhost and prints the local URL

#### Scenario: Missing frontend assets are reported clearly
- **WHEN** dashboard serve cannot find built Web assets
- **THEN** it exits with a clear build instruction instead of serving a broken
  page
