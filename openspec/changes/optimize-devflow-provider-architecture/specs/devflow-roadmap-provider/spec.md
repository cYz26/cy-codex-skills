## ADDED Requirements

### Requirement: GSD is an optional roadmap provider
DevFlow SHALL require GSD runtime, skills, agents, and lifecycle checks only
when the resolved roadmap provider is `gsd`.

#### Scenario: Roadmap provider is none
- **WHEN** a project resolves `roadmap_provider: none`
- **AND** GSD is missing, drifted, disabled, or smoke-failing
- **THEN** `coreReady` and methodology readiness are unaffected
- **AND** DevFlow does not install, update, link, invoke, or scaffold GSD artifacts

#### Scenario: GSD is selected but unavailable
- **WHEN** a project resolves `roadmap_provider: gsd`
- **AND** required GSD capabilities are unavailable
- **THEN** `roadmapReady` is false and roadmap-bound operations are blocked
- **AND** ordinary unbound OpenSpec work remains available

### Requirement: GSD routing requires roadmap suitability or explicit selection
DevFlow SHALL route to GSD only for explicit roadmap, milestone, phase,
dependency-wave, persistent-UAT, or multi-session lifecycle needs.

#### Scenario: Ordinary multi-slice OpenSpec change
- **WHEN** work has multiple capability slices but no roadmap lifecycle requirement
- **THEN** DevFlow uses OpenSpec, Task Ledger, and DevFlow evidence
- **AND** it does not infer or require GSD solely because the task is non-trivial

#### Scenario: Change is bound to a GSD phase
- **WHEN** `.dev-flow.json` records an active binding with OpenSpec change id, GSD phase id, milestone, and status
- **THEN** behavior completion requires OpenSpec verification
- **AND** phase transition additionally requires GSD phase verification

#### Scenario: Bound phase is missing or renamed
- **WHEN** an active binding references a phase that the selected GSD provider cannot resolve
- **THEN** status is `manual_review_required` and the phase transition is blocked
- **AND** DevFlow does not rewrite or guess the binding

#### Scenario: Bound change is archived or roadmap provider is disabled
- **WHEN** both OpenSpec and GSD verification pass and the change is archived
- **THEN** the binding is preserved with status `archived`
- **AND** switching roadmap provider to `none` preserves existing bindings as inactive and removes their GSD runtime gate

### Requirement: DevFlow and GSD have disjoint planning namespaces
DevFlow SHALL write only `.planning/devflow/**`; when GSD is selected, GSD SHALL
be the sole writer of root roadmap/state/config, phase, milestone, todo, and
root codebase artifacts.

#### Scenario: DevFlow records core verification
- **WHEN** DevFlow records command evidence in any roadmap configuration
- **THEN** it writes under `.planning/devflow/verification/**`
- **AND** it does not create or append a file under `.planning/phases/**`

#### Scenario: Root state is GSD-owned
- **WHEN** root `.planning/STATE.md` contains `gsd_state_version`
- **THEN** DevFlow does not parse, rewrite, merge, or normalize that file
- **AND** DevFlow uses `.planning/devflow/STATE.md` for its own state

#### Scenario: Codebase files differ only by case
- **WHEN** DevFlow and GSD run on a case-insensitive filesystem
- **THEN** DevFlow codebase artifacts remain under `.planning/devflow/codebase/**`
- **AND** GSD root `.planning/codebase/**` files are not overwritten

### Requirement: Legacy roadmap inference is content-driven
DevFlow SHALL infer roadmap ownership from explicit configuration, migration
state, and strong content markers and SHALL NOT infer GSD from installed runtime
or skills alone.

#### Scenario: Old DevFlow project contains unused GSD installation
- **WHEN** a repository has `.codex/gsd-core`, GSD skills, or agents
- **AND** its planning state contains DevFlow `workflow_version` markers without strong GSD project markers
- **THEN** it is inferred as legacy DevFlow/core rather than GSD
- **AND** existing GSD files are preserved

#### Scenario: Real GSD project has canonical markers
- **WHEN** a repository has `gsd_state_version`, GSD PROJECT/config, a parser-valid ROADMAP, or canonical GSD phase filenames
- **THEN** diagnostics infer GSD roadmap ownership with the supporting evidence
- **AND** DevFlow does not write root GSD paths

#### Scenario: Markers conflict
- **WHEN** DevFlow and GSD ownership markers are mixed or contradictory
- **THEN** status is `manual_review_required`
- **AND** migration apply performs no file changes

### Requirement: Planning migration is dry-run-first and reversible
DevFlow SHALL produce a hash-based migration plan before apply and SHALL require
explicit authorization for both artifact migration and dependency activation.

#### Scenario: Migration dry-run is executed
- **WHEN** migration runs without apply authorization
- **THEN** it reports current/target owner, evidence, source hashes, planned actions, conflicts, the snapshot it would create, rollback, and approval requirements
- **AND** it creates no snapshot and all repository and external state remains unchanged

#### Scenario: Migration apply succeeds
- **WHEN** the user explicitly approves an unconflicted migration
- **THEN** DevFlow creates a hash-verified snapshot, uses atomic writes, persists explicit provider selection, and records a rollback manifest
- **AND** a second apply is a no-op

#### Scenario: User-modified or mixed artifact is found
- **WHEN** migration cannot prove generated ownership or safe transformation
- **THEN** it stops before overwriting or deleting the artifact
- **AND** the report records a manual review action

#### Scenario: Migration apply fails before commit
- **WHEN** an authorized apply fails before all atomic replacements complete
- **THEN** original files, config, and lock remain at their pre-apply hashes
- **AND** no partial migrated state is treated as active

#### Scenario: Authorized rollback is requested
- **WHEN** a completed migration has an intact rollback manifest and current owned-file hashes still match the manifest
- **THEN** rollback restores config, lock, files, owners, hashes, and readiness to the recorded pre-migration state

#### Scenario: User edits a migrated file before rollback
- **WHEN** current content no longer matches the rollback manifest because of user edits
- **THEN** rollback returns `manual_review_required`
- **AND** it does not overwrite the edited file

### Requirement: Provider switching is non-destructive
Switching roadmap provider SHALL change routing and readiness without deleting
runtime files, skills, agents, links, user content, or historical evidence.

#### Scenario: GSD project switches to none
- **WHEN** an approved configuration changes `roadmap_provider` from `gsd` to `none`
- **THEN** DevFlow stops routing new work to GSD
- **AND** all GSD runtime and planning artifacts remain intact unless separately approved for cleanup

#### Scenario: Core project switches to GSD
- **WHEN** an approved configuration selects GSD
- **THEN** ownership and state migration must pass before GSD initialization
- **AND** DevFlow does not convert a legacy placeholder roadmap or phase into a real GSD project silently

### Requirement: Compatibility state resolution has a bounded window
DevFlow SHALL prefer namespaced state, permit legacy DevFlow state only in
declared compatibility mode through the `1.0.0` sunset release, and reject GSD
state as DevFlow input. Version comparison SHALL use numeric semantic-version
tuples and SHALL NOT extend the window for prerelease or build suffixes.

#### Scenario: Namespaced DevFlow state exists
- **WHEN** `.planning/devflow/STATE.md` exists
- **THEN** all DevFlow state consumers use it

#### Scenario: Legacy DevFlow state is still supported
- **WHEN** namespaced state is absent, root state has `workflow_version`, GSD is not selected, and compatibility support has not expired
- **THEN** DevFlow may read the legacy state with a migration warning
- **AND** any operation requiring a state write returns `migration_required` instead of rewriting root state

#### Scenario: Legacy compatibility has expired
- **WHEN** namespaced state is absent and root state has `workflow_version` after the declared sunset release
- **THEN** DevFlow does not read or write the root state
- **AND** it returns a no-write migration action and the sunset version

### Requirement: Planning artifact tracking policy is explicit
DevFlow SHALL distinguish canonical ownership from Git tracking and SHALL report
whether provider planning artifacts are tracked, partially tracked, or local
only without editing ignore rules automatically.

#### Scenario: Planning directory is ignored
- **WHEN** Git ignore rules exclude `.planning/**`
- **THEN** doctor reports `local_only` and the collaboration/recovery residual risk
- **AND** generated guidance does not describe those artifacts as checked in

#### Scenario: Only some required planning paths are tracked
- **WHEN** provider-owned required paths have mixed tracked and ignored status
- **THEN** doctor reports `partially_tracked` and enumerates both sets
- **AND** it does not edit ignore rules automatically

#### Scenario: GSD requires committed documents
- **WHEN** selected GSD has `commit_docs: true` and required GSD paths are local-only or partially tracked
- **THEN** `roadmapReady` is false because the declared commit contract cannot be satisfied
- **AND** core and methodology readiness remain unaffected

#### Scenario: Tracking is not a selected-provider requirement
- **WHEN** roadmap is `none` or selected GSD has `commit_docs: false`
- **THEN** local-only or partial tracking is advisory
- **AND** doctor records the residual collaboration/recovery risk
