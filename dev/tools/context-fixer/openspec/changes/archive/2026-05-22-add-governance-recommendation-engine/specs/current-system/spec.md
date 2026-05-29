## ADDED Requirements

### Requirement: Governance Recommendation Engine
Context Fixer SHALL produce advisory governance recommendations from sanitized
budget, activity, trace, and configuration evidence.

#### Scenario: Governance report is included
- **WHEN** a repository audit is run with session or trace evidence
- **THEN** the JSON report includes a `governance` object with status,
  mutation posture, grouped suggestions, and a flattened recommendation list

#### Scenario: Profile recommendations are generated without mutation
- **WHEN** an audit finds heavy MCP inventory or request tool schemas
- **THEN** the report includes profile recommendations with suggested
  default-disabled servers, research/design profile placement, or allowlist
  hints
- **AND** no Codex config file is modified

#### Scenario: AGENTS and Skills recommendations are specific
- **WHEN** project or global instruction files or skill metadata exceed
  configured thresholds
- **THEN** the report recommends which content classes should remain in AGENTS
  and which content classes should move to Skills or docs
- **AND** prompt and file bodies remain omitted

#### Scenario: MCP recommendations cite evidence
- **WHEN** configured MCP inventory or request tool definitions are top
  offenders
- **THEN** the report recommends profile, allowlist, or default-disable actions
  with evidence pointing to the relevant budget category or inventory item

#### Scenario: Command-output recommendations include concrete recipes
- **WHEN** Bash output is a top offender
- **THEN** the report includes tail, path-limited search, failure-only reporter,
  or RTK-style recipes for future commands
- **AND** the report does not include raw command output

#### Scenario: Governance output is sanitized
- **WHEN** governance recommendations are rendered as text, Markdown, JSON,
  HTML, or Web dashboard data
- **THEN** they omit prompt bodies, chat message bodies, command output bodies,
  tool argument bodies, file content bodies, and trace payload bodies
