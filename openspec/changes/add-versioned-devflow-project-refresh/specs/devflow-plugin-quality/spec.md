## ADDED Requirements

### Requirement: Project refresh impact is an executable DevFlow release gate
Every DevFlow change SHALL classify and verify its effect on the published
project-refresh contract before release promotion.

#### Scenario: A refresh-sensitive project surface changes
- **WHEN** canonical workflow configuration, configuration readers, project state, durable AGENTS guidance, control-plane templates, project-local skill inventory, official dependency layout, or migration behavior changes
- **THEN** the Project Refresh Impact is `changed`
- **AND** the refresh-contract identity changes
- **AND** the change supplies the required project-schema migration or managed refresh behavior and fixtures

#### Scenario: A project-facing change does not alter configuration schema
- **WHEN** a tracked project surface changes while the accepted project configuration schema remains compatible
- **THEN** the Project Refresh Impact records `verified-unchanged` for project schema with concrete comparison evidence
- **AND** the refresh-contract identity still changes so established projects detect the managed-surface drift

#### Scenario: A DevFlow change is not project-facing
- **WHEN** the change cannot affect any declared refresh-sensitive project surface
- **THEN** the Project Refresh Impact may be `not-applicable`
- **AND** records the inspected surfaces and concrete reason

#### Scenario: Impact evidence is missing or stale
- **WHEN** refresh-sensitive bytes, schema head, migration registry, fixtures, or the recorded impact disagree
- **THEN** pre-promotion and release promotion fail closed

#### Scenario: The project adapter manifest changes without a tracked-file byte change
- **WHEN** canonical manifest structure such as `projectLocalSkills`, `managedFiles`, `migrationSteps`, configuration targets, or AGENTS ownership changes while the declared tracked-input bytes remain unchanged
- **THEN** the impact analyzer detects the source-versus-baseline manifest identity change
- **AND** release promotion fails unless the refresh-contract revision and impact evidence advance consistently

### Requirement: Published refresh behavior has source release and cache parity
DevFlow SHALL publish and verify the project-refresh interface, contract,
migration chain, and test fixtures as one compatible release unit.

#### Scenario: A release candidate is verified
- **WHEN** DevFlow release verification runs
- **THEN** the packaged migration CLI, runtime implementation, refresh Skill reference, project-refresh metadata, migration steps, and contract identity match development source
- **AND** every supported older project schema reaches the current schema in the migration fixture matrix

#### Scenario: A named cache is refreshed
- **WHEN** an explicitly authorized DevFlow installation or cache refresh completes
- **THEN** readback proves that the installed project-refresh interface and contract identity match the verified release
- **AND** registration success alone is not accepted as freshness proof

#### Scenario: Plugin quality is assessed
- **WHEN** this plugin or Skill change reaches release verification
- **THEN** Plugin Eval runs against the generated release counterpart
- **AND** its score, findings, fixes, and any authorized deferrals are recorded with the project-refresh validation evidence
