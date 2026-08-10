## Purpose

Defines one fail-closed decision contract that distinguishes genuine missing authority from deterministic in-scope repair, exact cleanup, ordinary continuation, and technical evidence failure across DevFlow workflow surfaces.

## ADDED Requirements

### Requirement: Authority-delta resolution is total, exclusive, and centralized
DevFlow SHALL resolve each proposed workflow action through one authority-delta policy and SHALL return exactly one mutually exclusive decision from `CONTINUE`, `CONTINUE_WITH_MINIMAL_GUARD`, `DEFER_AND_CONTINUE`, `WAIT_OWNER`, `AUTO_CLEAN`, `FAIL_CLOSED_REPAIR`, or `AWAIT_HUMAN`.

#### Scenario: Normal approved action continues
- **WHEN** an action is within the current approved Goal, OpenSpec behavior, write set, and risk envelope and its evidence and identity are current
- **THEN** the resolver returns `CONTINUE`
- **AND** it reports no missing authority

#### Scenario: Decision precedence is deterministic
- **WHEN** one request appears eligible for more than one decision
- **THEN** untrusted evidence, ambiguity, invalid authority, identity drift, or material-risk expansion takes precedence over automatic cleanup, a minimal guard, deferral, or normal continuation
- **AND** the resolver emits exactly one decision with stable reason codes

#### Scenario: All decision inputs are bound
- **WHEN** the resolver evaluates an action
- **THEN** its result binds the active Goal, change, semantic plan, write set, action identity, ownership, risk class, effect target, evidence identity, and standing-authority contract when applicable
- **AND** a change to any bound authority input invalidates the prior result

### Requirement: Human Gates represent concrete missing authority only
DevFlow MUST return `AWAIT_HUMAN` only when continuation requires authority that the active approved contracts do not grant or would materially change the risk borne by the user.

#### Scenario: Missing authority creates one concrete gate
- **WHEN** an action requires an undeclared external effect, target, write set, dependency, public contract, persistence format, irreversible migration, new model/provider/account/credential privilege or spending envelope, product choice, or ownership decision
- **THEN** the resolver returns `AWAIT_HUMAN`
- **AND** emits a non-empty list of concrete missing authorities and one stable gate key

#### Scenario: Technical failure does not fabricate a Human Gate
- **WHEN** focused validation fails, evidence is incomplete, a receipt is stale, or a deterministic candidate drifts without requiring new authority to diagnose or repair
- **THEN** the resolver returns `FAIL_CLOSED_REPAIR`
- **AND** it MUST NOT write or recommend `awaiting_human` merely because work cannot yet continue

#### Scenario: Unknown ownership or material risk fails closed for a human decision
- **WHEN** available evidence cannot determine ownership or whether an action changes the user's material risk
- **THEN** the resolver returns `AWAIT_HUMAN`
- **AND** names the exact ownership or risk authority that is missing

### Requirement: Approved local and derived work does not reopen authority
DevFlow SHALL continue local, reversible, semantics-preserving, deterministically verifiable actions already covered by the approved slice without asking for implementation-strategy confirmation.

#### Scenario: Systemic local repair remains inside the slice
- **WHEN** a test exposes a policy defect whose systemic repair fits the approved behavior and write set without a dependency, public-contract expansion, or external effect
- **THEN** DevFlow continues the repair and records RED/GREEN evidence
- **AND** it does not create a new Human Gate for the chosen implementation strategy

#### Scenario: Derived evidence is refreshed
- **WHEN** an approved source change deterministically invalidates a generated provenance file, receipt, release counterpart, or verification record owned by the same slice
- **THEN** DevFlow refreshes that derived artifact through its declared writer and verification seam
- **AND** the refresh does not require additional authority

#### Scenario: Predeclared independent review runs
- **WHEN** the plan already requires an independent read-only review with named acceptance thresholds
- **THEN** DevFlow runs and records that review without another Human Gate

### Requirement: Standing Goal execution authority outlives attempt receipts
DevFlow SHALL distinguish stable human execution authority from ephemeral run and evidence receipts for predeclared model execution.

#### Scenario: Same-authority model attempt continues
- **WHEN** the active Goal envelope grants the exact task, provider, model, credential policy, cost policy, serial execution policy, effect, and target and current technical evidence exists
- **THEN** the resolver returns `CONTINUE` without requiring a release-oriented Standing Milestone Contract
- **AND** actual monetary cost is recorded and reported without a per-attempt currency confirmation

#### Scenario: Consumed or failed attempt is repaired rather than reauthorized
- **WHEN** an attempt receipt is consumed, stale, incomplete, or records a failed attempt while the stable execution boundary remains unchanged
- **THEN** the resolver returns `FAIL_CLOSED_REPAIR` for bounded repair, evidence refresh, refreeze, and a new attempt receipt
- **AND** the prior receipt's one-use lifecycle does not consume the standing human authority

#### Scenario: New same-authority attempt resumes
- **WHEN** bounded repair has restored current complete evidence and the next request changes only its attempt id
- **THEN** the resolver returns `CONTINUE`
- **AND** no `missingAuthority` or gate key is emitted

#### Scenario: Stable execution boundary changes
- **WHEN** the requested task, provider, model, credential privilege, cost policy, or serial/concurrency policy differs from the standing execution envelope
- **THEN** the resolver returns `AWAIT_HUMAN`
- **AND** names the exact stable execution authority that is missing

#### Scenario: Execution identity is malformed
- **WHEN** a `model.*` request or standing execution envelope omits or malforms a required identity field
- **THEN** the resolver returns `FAIL_CLOSED_REPAIR`
- **AND** malformed technical input does not fabricate missing human authority

### Requirement: Minimal guards remain bounded
DevFlow SHALL use `CONTINUE_WITH_MINIMAL_GUARD` only for one bounded RED/GREEN guard required to keep the approved Completion Contract safe.

#### Scenario: Bounded guard is eligible
- **WHEN** a discovered issue blocks safe completion, can be corrected locally within the approved behavior and write set, and requires no material authority delta
- **THEN** the resolver returns `CONTINUE_WITH_MINIMAL_GUARD`
- **AND** execution returns to the critical path after focused validation

#### Scenario: Guard would expand authority
- **WHEN** the proposed guard requires an undeclared dependency, target, public contract, irreversible effect, or write-set expansion
- **THEN** the resolver MUST NOT return `CONTINUE_WITH_MINIMAL_GUARD`
- **AND** it returns `AWAIT_HUMAN` with the concrete missing authority

### Requirement: Exact task-owned cleanup uses the generated-artifact contract
DevFlow SHALL route disposable output cleanup through the sealed Generated Artifact Lifecycle and SHALL NOT treat every deletion as a Human Gate.

#### Scenario: Exact task-owned output auto-cleans
- **WHEN** output was registered before creation, every candidate is proven task-owned, the owner has exited, paths are exact and non-recursive, identities are current, and no candidate is source, user content, historical receipt, or persistent evidence
- **THEN** the resolver returns `AUTO_CLEAN`
- **AND** cleanup requires the existing receipt-bound exact apply and terminal verification

#### Scenario: Owner remains active
- **WHEN** the owner process or lease remains active
- **THEN** the resolver returns `WAIT_OWNER`
- **AND** it does not create a Human Gate or delete the output

#### Scenario: Cleanup ownership is ambiguous
- **WHEN** registration, membership, ownership, identity, path scope, or retention evidence is ambiguous or drifted
- **THEN** automatic cleanup fails closed
- **AND** DevFlow preserves the candidate and requests human authority only when ownership or retention cannot be resolved inside the approved contract

### Requirement: Human Gate state is atomic and deduplicated
DevFlow SHALL persist a genuine Human Gate only through one gate-recording seam that keeps `current_stage` and `current_change.status` consistent and binds the concrete missing authority.

#### Scenario: Gate is recorded atomically
- **WHEN** a current authority resolution is `AWAIT_HUMAN` with non-empty missing authority
- **THEN** the recorder writes both state fields as `awaiting_human`
- **AND** records the gate key, missing authority, evidence identity, and one next question

#### Scenario: Gate recording recovers from an interrupted atomic boundary
- **WHEN** execution stops after a durable same-identity gate intent is written but before both STATE markers are activated
- **THEN** retry verifies the exact pre-gate STATE digest, Goal/change, resolution, gate key, and intended final receipt before activating the gate once
- **AND** drift, a different gate, an ambiguous receipt, or an already-consumed intent fails closed without overwriting STATE or fabricating a second gate

#### Scenario: Invalid gate request is rejected
- **WHEN** a caller asks to write `awaiting_human` without a current `AWAIT_HUMAN` resolution or concrete missing authority
- **THEN** the recorder rejects the write
- **AND** leaves both state fields unchanged

#### Scenario: Identical gate is not reopened
- **WHEN** the same unresolved gate key is evaluated again by an item boundary, Stop hook, doctor, review, commit, push, release, or refresh stage
- **THEN** DevFlow reuses the existing gate receipt
- **AND** does not ask another question or create another state transition

#### Scenario: Granted authority invalidates the old gate
- **WHEN** the missing authority is promoted into the active Goal, OpenSpec change, or Execution Ledger
- **THEN** DevFlow clears both awaiting markers through the same controlled seam
- **AND** a fresh resolution determines the next action

### Requirement: Hooks and diagnostics are read-only authority consumers
Stop hooks, doctors, validators, and read-only diagnostics SHALL consume authority resolutions but SHALL NOT synthesize authority, persist Human Gates, or perform external effects.

#### Scenario: Stop observes remaining approved work
- **WHEN** an approved in-scope action remains and no concrete missing authority exists
- **THEN** the Stop result reports the automatic continuation or repair action
- **AND** it does not label the condition `AWAIT_HUMAN`

#### Scenario: Doctor observes a real gate
- **WHEN** both awaiting markers and a current gate receipt agree
- **THEN** the doctor reports the concrete missing authority
- **AND** it makes no workflow-state write

### Requirement: Long-running execution has no false Human Gates
DevFlow SHALL prove the resolver and orchestrator through a dependency-ordered simulation of more than ten steps.

#### Scenario: Approved long run reaches its milestone
- **WHEN** a simulation includes ordinary slices, one minimal guard, derived evidence refresh, owner wait, exact `AUTO_CLEAN`, verification, review, milestone commit, push, publication, and named refresh under one current standing contract
- **THEN** it completes in dependency order with zero false `AWAIT_HUMAN` decisions
- **AND** every injected ambiguity, identity drift, invalid authority, or undeclared target case fails closed before mutation
