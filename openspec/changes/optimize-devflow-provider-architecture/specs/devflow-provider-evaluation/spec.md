## ADDED Requirements

### Requirement: Provider comparison uses controlled outcome scenarios
DevFlow SHALL provide a reproducible benchmark corpus that compares provider
outcomes using isolated, pinned, equivalent fixtures rather than static skill
size alone.

#### Scenario: Strict and lean profiles are compared
- **WHEN** the provider benchmark is authorized and executed
- **THEN** separate strict and lean benchmark configs use the same Codex binary, model, base repository hash, neutral prompt, sandbox, approval policy, verifier, and resource limit
- **AND** the result records DevFlow commit, provider ref, skill hashes, prompt hash, route evidence, tokens, tool calls, elapsed time, diffs, and verifier output

#### Scenario: Provider fixtures are compared for parity
- **WHEN** benchmark configs or fixtures are validated
- **THEN** initial workspace hashes match after excluding the allowlisted provider config, provider skills, and provider lock paths
- **AND** any other fixture difference fails benchmark readiness

#### Scenario: Provider is installed but not routed
- **WHEN** a run lacks evidence that the selected provider capability was actually invoked
- **THEN** the run is invalid for provider comparison
- **AND** it is excluded from default-switch evidence

### Requirement: Benchmark coverage represents DevFlow risk classes
The benchmark corpus SHALL use fixed task IDs for ambiguous decisions,
compatibility planning, known-failing bugs, risky characterization refactors,
external research, delegation plans, premature-completion pressure, code
review, context recovery, and authorization boundaries.

#### Scenario: Benchmark corpus is validated
- **WHEN** benchmark configuration is checked
- **THEN** all ten required task classes have machine-verifiable outcomes and canonical artifact checks
- **AND** each profile has at least three valid runs per task class before a default decision

### Requirement: Lean default requires quality non-inferiority and useful savings
DevFlow SHALL keep `lean-matt` opt-in unless quality, authorization, canonical
compliance, telemetry, and efficiency thresholds all pass.

#### Scenario: Lean satisfies the default-switch gate
- **WHEN** lean has zero unauthorized effects or canonical corruption, all high-risk classes pass three of three, at least 29 of 30 machine verifiers pass, canonical compliance is 100%, and telemetry coverage is at least 90%
- **AND** lean is no more than one failure worse than strict, paired median observed total tokens improve at least 20%, at least seven task classes improve on paired median total tokens, no class token median degrades more than 15%, aggregate tool calls and elapsed time each degrade no more than 10%, blind quality is within 0.25 of 5, and human corrections are no more than one higher
- **THEN** a separate approved change may propose lean as the new default

#### Scenario: Quality or efficiency gate fails
- **WHEN** any default-switch threshold is not met or required telemetry is missing
- **THEN** `lean-matt` remains opt-in
- **AND** DevFlow does not claim equivalent outcomes or a successful default transition

### Requirement: Evaluation evidence is release- and source-reproducible
DevFlow SHALL store benchmark configuration, rubric, machine results, and human
review evidence so the comparison can be repeated against a later release.

#### Scenario: Benchmark results are recorded
- **WHEN** an authorized benchmark completes
- **THEN** a tracked result manifest records aggregate metrics, provider hashes, invalid runs, reviewer decisions, and SHA-256 references to raw usage/verifier evidence
- **AND** raw evidence remains available at the immutable recorded location until the default decision is archived

#### Scenario: Raw benchmark evidence is unavailable
- **WHEN** a result manifest references raw evidence that cannot be accessed or hash-verified
- **THEN** the default-switch gate fails
- **AND** aggregate claims cannot substitute for the missing evidence

### Requirement: Architecture and default switching have separate release gates
DevFlow SHALL allow the provider seam, optional GSD routing, and opt-in adapters
to ship after structural verification without treating an unrun outcome
benchmark as approval to change the default.

#### Scenario: Provider architecture passes structural release checks
- **WHEN** profile, migration, state ownership, release, runtime, and Plugin Eval gates pass
- **AND** lean default-switch evidence is absent
- **THEN** the architecture may ship with `core + none` as the new-project default and lean as opt-in
- **AND** no benchmark equivalence claim is made
