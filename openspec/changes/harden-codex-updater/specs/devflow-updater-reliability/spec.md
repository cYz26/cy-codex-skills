# devflow-updater-reliability Specification

## Purpose

Define reliability requirements for DevFlow's Codex plugin and skill updater.

## ADDED Requirements
### Requirement: Git dry-run reports actual remote state when possible

The updater SHALL distinguish a clean Git checkout from an update-available checkout during dry-run checks.

#### Scenario: Git mirror is current
- **WHEN** a Git mirror has a clean working tree
- **AND** its upstream remote branch points at the same commit
- **THEN** dry-run reports the mirror as `unchanged`
- **AND** includes the current commit.

#### Scenario: Git mirror has remote changes
- **WHEN** a Git mirror has a clean working tree
- **AND** its upstream remote branch points at a different commit
- **THEN** dry-run reports the mirror as `would-update`
- **AND** includes before and after commit identifiers.

### Requirement: Installed plugin caches are refreshable

The updater SHALL plan and apply refreshes for configured installed plugins after marketplace snapshots are refreshed.

#### Scenario: Dry-run plans installed plugin refresh
- **WHEN** Codex config contains an enabled `plugin@marketplace` entry
- **AND** that marketplace is configured
- **THEN** dry-run reports a `plugin-install` item for that selector
- **AND** does not run `codex plugin add`.

#### Scenario: Apply refreshes installed plugin cache
- **WHEN** the updater runs with `--apply`
- **AND** Codex config contains an enabled `plugin@marketplace` entry
- **THEN** the updater runs `codex plugin add plugin@marketplace`
- **AND** reports the command result.

### Requirement: Installed plugin cache verification provides source evidence

The updater SHALL report source-vs-installed cache verification when it can locate both trees.

#### Scenario: Cache matches source
- **WHEN** an installed plugin cache tree exists
- **AND** the marketplace source tree is known
- **AND** both trees have the same fingerprint
- **THEN** the updater reports `plugin-cache-verify` with status `matches-source`.

#### Scenario: Cache differs from source
- **WHEN** an installed plugin cache tree exists
- **AND** the marketplace source tree is known
- **AND** the trees differ
- **THEN** the updater reports `plugin-cache-verify` with status `differs-from-source`.

### Requirement: Repository updater entrypoint delegates to canonical implementation

The repository-level maintenance script SHALL delegate to the canonical DevFlow updater implementation instead of maintaining a forked behavior copy.

#### Scenario: Root updater is invoked
- **WHEN** `dev/scripts/codex_auto_update_plugins_skills.py` is run
- **THEN** it loads and executes the DevFlow updater implementation
- **AND** it does not contain a separate updater implementation.
