## MODIFIED Requirements

### Requirement: Managed External Tool Collection
Context Fixer SHALL provide managed collection profiles that check, start,
invoke, collect from, and stop or reuse declared external tools.

#### Scenario: Official collection flow starts required external tools
- **WHEN** `context-fixer collect --project <repo> --profile full` is run
- **THEN** Context Fixer checks required external tool availability, starts or
  invokes configured collectors, writes artifacts into the run directory,
  imports them into the sanitized report, and records tool status
- **AND** the user is not required to manually run each external command

#### Scenario: Project-local external tools are discovered
- **WHEN** a declared external tool executable exists in a supported
  project-local tool bin directory
- **THEN** `tools doctor`, `tools list`, and `collect` treat the tool as
  available without requiring the user to export PATH manually

#### Scenario: Supplied trace is reused for claude-tap
- **WHEN** `context-fixer collect --project <repo> --profile full --trace <trace.jsonl>` is run
- **THEN** Context Fixer records the supplied trace as the claude-tap artifact
  and marks the capture tool as reused
- **AND** it does not invoke unsupported claude-tap arguments

#### Scenario: Claude-tap can be probed safely
- **WHEN** claude-tap is installed but no explicit trace artifact is supplied
- **THEN** Context Fixer probes tool availability with a supported command and
  reports status without writing probe output as a trace artifact

#### Scenario: Unavailable external tools degrade with explicit status
- **WHEN** a configured external tool is missing, unhealthy, or refuses to
  start
- **THEN** the run report marks that tool as `missing`, `failed`, or `skipped`
- **AND** Context Fixer continues with available sources unless the selected
  profile marks the tool as required

#### Scenario: Sensitive capture tools require trace-enabled profile
- **WHEN** a flow would start a request payload capture tool such as claude-tap
- **THEN** Context Fixer starts or reuses it only in a trace-enabled profile
  such as `trace` or `full`
- **AND** the report labels trace artifacts as sensitive while rendering only
  sanitized attribution

#### Scenario: Tool doctor reports availability
- **WHEN** the user runs `context-fixer tools doctor --project <repo>`
- **THEN** the system reports declared tool availability, executable path when
  found, profile participation, required status, and setup guidance

#### Scenario: Manual imports remain available
- **WHEN** `context-fixer trace import`, `context-fixer usage import`, or
  `context-fixer otel import` is run with an explicit file path
- **THEN** supplied artifacts are imported without requiring managed collection
- **AND** manual import is documented as an advanced/debug flow

#### Scenario: Tool process output is sanitized
- **WHEN** a managed tool writes stdout or stderr
- **THEN** Context Fixer records byte counts, hashes, status, and artifact paths
  but does not render raw stdout or stderr bodies
