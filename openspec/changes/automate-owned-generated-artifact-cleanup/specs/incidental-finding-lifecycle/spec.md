## MODIFIED Requirements

### Requirement: Critical Path and Escalation Budget

DevFlow SHALL require a non-trivial plan to identify its Critical Path,
Incidental Finding Budget, structural Escalation Triggers, and any standing
Generated Artifact Contract authority.

#### Scenario: Plan defines the incidental budget

- **WHEN** DevFlow writes a non-trivial technical plan
- **THEN** the plan names the active Critical Path
- **AND** defines the bounded guard allowed without scope expansion
- **AND** lists structural triggers that require reclassification or plan approval
- **AND** records whether generated-artifact automatic cleanup is unused or governed by a referenced pre-creation contract

#### Scenario: Finding crosses an escalation trigger

- **WHEN** a finding requires a new dependency, schema, public contract, standards-conformance effort, architecture component, migration, external effect, destructive action outside a valid Generated Artifact Contract, or expanded write set
- **THEN** DevFlow stops production expansion for that finding
- **AND** updates the canonical plan and approval boundary or records `BLOCKED_AWAITING_HUMAN`

#### Scenario: Registered task-owned artifact is reclaimed

- **WHEN** a valid pre-creation Generated Artifact Contract and fresh read-only plan classify exact task-owned output as `AUTO_CLEAN`
- **THEN** DevFlow treats exact reclamation as an authorized execution-lifecycle operation rather than an incidental destructive finding
- **AND** it still records a cleanup receipt and zero unlisted mutation

### Requirement: Severe Finding Human Stop

DevFlow MUST stop as `BLOCKED_AWAITING_HUMAN` when a finding creates severe
risk or requires material authority that the active contract does not grant.
A Generated Artifact Contract grants authority only for exact task-owned
artifacts that satisfy every current automatic-cleanup invariant.

#### Scenario: Severe safety or authority risk is discovered

- **WHEN** evidence indicates possible data loss, corruption, security or authority bypass, irreversible effects, destructive work outside a valid Generated Artifact Contract, or ambiguous ownership
- **THEN** DevFlow stops before speculative mutation
- **AND** it may complete only safe read-only diagnosis

#### Scenario: Generated artifact ownership is incomplete

- **WHEN** a cleanup candidate is unregistered, existed before registration, is tracked or protected, belongs to another owner, escapes scope, or has identity drift
- **THEN** DevFlow records `BLOCKED_AWAITING_HUMAN`
- **AND** MUST NOT infer authority from filename, extension, ignore status, or apparent disposability

#### Scenario: Product or execution authority must expand

- **WHEN** continuing would change public behavior, the Completion Contract, a production dependency, schema, migration, external effect, or unresolved product tradeoff
- **THEN** DevFlow records `BLOCKED_AWAITING_HUMAN`
- **AND** requests one concrete human decision with evidence, impact, safe options, and a recommendation

#### Scenario: Human resolves a blocker

- **WHEN** the human supplies the required decision
- **THEN** DevFlow promotes the decision into OpenSpec or the active ledger before resuming production work
