## ADDED Requirements

### Requirement: Release package contains no active legacy methodology integration

The DevFlow development and release packages SHALL contain no active Superpowers or GSD routing, selection, installation, activation, readiness, hooks, verification, archive, benchmark, fixture, or fallback behavior.

#### Scenario: Active source and release surfaces are scanned

- **WHEN** maintained runtime, skill, hook, template, documentation, test-fixture, and generated release paths are checked
- **THEN** Superpowers and GSD references are absent outside the explicit legacy inspector, its tests, the current change artifacts, and source-only historical evidence
- **AND** no allowed historical path is imported, packaged as active guidance, or used by readiness

#### Scenario: Packaged runtime is executed without legacy dependencies

- **GIVEN** Superpowers and GSD are not installed
- **WHEN** packaged DevFlow smoke and dependency checks run
- **THEN** the supported active workflow remains functional
- **AND** no missing legacy-provider warning or action is emitted

### Requirement: Matt methodology provenance is minimal and source-pinned

DevFlow release provenance SHALL retain only the approved Matt methodology source and exact skill hashes and SHALL contain no Superpowers or GSD dependency/source/install record.

#### Scenario: Dependency provenance is inspected

- **WHEN** the development or release provenance file is parsed
- **THEN** it pins `mattpocock/skills` `v1.1.0` to commit `d574778f94cf620fcc8ce741584093bc650a61d3`
- **AND** it records exactly the six approved Matt skill hashes and required license attribution
- **AND** it contains no Superpowers or GSD provider source or dependency

### Requirement: Simplified source and release remain equivalent

Release promotion SHALL derive the packaged DevFlow runtime, scripts, skills, docs, templates, provenance, and tests from the verified development source, and repeated promotion SHALL remain idempotent.

#### Scenario: Release is promoted after development verification

- **WHEN** the complete source-only pre-promotion runner, strict repository-wide OpenSpec validation, and diff check are recorded in a current source-hash-bound receipt, the active change and implementation gates are verified, separate durable release authorization is present, and promotion completes
- **THEN** every managed source/release counterpart is content-equivalent
- **AND** runtime manifest and source-commit metadata describe the promoted source
- **AND** the full post-promotion development suite includes the generated-release-dependent smoke and packaged-runtime modules

#### Scenario: Promotion is repeated without source changes

- **WHEN** the release promotion command runs again
- **THEN** it reports `current`
- **AND** produces no managed-content diff

### Requirement: Simplified workflow has end-to-end release evidence

The change SHALL record passing focused and full development tests, packaged tests, strict OpenSpec validation, release runtime verification, workflow validation, diff checks, and release-target Plugin Eval before claiming completion.

#### Scenario: Completion evidence is reviewed

- **WHEN** the change is presented as implemented
- **THEN** the evidence record names exact commands and results for every required validation layer
- **AND** release-target Plugin Eval has zero failures
- **AND** every warning is fixed or has an approved documented disposition
