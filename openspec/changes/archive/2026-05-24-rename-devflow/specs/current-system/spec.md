## ADDED Requirements

### Requirement: DevFlow plugin identity
The repository SHALL publish its Codex workflow plugin under the `dev-flow` package id with `DevFlow` as the display name.

#### Scenario: Release and development catalogs use DevFlow identity
- **WHEN** `.agents/plugins/marketplace.json` or `.agents/plugins/marketplace.dev.json` is inspected
- **THEN** the workflow plugin entry is named `dev-flow`
- **AND** its source path points to a `dev-flow` plugin root
