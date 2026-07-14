## ADDED Requirements

### Requirement: DevFlow has one active methodology path

DevFlow SHALL use its own intake, OpenSpec planning, task ledger, execution, evidence, verification, and completion control plane together with a single static MattPocock engineering capability pack. It SHALL NOT expose an active methodology profile or roadmap provider selection.

#### Scenario: Active workflow config is read

- **WHEN** DevFlow reads a current `.dev-flow.json`
- **THEN** workflow behavior is determined without a methodology profile, roadmap provider, provider selector, roadmap binding, or provider lock
- **AND** no unselected methodology or roadmap implementation is loaded

#### Scenario: Canonical behavior artifacts are created

- **WHEN** a behavior-changing task is planned or executed
- **THEN** OpenSpec remains the canonical owner of proposal, design, specs, tasks, verification, sync, and archive state
- **AND** Matt skills create no competing canonical plan, ticket, roadmap, or completion artifact

### Requirement: Methodology capability routing is static and allowlisted

DevFlow SHALL route methodology capabilities through one checked-in static registry containing only DevFlow/OpenSpec owners and the approved Matt skills `grilling`, `tdd`, `diagnosing-bugs`, `code-review`, `codebase-design`, and `domain-modeling`.

#### Scenario: Decision and execution capabilities are resolved

- **WHEN** DevFlow resolves decision resolution, implementation planning, test-first execution, diagnosis, review, completion, orchestration, architecture, or goal-definition capabilities
- **THEN** it returns the fixed implementation recorded by the static registry
- **AND** the result contains no profile-conditional branch

#### Scenario: Architecture guidance has no domain-language trigger

- **WHEN** DevFlow resolves `architecture-guidance` without domain concepts, vocabulary, invariants, or bounded contexts in scope
- **THEN** it requires `codebase-design` only
- **AND** `domain-modeling` is required only through the separately triggered `domain-language-modeling` capability

#### Scenario: Disallowed Matt workflow skill is installed globally

- **GIVEN** `implement`, `to-spec`, `to-tickets`, `setup-matt-pocock-skills`, or another non-allowlisted Matt skill exists in the user environment
- **WHEN** DevFlow resolves or activates task capabilities
- **THEN** that skill is not routed, required, linked, or invoked automatically

#### Scenario: Approved upstream skill refers to an excluded workflow skill

- **WHEN** DevFlow materializes the approved project-local Matt skill
- **THEN** a deterministic recorded adaptation replaces the excluded handoff with the DevFlow/OpenSpec-owned capability boundary
- **AND** the untouched vendored upstream bytes and their original hashes remain available for provenance verification

### Requirement: Matt skills are pinned and project-local

DevFlow SHALL source the approved Matt skills from the stable `mattpocock/skills` `v1.1.0` release at commit `d574778f94cf620fcc8ce741584093bc650a61d3`, verify the recorded content hashes, and require project-local readiness for each triggered Matt capability.

#### Scenario: Required project-local skill matches provenance

- **WHEN** dependency diagnosis runs for a capability backed by a Matt skill
- **THEN** the matching project-local skill and all required resources are verified against the pinned provenance
- **AND** the capability is ready only when the project-local copy matches

#### Scenario: Only a user-global skill exists

- **GIVEN** a matching Matt skill is installed globally but is absent from the target project's `.agents/skills`
- **WHEN** project readiness is checked for its capability
- **THEN** readiness fails with a project-local activation action
- **AND** the global installation is not treated as sufficient

#### Scenario: Stable tag differs from upstream main

- **WHEN** upstream `main` changes while the pinned release content remains available
- **THEN** DevFlow continues to verify against the pinned release
- **AND** it does not fail readiness or upgrade automatically because of `main` drift

### Requirement: Capability activation is minimal and authorization-gated

DevFlow SHALL plan or activate only the project-local Matt skills required by explicitly triggered capabilities, and any write or installation SHALL retain the existing explicit authorization gates.

#### Scenario: One Matt-backed capability is requested in dry-run mode

- **WHEN** project activation is asked to prepare one Matt-backed capability without apply authorization
- **THEN** it reports only the required skill-link and installation actions
- **AND** it does not change project files, install dependencies, or activate unrelated skills

#### Scenario: Apply is not authorized

- **WHEN** a required Matt skill is missing and dependency installation or project writes are not explicitly authorized
- **THEN** DevFlow reports the blocking action
- **AND** performs no installation, link creation, commit, push, archive, or migration

### Requirement: Subagent execution is bounded by a DevFlow contract

DevFlow SHALL allow subagents only for independent work or scoped parallel evidence gathering, and SHALL require a validated Agent Task Contract before delegation. The primary agent SHALL own shared artifacts, integration, final verification, and the completion claim.

#### Scenario: Independent read-only investigations are delegated

- **WHEN** two or more investigations can run independently
- **THEN** each worker receives a bounded objective, allowed read scope, required evidence, authority, and stop conditions
- **AND** the primary agent integrates and validates their findings

#### Scenario: Implementation write sets overlap

- **WHEN** proposed subagent contracts assign the same path or shared generated artifact to multiple writers
- **THEN** validation fails before delegation
- **AND** the work is serialized or reassigned to one owner

#### Scenario: Worker returns partial or failed evidence

- **WHEN** a delegated worker does not satisfy its evidence contract
- **THEN** the corresponding execution-ledger item remains incomplete
- **AND** the primary agent does not claim completion from the worker status alone

### Requirement: Active methodology diagnosis excludes legacy providers

Normal DevFlow dependency, activation, updater, hook, verification, archive, and release diagnostics SHALL NOT enumerate, install, import, select, or fall back to Superpowers or GSD.

#### Scenario: Core capability diagnosis runs

- **WHEN** dependency diagnosis runs for any supported active capability
- **THEN** its checks and actions contain only the active DevFlow/OpenSpec/Matt contract and independently requested developer tools
- **AND** no Superpowers or GSD candidate, source, command, hook, skill, agent, or runtime is reported
