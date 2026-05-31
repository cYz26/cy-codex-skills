## ADDED Requirements

### Requirement: Low-frequency skills are explicit-only

The DevFlow plugin SHALL mark low-frequency workflow skills as explicit-only for OpenAI invocation policy.

#### Scenario: Explicit-only policy is packaged

- **WHEN** the release plugin skill tree is inspected
- **THEN** `ai-native-tech-plan`, `checkpoint-compact`, `claude-code-delegate`, `context-health-check`, `context-tool-audit`, `execute-task`, `project-setup`, `verify-and-archive`, and `workflow-doctor` each include `agents/openai.yaml`
- **AND** each policy file sets `allow_implicit_invocation` to false.

### Requirement: Core routing skills stay implicit

The DevFlow plugin SHALL keep core routing skills implicitly invokable.

#### Scenario: Routing skills are not explicit-only

- **WHEN** the release plugin skill tree is inspected
- **THEN** `project-orchestrator`, `feature-intake`, `change-plan`, and `capability-research` do not include an explicit-only OpenAI invocation policy.

### Requirement: Plugin Eval readability warning is removed where scoped

The DevFlow plugin SHALL remove Python long lines in the scoped release and development plugin files.

#### Scenario: Python long lines are checked

- **WHEN** Python files under the release plugin are scanned
- **THEN** no Python line exceeds 120 characters.

### Requirement: Plugin Eval optimization is measured

The DevFlow plugin SHALL record before and after Plugin Eval evidence for this optimization.

#### Scenario: Plugin Eval is rerun

- **WHEN** the optimization is complete
- **THEN** Plugin Eval is run against `plugins/dev-flow`
- **AND** the result is compared to the recorded baseline for trigger, invoke, deferred, score, and remaining findings.
