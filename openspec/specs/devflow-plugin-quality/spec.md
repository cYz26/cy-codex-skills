# devflow-plugin-quality Specification

## Purpose
Define DevFlow's release-quality expectations for manifest discovery, concise skill metadata, context-tool implementation structure, packaged smoke tests, and Plugin Eval reassessment.
## Requirements
### Requirement: Manifest starter prompts fit Codex discovery
The DevFlow plugin manifest SHALL expose no more than three default starter prompts.

#### Scenario: Release and development manifests are inspected
- **WHEN** `.codex-plugin/plugin.json` is read from the release or development plugin root
- **THEN** `interface.defaultPrompt` contains at most three prompts
- **AND** the prompts cover planning, workflow setup, and verification/change flow entry points

### Requirement: Skill metadata remains concise and routable
DevFlow skill trigger descriptions SHALL be concise while retaining the concrete task signals needed for routing.

#### Scenario: High-cost skills are inspected
- **WHEN** `ai-native-tech-plan` and `context-tool-audit` skill metadata is read
- **THEN** each description is shorter than its pre-change description
- **AND** each description still names the main user intents that should trigger the skill

### Requirement: Context-tool implementation has focused modules
Context-tool audit and apply behavior SHALL be split into focused Python modules while preserving the public import facade.

#### Scenario: Existing CLI imports continue to work
- **WHEN** `audit_context_tools.py`, `apply_context_tool_actions.py`, or `workflow_lib.py` imports context-tool functions
- **THEN** imports still resolve through `workflow_context_tools`
- **AND** callers can still call `audit_context_tools` and `apply_context_tool_actions`

#### Scenario: Context-tool modules have clear responsibilities
- **WHEN** the scripts package is inspected
- **THEN** context-tool inventory, catalog reading, recommendation construction, and action application live in separate modules
- **AND** `workflow_context_tools.py` contains orchestration and compatibility exports rather than all implementation details

### Requirement: Release package includes packaged behavior tests
The release plugin package SHALL include compact smoke tests for packaged behavior.

#### Scenario: Release smoke tests run
- **WHEN** unittest discovery runs against `plugins/dev-flow/tests`
- **THEN** the tests validate manifest prompt count, context-tool importability, audit output shape, and action dry-run behavior
- **AND** the tests do not require network access or user Codex configuration changes

### Requirement: Plugin Eval findings are systematically reassessed
The change SHALL record a fresh systematic assessment after implementation.

#### Scenario: Final evaluation is performed
- **WHEN** implementation is complete
- **THEN** Plugin Eval is run for the release plugin root
- **AND** Plugin Eval is run for the development plugin root
- **AND** the final report calls out remaining warnings, if any, with concrete follow-up recommendations

### Requirement: Stop hooks use Codex Stop schema

DevFlow SHALL emit Stop hook JSON that conforms to the current Codex Stop hook
schema.

#### Scenario: Stop warning asks Codex to continue

- **WHEN** a DevFlow Stop hook has model-visible guidance to return
- **THEN** the hook output contains top-level `decision: "block"`
- **AND** the hook output contains a non-empty top-level `reason`
- **AND** the hook output does not contain `hookSpecificOutput`

#### Scenario: Non-Stop warning keeps additional context shape

- **WHEN** a non-Stop DevFlow hook has model-visible guidance to return
- **THEN** the hook output uses `hookSpecificOutput.additionalContext`
- **AND** the hook output names the matching hook event

### Requirement: Stop gates avoid repeated acknowledged maintenance prompts

DevFlow SHALL avoid repeatedly blocking Stop for the same acknowledged
medium-risk maintenance condition.

#### Scenario: Medium context-health report already acknowledged

- **GIVEN** a context-health report has been written into workflow state
- **AND** the current context-health signature still matches that report
- **WHEN** the Stop context-health hook runs again
- **THEN** the hook exits without emitting another Stop block prompt

#### Scenario: Context-health risk changes after acknowledgement

- **GIVEN** a context-health report has been written into workflow state
- **AND** the current context-health signature no longer matches that report
- **WHEN** the Stop context-health hook runs again
- **THEN** the hook may emit a Stop block prompt requiring reconciliation

### Requirement: Release promotion reports only real release changes

DevFlow SHALL report release promotion as synced only when runtime files,
managed outputs, or required managed outputs actually change.

#### Scenario: Build command is idempotent

- **GIVEN** release runtime files are current
- **AND** a release build command rewrites no managed output content
- **WHEN** release promotion runs
- **THEN** the promotion status is `current`
- **AND** no release validation prompt is emitted

#### Scenario: Build command updates managed output

- **GIVEN** a managed output is missing or content changes during a release
  build command
- **WHEN** release promotion runs
- **THEN** the promotion status is `synced`
- **AND** DevFlow asks for release validation and Plugin Eval before commit
