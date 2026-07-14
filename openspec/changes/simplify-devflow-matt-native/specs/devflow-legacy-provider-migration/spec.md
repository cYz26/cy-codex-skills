## ADDED Requirements

### Requirement: Legacy provider configuration is recognized explicitly

DevFlow SHALL provide an explicit legacy inspector that recognizes obsolete methodology profiles, roadmap providers, provider selectors, roadmap bindings, provider locks, generated provider links, and known Superpowers/GSD project markers.

#### Scenario: Obsolete config fields are present

- **WHEN** the inspector reads a project containing `methodology_profile`, `roadmap_provider`, `provider_selectors`, or `roadmap_bindings`
- **THEN** it reports every recognized field's presence and value type without echoing the value
- **AND** maps the project to the single current DevFlow configuration without activating the old selection

#### Scenario: Legacy provider artifacts are present

- **WHEN** the inspector finds recognized Superpowers or GSD skills, agents, hooks, runtime files, planning locations, or draft paths
- **THEN** it classifies each path as generated candidate, user/history data, conflict, or preserved unknown
- **AND** it does not infer that the provider is active or ready

### Requirement: Legacy inspection is deterministic and read-only

The legacy inspector SHALL produce a deterministic machine-readable report, SHALL redact configuration and provider-lock values, and SHALL NOT modify files, links, configuration, dependencies, caches, Git state, or external systems.

#### Scenario: Inspection is repeated without input changes

- **WHEN** the same project is inspected twice
- **THEN** the normalized findings, target configuration, conflicts, preserved paths, and manual actions are identical

#### Scenario: Legacy configuration contains credentials

- **WHEN** an obsolete field, provider lock, or unrelated current configuration contains a token or credential
- **THEN** the report exposes only recognized field presence and value type plus the fixed canonical target
- **AND** the token or credential does not appear in JSON or text output

#### Scenario: Operator requests help or JSON output

- **WHEN** the inspector CLI is invoked in any supported mode
- **THEN** it exposes no apply, cleanup, rollback, install, activate, commit, push, archive, or migration-write option
- **AND** filesystem content and link targets remain unchanged

### Requirement: Legacy inspection is isolated from active runtime

The legacy inspector SHALL be import-isolated from normal dependency, activation, updater, hook, verification, archive, scaffold, and release-readiness execution.

#### Scenario: Active runtime import graph is inspected

- **WHEN** packaged and development runtime modules are analyzed
- **THEN** no active entrypoint imports the legacy inspector module or CLI
- **AND** the inspector imports no Superpowers or GSD runtime, provider registry, installer, or network client

#### Scenario: Legacy providers are unavailable

- **GIVEN** no Superpowers plugin and no GSD runtime is installed
- **WHEN** the legacy inspector runs
- **THEN** it still completes from filesystem metadata alone
- **AND** it emits no install or fallback action

### Requirement: Active readers fail closed on legacy selection state

Active DevFlow configuration readers SHALL reject obsolete provider-selection keys with a migration-required diagnostic that names the explicit inspector command.

#### Scenario: Normal workflow sees a legacy roadmap provider

- **WHEN** an active workflow command reads a config containing `roadmap_provider: gsd`
- **THEN** it stops provider-dependent routing
- **AND** reports the legacy-inspection next action without importing or invoking GSD

#### Scenario: Normal workflow sees no legacy keys

- **WHEN** an active workflow command reads the current minimal config
- **THEN** it proceeds without consulting the legacy inspector or provider state

### Requirement: User and historical data are preserved by default

The legacy inspector SHALL treat user-authored planning files, historical OpenSpec evidence, prior verification records, and ambiguous paths as preserved data.

#### Scenario: Historical or ambiguous content is found

- **WHEN** a recognized legacy directory contains content that is not proven generated and disposable
- **THEN** the inspector reports it as preserved or conflicted
- **AND** provides no deletion instruction that claims the content is safe to remove automatically
