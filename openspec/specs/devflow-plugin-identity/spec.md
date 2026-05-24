# devflow-plugin-identity Specification

## Purpose
Define DevFlow's canonical plugin identity, marketplace registration, stable workflow skill protocol, hook configuration compatibility, and maintained documentation labels.

## Requirements
### Requirement: Canonical plugin identity
The plugin SHALL use `dev-flow` as its canonical machine-readable package id and `DevFlow` as its user-facing display name.

#### Scenario: Manifest exposes new identity
- **WHEN** the plugin manifest is read from the dev or release plugin root
- **THEN** `name` is `dev-flow`
- **AND** `interface.displayName` is `DevFlow`

#### Scenario: Marketplace registers new identity
- **WHEN** a local marketplace catalog is read
- **THEN** the plugin entry is registered as `dev-flow`
- **AND** the entry path resolves to the matching `dev-flow` plugin directory

### Requirement: Existing workflow skill protocol remains stable
The plugin SHALL keep existing project-local workflow skill names stable during the rename.

#### Scenario: Dependency check still finds project orchestrator skill
- **WHEN** dependency validation runs for an activated project
- **THEN** it still checks for the `project-orchestrator` project-local skill

### Requirement: Hook configuration compatibility
Hook configuration SHALL prefer `.dev-flow.json` and SHALL read `.codex-project-orchestrator.json` as a legacy fallback when the new file is absent.

#### Scenario: New hook config overrides legacy config
- **WHEN** both `.dev-flow.json` and `.codex-project-orchestrator.json` exist in a target repo
- **THEN** hook policy reads `.dev-flow.json`

#### Scenario: Legacy hook config still works
- **WHEN** only `.codex-project-orchestrator.json` exists in a target repo
- **THEN** hook policy reads the legacy file

### Requirement: Warning and documentation labels use new name
Current runtime warning labels and maintained docs SHALL refer to `DevFlow` or `dev-flow` instead of `codex-project-orchestrator` for canonical identity surfaces.

#### Scenario: Hook warning uses new label
- **WHEN** an edit or gate hook emits a warning
- **THEN** the warning prefix uses `DevFlow`

#### Scenario: README uses new plugin paths
- **WHEN** the repository or plugin README documents plugin locations or install references
- **THEN** it uses `dev-flow` paths and marketplace names
