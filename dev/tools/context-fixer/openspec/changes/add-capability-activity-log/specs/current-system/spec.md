## ADDED Requirements

### Requirement: Capability Activity Reporting
Context Fixer SHALL include a sanitized capability activity report that distinguishes observed capability calls from configured or available capabilities.

#### Scenario: Report observed session tool calls
- **WHEN** analyzed session logs contain tool call and tool result events
- **THEN** the system reports tool names, call counts, result counts, timestamps, and estimated argument/output sizes without printing argument or output bodies

#### Scenario: Report request trace activity
- **WHEN** the user supplies request trace files
- **THEN** the system reports sanitized request activity categories, request methods, paths without query strings, statuses, latencies, models, and available request tool names

#### Scenario: Report configured capability inventory
- **WHEN** global or project Codex configuration includes plugins, skills, or MCP servers
- **THEN** the system reports them as configured inventory and SHALL NOT label them as observed calls unless matching session or trace evidence exists

#### Scenario: Render activity in all output formats
- **WHEN** the user renders text, JSON, or HTML output
- **THEN** the system includes capability activity summaries and keeps prompt bodies, chat bodies, tool argument bodies, tool output bodies, and auth headers omitted
