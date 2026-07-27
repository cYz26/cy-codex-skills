## ADDED Requirements

### Requirement: Ownership is registered before artifact creation

DevFlow SHALL grant automatic cleanup eligibility only through a valid
Generated Artifact Contract sealed before the owning command creates an
artifact.

#### Scenario: Task registers an isolated output root

- **WHEN** a task seals a contract for an absent or empty task/run-specific root before executing the bound command
- **THEN** DevFlow records the repository, task, run, owner, command digest, root identity, retention policy, and before-state
- **AND** later artifacts under that root may be evaluated for automatic cleanup

#### Scenario: Task registers adjacent output scope

- **WHEN** a tool cannot redirect generated output into an isolated root
- **THEN** the contract MUST predeclare a parent-scoped output pattern and complete before-state
- **AND** only exact entries absent from that before-state may become cleanup candidates

#### Scenario: Artifact predates registration

- **WHEN** an artifact exists before its contract is sealed or no valid contract exists
- **THEN** DevFlow MUST NOT infer ownership from its name, extension, ignore status, or directory
- **AND** cleanup requires a Human Gate

### Requirement: Observed manifests bind exact generated artifacts

DevFlow SHALL expand every contract-matching artifact into an immutable
manifest with exact identity and ownership evidence.

#### Scenario: Generated entries are observed

- **WHEN** the bound command finishes and DevFlow observes its declared output scopes
- **THEN** the manifest records each exact relative path, type, device, inode, mode, link count, owner, timestamps, size, content digest when applicable, and directory membership
- **AND** it records the owning command result and process/lease completion

#### Scenario: Observation crosses declared scope

- **WHEN** an observed candidate escapes its declared root, resolves through a symlink, or requires following an unowned link
- **THEN** the manifest is invalid for automatic cleanup
- **AND** the lifecycle decision is `HUMAN_GATE`

### Requirement: Cleanup classification is deterministic and read-only

DevFlow SHALL classify a contract and manifest without mutating files,
processes, configuration, workflow state, or evidence.

#### Scenario: Exact task-owned artifact is eligible

- **WHEN** registration, baseline, repository identity, ownership, scope, process exit, retention, protection, tracked-state, identity, and membership checks all pass
- **THEN** the read-only decision is `AUTO_CLEAN`

#### Scenario: Owner is still active

- **WHEN** the owning process or lease remains live and all other checks are valid
- **THEN** the decision is `WAIT_OWNER`
- **AND** DevFlow performs no deletion and may retry without opening a Human Gate

#### Scenario: Artifact is retained

- **WHEN** the contract marks an artifact for evidence retention or promotion
- **THEN** the decision is `RETAIN`
- **AND** cleanup does not run until the retention contract changes through its owning workflow

#### Scenario: Ownership or identity is unsafe

- **WHEN** an artifact is unregistered, pre-existing, tracked, protected, shared, externally located outside an isolated root, occupied by another owner, or identity-drifted
- **THEN** the decision is `HUMAN_GATE`
- **AND** the result includes the exact failed invariant

### Requirement: Automatic cleanup is exact and fail closed

DevFlow SHALL apply automatic cleanup only to a current `AUTO_CLEAN` plan and
MUST revalidate every invariant immediately before the first mutation.

#### Scenario: Exact cleanup succeeds

- **WHEN** apply mode revalidates an `AUTO_CLEAN` plan without drift
- **THEN** it removes exact non-directory entries without following links
- **AND** removes exact directories deepest-first only when empty
- **AND** uses no wildcard or recursive deletion

#### Scenario: Preflight changes before mutation

- **WHEN** any contract, manifest, repository, process, tracked-state, identity, hash, or directory-membership value changes before the first removal
- **THEN** cleanup stops with zero mutation
- **AND** the receipt reports the failed invariant

#### Scenario: Operating-system failure occurs after some removals

- **WHEN** an exact removal fails after earlier entries were removed
- **THEN** DevFlow stops further mutation
- **AND** emits a failed receipt listing exact completed and remaining entries
- **AND** MUST NOT report cleanup complete or retry unrecorded work

#### Scenario: Cleanup is replayed after success

- **WHEN** apply mode receives a valid successful receipt and all exact targets remain absent
- **THEN** it returns the same completed postcondition without additional mutation

### Requirement: Cleanup receipts prove scope and postconditions

DevFlow SHALL emit a versioned cleanup receipt bound to the contract,
manifest, decision, exact mutation result, and post-cleanup observation.

#### Scenario: Successful receipt is inspected

- **WHEN** automatic cleanup succeeds
- **THEN** the receipt records contract and manifest hashes, decision, removed entries, zero unlisted mutation, exact absent targets, retained targets, and no process/configuration/Git effect

#### Scenario: Receipt does not match its inputs

- **WHEN** a receipt references changed contract or manifest bytes or omits an exact mutation result
- **THEN** DevFlow rejects the receipt
- **AND** dependent task or worker cleanup remains incomplete

### Requirement: Main tasks and workers share one lifecycle

DevFlow SHALL support Generated Artifact Contract references from main-task
execution and Agent Task Contracts without introducing a parallel cleanup
policy.

#### Scenario: Worker declares generated artifacts

- **WHEN** an Agent Task Contract references a Generated Artifact Contract
- **THEN** G41 post-validation requires a valid terminal cleanup receipt
- **AND** `cleanup_complete` cannot become true while a generated artifact remains unresolved

#### Scenario: Existing task has no artifact contract

- **WHEN** a task does not reference a Generated Artifact Contract
- **THEN** existing task and worker validation behavior remains compatible
- **AND** no artifact gains automatic cleanup authority

### Requirement: Validation surfaces remain read-only

DevFlow hooks, doctors, validators, and stop policies SHALL only inspect and
report Generated Artifact Lifecycle state.

#### Scenario: Validator observes eligible cleanup

- **WHEN** a read-only validation surface observes an `AUTO_CLEAN`, `WAIT_OWNER`, `RETAIN`, or `HUMAN_GATE` decision
- **THEN** it reports the decision and next action
- **AND** it does not invoke cleanup apply mode

#### Scenario: Orchestrator receives auto-clean decision

- **WHEN** an approved execution route receives `AUTO_CLEAN`
- **THEN** the orchestrator may invoke the explicit cleanup apply operation under the sealed standing contract
- **AND** ordinary automatic reclamation does not require a per-run Human Gate

### Requirement: Source and release behavior remain equivalent

The DevFlow release package SHALL contain the same Generated Artifact
Lifecycle schemas, module, CLI, templates, and tests as the development source.

#### Scenario: Release counterpart is verified

- **WHEN** release packaging and runtime verification run
- **THEN** every managed generated-artifact file is present and byte-equivalent
- **AND** packaged smoke tests exercise read-only classification and exact apply behavior without network or user configuration mutation
