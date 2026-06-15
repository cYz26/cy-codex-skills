# devflow-dependency-workflow Specification

## Purpose

Define DevFlow's integration rules for external workflow tools, required dependency validation, project-local skill refresh behavior, and update discovery.

## ADDED Requirements
### Requirement: Superpowers artifacts map into canonical DevFlow workflow artifacts

DevFlow SHALL treat Superpowers as the discipline and gate layer while keeping OpenSpec, GSD, and DevFlow planning files as the canonical durable artifacts.

#### Scenario: Behavior change planning uses OpenSpec as source of truth
- **WHEN** Superpowers brainstorming or writing-plans is used for a behavior, API, data, integration, compatibility, or error-handling change
- **THEN** the resulting approved design and task content is captured in `openspec/changes/<change-id>/proposal.md`, `design.md`, `specs/`, or `tasks.md`
- **AND** any `docs/superpowers/` artifact is treated as draft input or review notes rather than the canonical source of truth

#### Scenario: Phase planning uses GSD phase files as source of truth
- **WHEN** Superpowers writing-plans is used for stage, milestone, or phase-level work
- **THEN** the resulting plan content is captured in `.planning/phases/.../PLAN.md` or another DevFlow-approved ledger
- **AND** GSD phases remain governance containers rather than technical completion boundaries

### Requirement: Dependency validation covers routed GSD skills

DevFlow dependency checks SHALL require every GSD skill that DevFlow routing instructions invoke as part of the core workflow.

#### Scenario: Workflow doctor dependency is validated
- **WHEN** dependency validation runs for a project using DevFlow
- **THEN** it checks that `.codex/skills/gsd-progress/SKILL.md` exists
- **AND** missing `gsd-progress` is reported as a required dependency failure

#### Scenario: Project-local GSD Core runtime is validated
- **WHEN** dependency validation runs for a project using DevFlow
- **THEN** it checks that `.codex/gsd-core/bin/gsd-tools.cjs` exists
- **AND** it does not require the legacy `gsd-sdk` executable

### Requirement: Project-local skill activation can refresh stale provider symlinks

DevFlow project activation SHALL detect project-local skill symlinks that point to an older provider source and SHALL refresh them only when explicitly requested.

#### Scenario: Stale symlink is reported without refresh
- **WHEN** a project-local skill is a symlink to a provider-owned source different from the selected current source
- **AND** activation runs without refresh enabled
- **THEN** activation reports the skill as linked to an existing source
- **AND** it does not rewrite the symlink

#### Scenario: Stale symlink refresh is explicit
- **WHEN** a project-local skill is a symlink to a provider-owned source different from the selected current source
- **AND** activation runs with refresh enabled
- **THEN** activation rewrites the symlink to the selected current source
- **AND** reports the skill as refreshed

### Requirement: External update checks are read-only before apply

DevFlow update tooling SHALL be able to report installed and latest GSD/OpenSpec versions without running mutating installers.

#### Scenario: Dry-run reports package version state
- **WHEN** the update script runs without `--apply`
- **THEN** it reports the installed and latest known GSD and OpenSpec versions when available
- **AND** it does not execute `npx get-shit-done-cc@latest`, `npm update -g @fission-ai/openspec`, or equivalent mutating update commands

#### Scenario: GSD checks use OpenGSD Core
- **WHEN** the update script runs for a DevFlow project with `.codex/gsd-core/VERSION`
- **THEN** it reports the GSD package state using `@opengsd/gsd-core`
- **AND** apply mode uses `npx -y @opengsd/gsd-core@latest --codex --local --profile=standard`
- **AND** it does not reference `get-shit-done-cc` or `gsd-sdk`

### Requirement: Context audit instructions are portable

DevFlow context-tool audit documentation SHALL use commands that work on systems with a normal `python3` executable.

#### Scenario: Context audit command is not host-specific
- **WHEN** the `context-tool-audit` skill is read
- **THEN** its command examples use `python3`
- **AND** they do not require `/opt/homebrew/bin/python3.11`
