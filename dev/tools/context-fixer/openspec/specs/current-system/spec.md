# Current System Specification

## Purpose

Define the accepted baseline behavior for Context Fixer, a local-first Codex
context auditing CLI.

## Requirements

### Requirement: Local-First Context Analysis

Context Fixer SHALL analyze local Codex context evidence from a target
repository without mutating project files, global Codex configuration, or
session history.

#### Scenario: Analyze target repository
- **WHEN** the user runs `context_fixer --repo <repo>`
- **THEN** the system reports context pressure, source-of-truth usage, policy
  status, likely contributors, findings, and recommendations for that repository

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
- **THEN** the system combines request usage and request shape attribution with
  session and static-source evidence

#### Scenario: No trace file supplied
- **WHEN** the user omits `--trace`
- **THEN** the system reports request trace availability as absent and continues
  using session and static-source evidence

### Requirement: Sanitized Reporting

Context Fixer SHALL render text, JSON, and self-contained HTML reports without
printing prompt bodies, chat message bodies, tool argument bodies, or tool output
bodies.

#### Scenario: Render text report
- **WHEN** the user runs the CLI without `--json` or `--html`
- **THEN** the system prints a readable report with labels, paths, token
  estimates, exact telemetry where available, findings, and recommendations

#### Scenario: Render JSON report
- **WHEN** the user passes `--json`
- **THEN** the system emits structured sanitized report data suitable for
  downstream tooling

#### Scenario: Render HTML report
- **WHEN** the user passes `--html <path>`
- **THEN** the system writes a static self-contained dashboard report to the
  requested path

### Requirement: Compatibility Alias

Context Fixer SHALL preserve the `codex-context-lens` compatibility import and
console path for existing local automation during this baseline.

#### Scenario: Compatibility module remains importable
- **WHEN** existing automation imports `codex_context_lens`
- **THEN** the compatibility package delegates to the Context Fixer
  implementation

### Requirement: Workflow Baseline

The project workflow SHALL keep durable planning, OpenSpec, checkpoint, and
verification records before archive or phase completion.

#### Scenario: Verification evidence before archive
- **WHEN** the current-system baseline is reviewed for archive
- **THEN** the workflow state includes recorded verification commands, command
  results, and any remaining risks

#### Scenario: Archive remains gated
- **WHEN** verification or approval gates are incomplete
- **THEN** the workflow state keeps archive disallowed
