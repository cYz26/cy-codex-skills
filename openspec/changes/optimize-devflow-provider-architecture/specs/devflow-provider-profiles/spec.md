## ADDED Requirements

### Requirement: DevFlow Core is independently ready
DevFlow SHALL provide a complete core workflow with OpenSpec, planning,
execution evidence, review, completion proof, archive, and release gates without
requiring Superpowers, Matt skills, or GSD.

#### Scenario: Core has no external methodology or roadmap provider
- **WHEN** a project selects `methodology_profile: core` and `roadmap_provider: none`
- **AND** Superpowers, Matt skills, and GSD are absent
- **THEN** `coreReady` and `methodologyReady` are true
- **AND** core planning, TDD-evidence, review, and fresh completion-proof gates remain required when triggered

### Requirement: Provider axes are explicit and orthogonal
DevFlow SHALL resolve methodology profile independently from roadmap provider
without reusing workflow mode or the existing developer-helper `--strict` flag.

#### Scenario: Strict methodology does not imply GSD
- **WHEN** a project selects `strict-superpowers` and `roadmap_provider: none`
- **THEN** Superpowers capabilities are selected
- **AND** GSD is neither required nor inferred

#### Scenario: Existing strict CLI semantics remain compatible
- **WHEN** dependency diagnostics run with `--strict`
- **THEN** the flag continues to control developer-helper gates such as Plugin Eval
- **AND** methodology selection comes from the provider configuration or a separate methodology option

### Requirement: Capability readiness is separate from evidence readiness
DevFlow SHALL distinguish provider installation and capability availability from
the canonical evidence required to satisfy a runtime gate.

#### Scenario: TDD skill is installed but no RED evidence exists
- **WHEN** the selected provider exposes a TDD skill
- **AND** the active task requires test-first execution but has no RED evidence or approved not-applicable reason
- **THEN** provider readiness may be `ready`
- **AND** the `test-first-execution` evidence gate remains unsatisfied

### Requirement: Provider resolution binds one verifiable source
DevFlow SHALL bind every selected external provider to one source root, version
or ref, channel, and content identity and SHALL NOT combine skills from
different provider distributions.

#### Scenario: Multiple Superpowers sources are available
- **WHEN** more than one Superpowers cache root can satisfy the strict profile
- **AND** no explicit project binding or provider lock selects one source
- **THEN** strict readiness is `ambiguous_source`
- **AND** DevFlow does not silently choose the highest version or mix skills across roots

#### Scenario: Matt source is selected
- **WHEN** `lean-matt` is activated
- **THEN** the provider lock records the configured repository/ref or commit, source paths, and selected skill hashes
- **AND** a drifted or unverifiable skill source is reported before routing

#### Scenario: Portable selector resolves a machine-local lock
- **WHEN** `.dev-flow.json` names a provider source record without an absolute path
- **THEN** DevFlow resolves a matching local root and records its digest/hashes in `.planning/devflow/providers.lock.json`
- **AND** selector precedence is explicit config, matching lock, then unique compatible discovery

#### Scenario: First activation has ambiguous candidates
- **WHEN** discovery finds multiple compatible sources and no selector or matching lock exists
- **THEN** dry-run reports candidate source identifiers and `ambiguous_source`
- **AND** persisting a selection requires an apply-authorized provider-source override

### Requirement: Hook checks follow the selected manifest
DevFlow SHALL require and trust-check a provider hook only when the selected
distribution declares that hook for a selected capability.

#### Scenario: Curated Superpowers is hookless
- **WHEN** strict methodology selects a compatible Superpowers distribution whose manifest declares no SessionStart hook
- **THEN** strict readiness does not report `hook_missing`
- **AND** skill capability checks continue normally

#### Scenario: Selected distribution declares an executable hook
- **WHEN** the selected provider manifest declares a hook required by its adapter
- **AND** Codex trust is missing
- **THEN** the affected strict capability is blocked with `hook_untrusted_when_declared`
- **AND** DevFlow does not trust the hook automatically

### Requirement: Lean Matt routing uses only approved primitives
The `lean-matt` adapter SHALL map only approved composable skills and SHALL keep
Matt's alternate control-plane and mutating orchestration skills out of implicit
DevFlow routing.

#### Scenario: Lean capabilities are resolved
- **WHEN** the lean provider is ready
- **THEN** DevFlow may map decision resolution to `grilling`, TDD to `tdd`, diagnosis to `diagnosing-bugs`, review to `code-review`, and architecture guidance to `codebase-design` or `domain-modeling`
- **AND** implementation planning and completion proof remain DevFlow/OpenSpec-owned

#### Scenario: Matt control-plane skills are installed
- **WHEN** `ask-matt`, `to-spec`, `to-tickets`, `implement`, `triage`, or `wayfinder` are present
- **THEN** none appears in the lean adapter's implicit routing table
- **AND** explicit invocation remains subject to canonical artifact and side-effect authority

### Requirement: Strict Superpowers remains an optional adapter
The strict adapter SHALL preserve Superpowers decision, planning, TDD,
diagnosis, review, completion, orchestration, and finishing capabilities without
making Superpowers a core dependency or canonical artifact owner.

#### Scenario: Strict capability is unavailable
- **WHEN** a selected strict capability is missing from the bound Superpowers source
- **THEN** `methodologyReady` is false for strict work
- **AND** an unrelated project using `core` is not blocked

#### Scenario: Superpowers produces a draft artifact
- **WHEN** a Superpowers plan, spec, SDD report, or review note exists
- **THEN** it cannot satisfy a DevFlow canonical gate until promoted into OpenSpec, evidence, or an approved ledger

### Requirement: Provider side effects cannot expand user authority
DevFlow SHALL enforce a machine-readable side-effect policy on its own provider
routing, activation, updater, hook, and promotion paths, while retaining AGENTS,
ENGINEERING_POLICY, OpenSpec, and user authority as the outer boundary.

#### Scenario: Provider requests an external mutation
- **WHEN** a routed provider action would write a tracker, commit, push, create a PR, install or update a dependency, clean files, archive, or release
- **AND** that effect lacks explicit user authorization
- **THEN** DevFlow does not perform or automatically route the effect
- **AND** diagnostics return a non-mutating next action

#### Scenario: Approved OpenSpec execution writes code and tests
- **WHEN** an approved task declares a code/test write set and validation commands
- **THEN** the selected provider may operate within that write set
- **AND** all other side-effect classes remain governed by their own authorization gates

#### Scenario: Provider writes a draft or canonical artifact
- **WHEN** a provider wants to write planning or review output
- **THEN** draft output is limited to its declared draft path/write set
- **AND** canonical output is written only by an approved DevFlow/OpenSpec promoter

#### Scenario: Provider requests branch isolation
- **WHEN** a provider recommends a branch or worktree
- **THEN** DevFlow permits it only when the approved execution plan declares that isolation action
- **AND** otherwise it continues inline only if the plan allows or stops for direction

#### Scenario: Provider reads a tracker
- **WHEN** tracker context is within the user's task scope
- **THEN** read-only tracker access may occur
- **AND** any tracker write remains separately authorization-gated

#### Scenario: Goal state change is not explicitly requested
- **WHEN** goal definition is useful but the user has not requested goal creation or control
- **THEN** DevFlow returns a Goal Mode Prompt
- **AND** neither DevFlow nor the provider changes active goal state

### Requirement: Diagnostics and activation are selection-scoped
DevFlow SHALL check, install, link, update, and recommend only dependencies of
the selected profile, selected roadmap provider, or currently triggered
on-demand capability.

#### Scenario: Unselected provider is installed
- **WHEN** Superpowers or Matt is available but not selected
- **THEN** it is reported as `available_unselected` or an advisory pollution risk
- **AND** it does not participate in readiness, activation, updater, or fallback selection

#### Scenario: Dry-run activation is requested
- **WHEN** activation or migration runs without explicit apply authorization
- **THEN** it emits commands and file actions without changing config, caches, links, runtime files, or planning artifacts

### Requirement: Goal definition is an on-demand capability
DevFlow SHALL declare `define-goal` provenance and diagnose it only when the
Goal Suitability Gate or an explicit user request requires goal definition.

#### Scenario: Ordinary task does not need a goal
- **WHEN** a core task is not goal-suitable and the user did not request Goal Mode
- **THEN** missing `define-goal` does not reduce core readiness

#### Scenario: Goal-backed work requires goal definition
- **WHEN** the Goal Suitability Gate requires goal definition
- **THEN** DevFlow reports the `goal-definition` capability status and routes to `define-goal` if available
- **AND** DevFlow scripts do not call goal tools automatically

### Requirement: New and legacy selections are deterministic
DevFlow SHALL write `core + none` for new scaffolds and SHALL preserve existing
unconfigured repositories through content-driven, read-only inference until an
explicit migration is applied.

#### Scenario: New project is scaffolded
- **WHEN** DevFlow creates provider configuration for a new repository
- **THEN** the canonical configuration selects `methodology_profile: core` and `roadmap_provider: none`
- **AND** no external provider is installed automatically

#### Scenario: Legacy profile is inferred
- **WHEN** an existing repository lacks explicit provider configuration
- **THEN** diagnostics report the inference source, evidence, confidence, and migration recommendation
- **AND** no profile, link, runtime, or artifact is changed automatically

#### Scenario: Legacy Superpowers project is inferred
- **WHEN** an unconfigured existing repository has project-local Superpowers links that resolve to one verifiable provider source
- **THEN** methodology status is `legacy_profile_inferred` with effective profile `strict-superpowers`
- **AND** installed standalone Matt skills do not replace or override that selection
