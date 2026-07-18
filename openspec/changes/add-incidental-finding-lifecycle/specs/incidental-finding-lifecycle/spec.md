## ADDED Requirements

### Requirement: Exhaustive Incidental Finding Classification

DevFlow SHALL classify every out-of-scope finding discovered during approved
work as exactly one of `CONTINUE_WITH_MINIMAL_GUARD`, `DEFER_AND_CONTINUE`, or
`BLOCKED_AWAITING_HUMAN` before expanding production work.

#### Scenario: Safe bounded guard protects completion

- **WHEN** a finding blocks safe completion and one bounded RED/GREEN cycle can resolve it within the approved behavior and write set
- **THEN** DevFlow classifies it as `CONTINUE_WITH_MINIMAL_GUARD`
- **AND** execution returns to the active critical path after the guard passes focused validation

#### Scenario: Non-blocking improvement is deferred

- **WHEN** a finding does not block the active Completion Contract and current mitigation leaves the critical path safe
- **THEN** DevFlow classifies it as `DEFER_AND_CONTINUE`
- **AND** production implementation for the optional follow-up does not begin in the active task

#### Scenario: Required behavior cannot be deferred

- **WHEN** a finding demonstrates that required Completion Contract behavior is missing or unsafe
- **THEN** DevFlow MUST NOT classify that behavior as `DEFER_AND_CONTINUE`
- **AND** it either completes a bounded approved guard or stops for human resolution

#### Scenario: Ambiguous classification fails closed

- **WHEN** available evidence cannot establish whether continuing is safe or authorized
- **THEN** DevFlow classifies the finding as `BLOCKED_AWAITING_HUMAN`

### Requirement: Critical Path and Escalation Budget

DevFlow SHALL require a non-trivial plan to identify its Critical Path,
Incidental Finding Budget, and structural Escalation Triggers.

#### Scenario: Plan defines the incidental budget

- **WHEN** DevFlow writes a non-trivial technical plan
- **THEN** the plan names the active Critical Path
- **AND** defines the bounded guard allowed without scope expansion
- **AND** lists structural triggers that require reclassification or plan approval

#### Scenario: Finding crosses an escalation trigger

- **WHEN** a finding requires a new dependency, schema, public contract, standards-conformance effort, architecture component, migration, external effect, destructive action, or expanded write set
- **THEN** DevFlow stops production expansion for that finding
- **AND** updates the canonical plan and approval boundary or records `BLOCKED_AWAITING_HUMAN`

### Requirement: Durable Finding Register

DevFlow SHALL record every deferred or blocked finding in the tracked
`TASK_LEDGER.md` Incidental Finding Register without granting it execution
authority.

#### Scenario: Finding is recorded durably

- **WHEN** a finding is classified as `DEFER_AND_CONTINUE` or `BLOCKED_AWAITING_HUMAN`
- **THEN** the register records a stable ID, summary, disposition, severity, evidence, affected contract, impact, mitigation, disposition reason, recommended follow-up, trigger, and human disposition
- **AND** `.planning` state or chat is not the only record

#### Scenario: Existing project has no register

- **WHEN** an established project first needs to record an incidental finding
- **THEN** DevFlow adds the register section non-destructively
- **AND** it does not overwrite existing ledger content or require a broad project migration

#### Scenario: Follow-up is accepted

- **WHEN** a human accepts a recommended follow-up
- **THEN** the register records the human disposition
- **AND** the follow-up becomes executable only after normal intake and the required OpenSpec or ledger approval

### Requirement: Severe Finding Human Stop

DevFlow MUST stop as `BLOCKED_AWAITING_HUMAN` when a finding creates severe
risk or requires material authority that the active contract does not grant.

#### Scenario: Severe safety or authority risk is discovered

- **WHEN** evidence indicates possible data loss, corruption, security or authority bypass, irreversible effects, destructive work, or ambiguous ownership
- **THEN** DevFlow stops before speculative mutation
- **AND** it may complete only safe read-only diagnosis

#### Scenario: Product or execution authority must expand

- **WHEN** continuing would change public behavior, the Completion Contract, a production dependency, schema, migration, external effect, or unresolved product tradeoff
- **THEN** DevFlow records `BLOCKED_AWAITING_HUMAN`
- **AND** requests one concrete human decision with evidence, impact, safe options, and a recommendation

#### Scenario: Human resolves a blocker

- **WHEN** the human supplies the required decision
- **THEN** DevFlow promotes the decision into OpenSpec or the active ledger before resuming production work

### Requirement: Completion Follow-up Confirmation

DevFlow SHALL disclose all residual findings in the current completion claim
and request human confirmation before starting any recommended follow-up.

#### Scenario: Current task completes with deferred findings

- **WHEN** all active Completion Contract requirements pass and only non-blocking `DEFER_AND_CONTINUE` findings remain
- **THEN** the completion claim lists each finding, its mitigation, why it does not block completion, and the recommended order
- **AND** asks the human to accept, reject, or defer the proposed follow-up

#### Scenario: Follow-up confirmation is pending

- **WHEN** the human has not yet answered the follow-up question
- **THEN** the current completion claim may remain valid if the finding is proven non-blocking
- **AND** DevFlow MUST NOT start the follow-up change

#### Scenario: Severe finding remains unresolved

- **WHEN** any `BLOCKED_AWAITING_HUMAN` finding remains open
- **THEN** DevFlow MUST NOT claim completion, verification readiness, archive readiness, or authorization to continue

### Requirement: Lifecycle Is Packaged Across Workflow Surfaces

DevFlow SHALL package the same lifecycle in intake, planning, execution,
completion, orchestration, and generated project control-plane guidance.

#### Scenario: Source plugin guidance is inspected

- **WHEN** DevFlow source skills and templates are inspected
- **THEN** they use the three normative dispositions consistently
- **AND** planning, persistence, stop, resume, completion, and follow-up-confirmation responsibilities are present

#### Scenario: No parallel state system is introduced

- **WHEN** the lifecycle is implemented
- **THEN** OpenSpec remains canonical for behavior and active tasks
- **AND** `TASK_LEDGER.md` remains the tracked cross-change register
- **AND** no new hook, dependency, schema, background process, or automatic canonical writer is required
