## ADDED Requirements

### Requirement: Context Budget Sections
Context Fixer SHALL expose an explicit context budget model that separates
baseline context, session growth, turn-level deltas, request composition, and top
offenders in structured JSON output.

#### Scenario: Report includes budget model
- **WHEN** the user analyzes a repository with session or trace evidence
- **THEN** the JSON report includes a `budget` object with `baseline`,
  `session_growth`, `turn_deltas`, `request_composition`, `top_offenders`, and
  `recommendations` sections

#### Scenario: Baseline section summarizes always-on context
- **WHEN** the repository or Codex home contains AGENTS files, skill metadata,
  Codex config, MCP config, hooks, or workflow files
- **THEN** the `budget.baseline` section groups those contributors by stable
  source category and reports estimated tokens, bytes, count, and risk status

#### Scenario: Session growth section summarizes runtime context
- **WHEN** Codex session JSONL contains messages, tool arguments, tool output,
  bash output, file content, patch/diff content, web/search output, MCP output,
  or token telemetry
- **THEN** the `budget.session_growth` section groups runtime contributors by
  stable source category without exposing sensitive bodies

#### Scenario: Turn deltas identify context spikes
- **WHEN** token telemetry or parser evidence shows per-turn growth
- **THEN** the `budget.turn_deltas` section lists the largest deltas with source,
  timestamp or path, estimated/exact token counts, and compact-safe metadata

#### Scenario: Request composition summarizes supplied traces
- **WHEN** a request trace is supplied with request body or usage evidence
- **THEN** the `budget.request_composition` section summarizes instructions,
  messages, tool definitions, tool results, exact usage, and request metadata
  without exposing request payload bodies

### Requirement: Stable Source Taxonomy
Context Fixer SHALL classify evidence using stable source categories that align
with Codex Context Lens terminology.

#### Scenario: Static sources are classified
- **WHEN** static project or Codex-home evidence is scanned
- **THEN** the system classifies contributors into categories including
  `global_agents`, `project_agents`, `nested_agents`, `skill_metadata`,
  `mcp_schema`, `hooks_context`, `codex_config`, and `workflow_context` where the
  evidence supports those distinctions

#### Scenario: Runtime sources are classified
- **WHEN** session JSONL evidence is parsed
- **THEN** the system classifies contributors into categories including
  `user_history`, `assistant_history`, `tool_call_args`, `tool_result`,
  `bash_output`, `file_content`, `patch_diff`, `web_result`, `mcp_output`,
  `developer_instructions`, and `conversation_summary` where the evidence
  supports those distinctions

#### Scenario: Unknown sources remain useful
- **WHEN** a source cannot be safely classified into a narrower category
- **THEN** the system reports it as a generic sanitized category instead of
  dropping it or exposing sensitive content

### Requirement: Budget-Driven Recommendations
Context Fixer SHALL generate recommendations from budget evidence, policy
thresholds, and top offenders.

#### Scenario: Recommendations cover expected optimization classes
- **WHEN** report evidence indicates large instruction files, global skills,
  heavy MCP inventory, large tool output, repeated diffs, file-read pressure,
  request trace availability, or high context usage
- **THEN** the system emits actionable recommendations for AGENTS slimming,
  skill locality, MCP/profile governance, command-output limiting, trace review
  or setup, repeated-diff/file-read reduction, and checkpoint/compact timing as
  applicable

#### Scenario: Recommendations include evidence
- **WHEN** a budget recommendation is emitted
- **THEN** the recommendation includes priority, title, reason, action, and
  source evidence that can be traced to a report section, contributor, event, or
  inventory item

## MODIFIED Requirements

### Requirement: Local-First Context Analysis
Context Fixer SHALL analyze local Codex context evidence from a target
repository without mutating project files, global Codex configuration, session
history, or request traces.

#### Scenario: Analyze target repository
- **WHEN** the user runs `context_fixer --repo <repo> --session-only` or supplies
  `--trace <trace.jsonl>`
- **THEN** the system reports context pressure, source-of-truth usage, policy
  status, budget sections, likely contributors, top offenders, findings, and
  recommendations for that repository

#### Scenario: Inspect project instruction chain
- **WHEN** the target repository contains Codex instruction files or
  project-local configuration
- **THEN** the system includes the discovered instruction chain and relevant
  project AI configuration inventory in the report

### Requirement: Optional Request Trace Attribution
Context Fixer SHALL treat request trace evidence as an explicit user-supplied
input and SHALL NOT provide proxy or tap capture behavior as part of this
baseline.

#### Scenario: Analyze supplied trace file
- **WHEN** the user runs `context_fixer --repo <repo> --trace <trace.jsonl>`
- **THEN** the system combines request usage, request composition, and request
  shape attribution with session and static-source evidence

#### Scenario: No trace file supplied
- **WHEN** the user omits `--trace` and does not pass `--session-only`
- **THEN** the CLI exits with request trace setup guidance instead of silently
  producing a lower-confidence report

#### Scenario: Explicit session-only analysis
- **WHEN** the user passes `--session-only`
- **THEN** the system reports request trace availability as absent and continues
  using session and static-source evidence

### Requirement: Sanitized Reporting
Context Fixer SHALL render text, JSON, and self-contained HTML reports without
printing prompt bodies, chat message bodies, tool argument bodies, tool output
bodies, command output bodies, file content bodies, or request trace payload
bodies.

#### Scenario: Render text report
- **WHEN** the user runs the CLI without `--json` or `--html`
- **THEN** the system prints a readable report with labels, paths, token
  estimates, budget sections, exact telemetry where available, findings, and
  recommendations

#### Scenario: Render JSON report
- **WHEN** the user passes `--json`
- **THEN** the system emits structured sanitized report data suitable for
  downstream tooling

#### Scenario: Render HTML report
- **WHEN** the user passes `--html <path>`
- **THEN** the system writes a static self-contained dashboard report to the
  requested path with budget, top offender, timeline, activity, and
  recommendation sections
