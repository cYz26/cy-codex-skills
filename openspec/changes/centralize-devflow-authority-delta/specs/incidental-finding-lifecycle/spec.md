## MODIFIED Requirements

### Requirement: Critical Path and Escalation Budget
DevFlow SHALL require a non-trivial plan to identify its Critical Path,
Incidental Finding Budget, structural Escalation Triggers, and the authority
contract used to distinguish technical repair from a material authority delta.

#### Scenario: Plan defines the incidental budget

- **WHEN** DevFlow writes a non-trivial technical plan
- **THEN** the plan names the active Critical Path
- **AND** defines the bounded guard allowed without scope expansion
- **AND** lists structural triggers that require authority-delta resolution or plan amendment

#### Scenario: Finding crosses an escalation trigger without new authority

- **WHEN** a finding is local, reversible, semantics-preserving, deterministically verifiable, and already covered by the approved behavior and write set
- **THEN** DevFlow routes it through normal continuation or `CONTINUE_WITH_MINIMAL_GUARD`
- **AND** the trigger label alone does not create a Human Gate

#### Scenario: Non-blocking related improvement is deferred without leaving the task

- **WHEN** an optimization discovered during execution is related but does not block the Completion Contract and a safe bounded workaround or current behavior preserves the critical path
- **THEN** DevFlow records `DEFER_AND_CONTINUE`, continues the active task, and summarizes the finding at completion
- **AND** it does not start the follow-up work or ask for an intermediate Human Gate

#### Scenario: Finding creates a material authority delta

- **WHEN** a finding requires an undeclared dependency, schema, public contract, architecture component, migration, external target, destructive action, material risk, or expanded write set
- **THEN** DevFlow stops production expansion for that finding
- **AND** updates the canonical plan and approval boundary or records `BLOCKED_AWAITING_HUMAN` with concrete missing authority

### Requirement: Severe Finding Human Stop
DevFlow MUST stop as `BLOCKED_AWAITING_HUMAN` when a finding creates severe
risk or requires material authority that the active contracts do not grant;
technical failure or a phase boundary alone MUST NOT create that state.

#### Scenario: Severe safety or authority risk is discovered

- **WHEN** evidence indicates possible data loss, corruption, security or authority bypass, irreversible effects, undeclared destructive work, or ambiguous ownership
- **THEN** DevFlow stops before speculative mutation
- **AND** it may complete only safe read-only diagnosis

#### Scenario: Product or execution authority must expand

- **WHEN** continuing would change public behavior, the Completion Contract, a production dependency, schema, migration, undeclared external effect, material risk, or unresolved product tradeoff
- **THEN** DevFlow records `BLOCKED_AWAITING_HUMAN`
- **AND** requests one concrete human decision with evidence, impact, safe options, a recommendation, and the missing authority

#### Scenario: Preauthorized milestone effect remains executable

- **WHEN** an external effect is already bound by a current Milestone External Effects Contract and every evidence and identity precondition passes
- **THEN** DevFlow does not reclassify the effect as `BLOCKED_AWAITING_HUMAN`
- **AND** the same standing authority covers its declared downstream commit, push, publication, and named refresh steps

#### Scenario: Human resolves a blocker

- **WHEN** the human supplies the required decision
- **THEN** DevFlow promotes the decision into OpenSpec or the active ledger before resuming production work

### Requirement: Lifecycle Is Packaged Across Workflow Surfaces
DevFlow SHALL package the same lifecycle and authority-delta model in intake,
planning, execution, completion, orchestration, release, refresh, and generated
project control-plane guidance.

#### Scenario: Source plugin guidance is inspected

- **WHEN** DevFlow source skills and templates are inspected
- **THEN** they use the normative dispositions and authority-delta vocabulary consistently
- **AND** planning, persistence, stop, resume, cleanup, completion, publication, refresh, and follow-up responsibilities are present

#### Scenario: No parallel planning or background state system is introduced

- **WHEN** the lifecycle is implemented
- **THEN** OpenSpec remains canonical for behavior and active tasks
- **AND** `TASK_LEDGER.md` remains the tracked cross-change register
- **AND** milestone contracts and receipts remain namespaced DevFlow execution evidence rather than a second task queue
- **AND** no new dependency, mutating hook, or background process is required
