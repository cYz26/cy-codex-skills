## ADDED Requirements

### Requirement: Guided Governance Remediation
Context Fixer SHALL provide a two-step remediation workflow that plans and then
explicitly applies allowed governance changes with backups.

#### Scenario: Remediation dry-run creates a reviewable plan
- **WHEN** `context-fixer remediate plan --project <repo> --session-only --output remediation.json` is run
- **THEN** Context Fixer writes a plan containing AGENTS, Skills, MCP profile,
  hook, and command-output recommendations
- **AND** no repository or Codex configuration file is modified

#### Scenario: Remediation apply requires explicit input
- **WHEN** `context-fixer remediate apply remediation.json --project <repo> --backup-dir <dir>` is run
- **THEN** only changes listed in the remediation plan are applied
- **AND** original files are backed up before modification

#### Scenario: Unknown operations are refused
- **WHEN** a remediation plan contains an unknown operation type
- **THEN** Context Fixer refuses to apply the plan and reports the unsupported
  operation

#### Scenario: Unsafe paths are refused
- **WHEN** a remediation operation targets an absolute path outside the project
  or approved Codex configuration paths
- **THEN** Context Fixer refuses the operation

#### Scenario: Apply output is sanitized
- **WHEN** a remediation plan or apply result is rendered
- **THEN** it omits prompt bodies, trace payload bodies, command output bodies,
  and file content bodies
