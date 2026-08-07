## Purpose

Define a deterministic and reversible way to bring an established DevFlow
project from a supported older workflow configuration to the current project
contract without overwriting project-owned guidance or cleaning historical data.

## ADDED Requirements

### Requirement: Refresh has a Skill orchestration seam and a deterministic project seam
DevFlow SHALL keep human-facing refresh orchestration separate from the
deterministic refresh of one project.

#### Scenario: A DevFlow upgrade precedes project refresh
- **WHEN** a user asks to refresh DevFlow and one or more established projects
- **THEN** the refresh workflow verifies the named DevFlow installation and cache before producing a project apply plan
- **AND** project discovery, cross-project ordering, and Human Gates remain owned by the refresh Skill

#### Scenario: A project plan is requested directly
- **WHEN** the project refresh interface is invoked without apply authorization
- **THEN** it inspects exactly one project and returns a deterministic plan without writing any project, report, state, candidate, or cache path

#### Scenario: A directory has no trusted DevFlow adoption marker
- **WHEN** project planning finds neither active DevFlow configuration nor another trusted DevFlow control-plane marker
- **THEN** it returns `not_applicable`
- **AND** it does not create workflow state or invite implicit project adoption

### Requirement: Project workflow schema is versioned independently
DevFlow SHALL distinguish the plugin release version, migration-engine schema,
project workflow schema, and refresh-contract identity.

#### Scenario: A project already matches the current schema
- **WHEN** the observed project configuration and stored refresh evidence match the current project workflow schema and refresh contract
- **THEN** the plan reports the project schema as current without scheduling a configuration rewrite

#### Scenario: The contract advances beyond the initial schema
- **WHEN** the manifest names a current project-schema head and immutable configuration target greater than version 1
- **THEN** baseline detection, create-if-absent planning, staging, and verification derive the current schema and exact target bytes from that manifest contract
- **AND** no runtime path assumes that `full-openspec` configuration syntax always means schema 1

#### Scenario: A supported older schema is detected
- **WHEN** trusted project evidence identifies exactly one supported older project schema
- **THEN** the planner resolves exactly one ordered migration path to the current schema
- **AND** every migration step has a stable identifier and verification contract

#### Scenario: A migration registry is invalid
- **WHEN** the migration path contains a gap, fork, cycle, duplicate identifier, unknown predecessor, or no route to the current schema
- **THEN** planning fails closed before any project write

#### Scenario: A baseline cannot be proved uniquely
- **WHEN** state, configuration shape, or trusted fingerprints identify no baseline or more than one baseline
- **THEN** the plan reports `baseline_ambiguous`
- **AND** migration apply remains unavailable until a human records the disposition and a fresh plan is produced

#### Scenario: Configuration and stored state disagree on schema
- **WHEN** trusted configuration evidence and trusted migration state identify different project schema versions
- **THEN** the plan reports `baseline_ambiguous` rather than treating state as ordinary stale metadata
- **AND** neither configuration migration nor state synchronization is available from that plan

### Requirement: Refresh plans are sealed, exact, and redacted
Every project refresh apply SHALL be derived from a deterministic read-only plan
that binds source identity, observed state, intended actions, and exact managed
paths.

#### Scenario: A plan is produced
- **WHEN** read-only project inspection completes
- **THEN** the result identifies the project schema, refresh-contract identity, ordered action identifiers, exact repository-relative write set, before fingerprints, required authorizations, manual actions, verification contract, and a deterministic plan digest
- **AND** timestamps and redacted configuration values do not influence the digest

#### Scenario: Unrelated worktree state exists
- **WHEN** files outside the plan's managed read and write set are modified
- **THEN** the plan reports that unrelated work without claiming ownership
- **AND** those unrelated paths do not invalidate an otherwise safe plan

#### Scenario: A managed input changes after planning
- **WHEN** source identity, refresh-contract identity, an observed managed path, or an intended write set no longer matches the sealed plan
- **THEN** apply returns `plan_stale`
- **AND** no planned write occurs

#### Scenario: Legacy configuration contains sensitive values
- **WHEN** planning inspects retired selection fields or unrelated configuration values
- **THEN** JSON and human-readable output expose field names, classifications, types, and digests only
- **AND** raw values are not emitted in plans, errors, receipts, or history

### Requirement: Apply is explicit, transactional, and reversible
DevFlow SHALL apply only a sealed dependency-valid plan whose required
authorizations are explicitly present, and SHALL verify or restore the complete
selected transaction before returning.

#### Scenario: Required authorization is absent
- **WHEN** a plan contains an action whose named authorization was not supplied
- **THEN** apply returns `authorization_required`
- **AND** that action and every dependent action remain unwritten

#### Scenario: Preflight finds a conflict
- **WHEN** any selected path escapes the project, overlaps another selected path, crosses an untrusted symlink, has ambiguous ownership, or differs from its before fingerprint
- **THEN** the complete selected transaction is rejected before its first write

#### Scenario: A selected transaction succeeds
- **WHEN** every selected action is authorized, staged, promoted, and freshly verified
- **THEN** migration state advances only after all project files pass verification
- **AND** DevFlow writes both apply and verification receipts that independently bind before and after fingerprints, actions, authorizations, changed paths, preserved paths, and rollback status

#### Scenario: Promotion or verification fails
- **WHEN** a selected write cannot be promoted or any post-apply requirement fails
- **THEN** DevFlow restores every already-promoted path to its recorded preimage in reverse order
- **AND** the result distinguishes `verification_failed_rolled_back` from `rollback_failed`
- **AND** migration state does not advance

#### Scenario: Explicit rollback follows a successful apply
- **WHEN** a human authorizes rollback from a successful apply receipt and every affected path still matches its recorded after fingerprint
- **THEN** DevFlow restores the complete transaction and emits a rollback receipt
- **AND** it refuses to overwrite a path edited after apply

### Requirement: Known legacy configuration can migrate without discarding current settings
DevFlow SHALL support an explicit migration of recognized retired workflow
selection fields to the current canonical workflow mode while preserving
unrelated project configuration.

#### Scenario: A trusted legacy configuration is eligible
- **WHEN** `.dev-flow.json` is a trusted regular project file, has one recoverable exact preimage, and contains a non-conflicting recognized legacy shape
- **THEN** the plan removes only the retired selection fields
- **AND** sets `workflow.mode` to `full-openspec`
- **AND** preserves every unrelated root and workflow setting's JSON value and type exactly
- **AND** requires the named workflow-configuration-migration authorization

#### Scenario: Legacy aliases conflict
- **WHEN** equivalent retired fields appear with conflicting values or the current workflow object cannot be preserved safely
- **THEN** the configuration action is `manual_only`
- **AND** no automatic rewrite or cleanup is offered

#### Scenario: A recoverable preimage is unavailable
- **WHEN** the target configuration is untracked, already modified, non-regular, symlinked, unreadable, or otherwise lacks an exact trusted rollback source
- **THEN** the configuration action is `manual_only`
- **AND** all existing content remains unchanged

#### Scenario: A trusted adopted project lacks configuration
- **WHEN** a project has a trusted DevFlow control plane but `.dev-flow.json` is absent
- **THEN** an explicitly authorized plan may create the current canonical configuration
- **AND** rollback may remove it only while it still matches the receipt's after fingerprint

### Requirement: Project-owned guidance and legacy data remain protected
Project refresh SHALL distinguish safe managed refresh actions from human-owned
merges, ambiguous content, and separately authorized cleanup.

#### Scenario: Active AGENTS guidance is current
- **WHEN** active `AGENTS.md` satisfies the current durable DevFlow guidance contract
- **THEN** the plan reports AGENTS status `unchanged`
- **AND** does not create a generated candidate solely because scaffold would render one

#### Scenario: Active AGENTS guidance is stale
- **WHEN** active `AGENTS.md` lacks current durable workflow guidance
- **THEN** the plan reports `agents_merge_required`
- **AND** an authorized apply may create a non-conflicting `AGENTS.md.generated` candidate
- **AND** the interface never overwrites or merges active `AGENTS.md`

#### Scenario: A generated AGENTS candidate conflicts
- **WHEN** `AGENTS.md.generated` already exists with content not proven to be the same planned candidate
- **THEN** candidate creation is blocked and both files are preserved

#### Scenario: Legacy or custom skill content exists
- **WHEN** legacy `.codex/skills`, historical planning data, a non-symlink managed skill target, or a custom official-skill copy is found
- **THEN** refresh reports the exact conflict or manual action
- **AND** never deletes, overwrites, or reclassifies that content as automatically owned

#### Scenario: Safe and manual actions coexist
- **WHEN** a sealed plan contains dependency-independent safe actions and manual-only actions
- **THEN** apply may execute only an explicitly selected dependency-closed safe subset
- **AND** final project status remains incomplete until every required manual action is resolved and a fresh verification passes

### Requirement: Fresh verification determines completion
Project refresh SHALL derive completion from fresh structured verification rather
than command exit codes or the fact that writes were attempted.

#### Scenario: Apply completes successfully
- **WHEN** selected actions have been applied
- **THEN** DevFlow reruns project migration sync, workflow validation, cache-drift diagnosis, configuration-schema verification, AGENTS disposition, and managed-path readback
- **AND** reports every included, skipped, changed, preserved, conflicting, and restart-required item

#### Scenario: Required review remains
- **WHEN** configuration migration, AGENTS merge, dependency installation, legacy cleanup, or another required Human Gate remains unresolved
- **THEN** the project is not reported as refreshed or current

#### Scenario: A non-Git project is inspected
- **WHEN** project planning or verification runs without Git metadata
- **THEN** read-only diagnostics and explicit path reporting remain available
- **AND** any action whose rollback contract requires Git evidence remains manual-only

### Requirement: Existing read-only consumers remain compatible
The enhanced project migration interface SHALL preserve the current read-only
hook, updater, and operator integration while routing all writes through the new
plan and verification contract.

#### Scenario: A current no-subcommand sync invocation runs
- **WHEN** an existing caller requests the legacy JSON sync report
- **THEN** it remains read-only and preserves the established current, migration-pending, blocked, and not-applicable summary fields
- **AND** additive refresh-engine fields do not require the caller to parse configuration values

#### Scenario: A legacy apply invocation is used
- **WHEN** an existing caller explicitly requests ordinary apply without the new workflow-configuration authorization
- **THEN** it routes through the same sealed planner, preflight, transaction, and verification implementation
- **AND** it does not migrate retired configuration or bypass a Human Gate

#### Scenario: Machine-readable status requires attention
- **WHEN** planning, apply, verification, or rollback requires review or fails
- **THEN** the CLI emits a stable status and next action in JSON
- **AND** returns a non-success exit class for authorization-required, conflict, stale-plan, dependency, or internal-failure outcomes
