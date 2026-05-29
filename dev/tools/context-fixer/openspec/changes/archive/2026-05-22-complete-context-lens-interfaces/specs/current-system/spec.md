## ADDED Requirements

### Requirement: Document-Aligned CLI Commands
Context Fixer SHALL provide command-oriented CLI entry points aligned with the
Codex Context Lens technical solution while preserving the existing legacy flags.

#### Scenario: Audit project
- **WHEN** the user runs `context-fixer audit --project <repo> --session-only`
- **THEN** the system analyzes the repository and prints a sanitized project
  context audit report

#### Scenario: List sessions
- **WHEN** the user runs `context-fixer sessions --repo <repo> --top <N>`
- **THEN** the system lists up to `<N>` matching Codex session JSONL files with
  sanitized usage summary fields

#### Scenario: Inspect session
- **WHEN** the user runs `context-fixer inspect <session.jsonl> --repo <repo>`
- **THEN** the system analyzes that session as explicit session evidence

#### Scenario: Render report formats
- **WHEN** the user runs `context-fixer report --project <repo> --format markdown`
- **THEN** the system emits a sanitized Markdown report

#### Scenario: Print recommendations
- **WHEN** the user runs `context-fixer recommend --project <repo> --session-only`
- **THEN** the system prints sanitized budget and compression recommendations
  without raw prompt, argument, output, or trace bodies

#### Scenario: Doctor configuration
- **WHEN** the user runs `context-fixer doctor --project <repo>`
- **THEN** the system prints sanitized data source, policy, instruction chain,
  inventory, and setup health information

#### Scenario: Import trace
- **WHEN** the user runs `context-fixer trace import <trace.jsonl> --repo <repo>`
- **THEN** the system analyzes the supplied trace as request evidence without
  enabling live capture

### Requirement: Markdown Report Rendering
Context Fixer SHALL support Markdown as a first-class sanitized report format.

#### Scenario: Markdown report includes budget model
- **WHEN** a Markdown report is rendered
- **THEN** it includes summary, context budget, top offenders, timeline,
  capability activity, recommendations, findings, and instruction chain sections

#### Scenario: Markdown report is sanitized
- **WHEN** a Markdown report is rendered from sensitive session or trace fixtures
- **THEN** it omits prompt bodies, chat message bodies, command output bodies,
  tool argument bodies, file content bodies, and trace payload bodies

### Requirement: Hook Collector
Context Fixer SHALL provide an optional local hook collector that records
sanitized Codex hook event metadata without changing Codex behavior.

#### Scenario: Record post-tool-use event
- **WHEN** `context-fixer-hook post-tool-use` receives hook event JSON on stdin
- **THEN** it appends a sanitized JSONL record under the Context Fixer cache and
  prints a short success status

#### Scenario: Hook record omits sensitive bodies
- **WHEN** the hook input contains command output, tool input, prompt text, or
  other large body fields
- **THEN** the stored record includes size, estimated tokens, hash, tool name,
  command preview, cwd/session metadata, status fields, and source field names
  but not the raw body values

### Requirement: Skill Workflow Integration
Context Fixer SHALL ship a repository skill guide that invokes the current CLI
commands and privacy posture.

#### Scenario: Skill guide references current commands
- **WHEN** a developer reads `skills/context-fixer/SKILL.md`
- **THEN** the guide includes the new audit, report, recommend, sessions,
  inspect, trace import, and hook collector workflows

## MODIFIED Requirements

### Requirement: Local-First Context Analysis
Context Fixer SHALL analyze local Codex context evidence from a target
repository without mutating project files, global Codex configuration, session
history, or request traces.

#### Scenario: Analyze target repository
- **WHEN** the user runs the legacy CLI, `audit`, `report`, `recommend`, or
  `doctor` against a target repository
- **THEN** the system reports context pressure, source-of-truth usage, policy
  status, budget sections, likely contributors, top offenders, findings, and
  recommendations for that repository according to the command purpose

#### Scenario: Inspect project instruction chain
- **WHEN** the target repository contains Codex instruction files or
  project-local configuration
- **THEN** the system includes the discovered instruction chain and relevant
  project AI configuration inventory in the report

### Requirement: Sanitized Reporting
Context Fixer SHALL render text, Markdown, JSON, and self-contained HTML reports
without printing prompt bodies, chat message bodies, tool argument bodies, tool
output bodies, command output bodies, file content bodies, or request trace
payload bodies.

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
