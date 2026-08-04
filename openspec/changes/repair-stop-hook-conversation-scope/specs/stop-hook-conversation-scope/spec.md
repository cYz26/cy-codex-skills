## Purpose

Defines when DevFlow may enforce repository-level automatic continuation from a
Codex Stop hook without trapping reentrant or ephemeral conversations.

## ADDED Requirements

### Requirement: Stop continuation is one-shot

DevFlow SHALL consume the Codex Stop lifecycle payload before evaluating the
repository execution source. A turn that Codex reports as already continued by
Stop MUST exit successfully without another blocking response.

#### Scenario: First durable stop attempt has executable work

- **WHEN** a durable conversation reports `stop_hook_active: false`
- **AND** its recognized DevFlow repository has approved executable work
- **THEN** the Stop hook exits successfully with one schema-compatible
  `decision: "block"` response
- **AND** the existing continuation outcome remains the response reason.

#### Scenario: Continued turn reaches Stop again

- **WHEN** a Stop payload reports `stop_hook_active: true`
- **THEN** the Stop hook exits successfully with empty stdout
- **AND** it does not evaluate or mutate the repository execution source.

### Requirement: Ephemeral conversations do not own durable execution

DevFlow SHALL apply repository-level automatic continuation only to a durable
or legacy-compatible Stop conversation. A current Codex payload that explicitly
has no persistent transcript MUST be treated as out of scope for enforcement.

#### Scenario: Ephemeral side conversation stops beside active work

- **WHEN** a Stop payload contains `transcript_path: null`
- **AND** the working directory contains an unfinished DevFlow execution source
- **THEN** the Stop hook exits successfully with empty stdout
- **AND** it does not consume, alter, or continue that execution source.

#### Scenario: Durable conversation retains continuation enforcement

- **WHEN** a Stop payload contains a non-empty persistent transcript path
- **AND** `stop_hook_active` is false
- **THEN** DevFlow evaluates the recognized repository execution source
- **AND** existing Human Gate, verification, continuation, and external-effect
  precedence remains unchanged.

#### Scenario: Legacy payload omits transcript scope

- **WHEN** a Stop payload omits `transcript_path`
- **AND** it does not report an already continued turn
- **THEN** DevFlow preserves the existing fail-closed repository evaluation
- **AND** does not silently weaken continuation for older Codex payloads or
  direct callers.

### Requirement: Diagnostic and Doctor surfaces expose the scope contract

DevFlow SHALL keep manual Stop diagnostics independent from hook applicability
and SHALL expose a deterministic Doctor check for the supported scope cases.

#### Scenario: Operator requests JSON diagnostics

- **WHEN** an operator invokes the Stop script with `--json` and an explicit
  repository
- **THEN** DevFlow evaluates and prints the complete Stop-check report
- **AND** missing hook-only transcript fields do not suppress diagnostics.

#### Scenario: Workflow Doctor verifies Stop scope invariants

- **WHEN** Workflow Doctor runs against a valid DevFlow project
- **THEN** its JSON report includes the Stop-hook protocol check
- **AND** the check proves that reentrant and ephemeral payloads do not enforce
  continuation while durable and legacy-compatible payloads do
- **AND** a failed protocol check makes the Doctor report need repair.

### Requirement: Scope classification remains read-only and schema-compatible

DevFlow MUST NOT parse unstable transcript contents, add workflow-state schema,
or emit unsupported Stop response fields to classify a conversation.

#### Scenario: Scope is classified

- **WHEN** any Stop payload is classified
- **THEN** DevFlow uses only documented top-level lifecycle fields
- **AND** it writes no OpenSpec, ledger, workflow state, Git state, generated
  release, installed cache, or external system.
