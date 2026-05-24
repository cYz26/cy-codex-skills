# Current System Specification

## Purpose

Capture stable, repository-level facts for the current DevFlow plugin system so OpenSpec changes can sync against a valid baseline.

## Requirements
### Requirement: Brownfield current-system baseline exists
The repository SHALL maintain a valid current-system OpenSpec baseline for repository-wide behavior.

#### Scenario: Current-system spec is validated
- **WHEN** OpenSpec validates repository specs
- **THEN** the current-system spec includes a purpose
- **AND** it includes at least one requirements section

### Requirement: DevFlow plugin identity
The repository SHALL publish its Codex workflow plugin under the `dev-flow` package id with `DevFlow` as the display name.

#### Scenario: Release and development catalogs use DevFlow identity
- **WHEN** `.agents/plugins/marketplace.json` or `.agents/plugins/marketplace.dev.json` is inspected
- **THEN** the workflow plugin entry is named `dev-flow`
- **AND** its source path points to a `dev-flow` plugin root
