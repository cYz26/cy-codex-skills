## MODIFIED Requirements

### Requirement: Sanitized Reporting
Context Fixer SHALL render text, Markdown, JSON, and self-contained HTML reports
without printing prompt bodies, chat message bodies, tool argument bodies, tool
output bodies, command output bodies, file content bodies, request trace payload
bodies, authorization headers, or request trace URL query strings/fragments.

#### Scenario: Render text report
- **WHEN** the user runs the CLI without `--json`, `--html`, or
  `--format markdown`
- **THEN** the system prints a readable report with labels, paths, token
  estimates, budget sections, exact telemetry where available, findings, and
  recommendations

#### Scenario: Render JSON report
- **WHEN** the user passes `--json` or `--format json`
- **THEN** the system emits structured sanitized report data suitable for
  downstream tooling

#### Scenario: Render Markdown report
- **WHEN** the user passes `--format markdown`
- **THEN** the system emits a sanitized Markdown report suitable for saving or
  sharing after local review

#### Scenario: Render HTML report
- **WHEN** the user passes `--html <path>` or `--format html --output <path>`
- **THEN** the system writes a static self-contained dashboard report to the
  requested path with budget, top offender, timeline, activity, and
  recommendation sections

#### Scenario: Request trace URL metadata is sanitized
- **WHEN** a supplied request trace contains request paths, endpoint URLs, or
  upstream URLs with query strings or fragments
- **THEN** Context Fixer reports only sanitized URL metadata without query
  strings or fragments in text, Markdown, JSON, HTML, Web dashboard data, and
  persisted history snapshots
