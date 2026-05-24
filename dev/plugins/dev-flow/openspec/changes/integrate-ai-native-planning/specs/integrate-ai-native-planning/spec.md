# Specification Delta: Integrate AI-native planning

<!-- ai-native-plan-lint: allow-human-planning-terms -->

## ADDED Requirements

### Requirement: AI-native planning skill

The plugin SHALL provide an `ai-native-tech-plan` skill that triggers for technical plans, implementation plans, architecture plans, Codex execution plans, workflow plans, and requests to avoid partial MVP-style delivery.

#### Scenario: Generate a technical plan

- GIVEN a user asks for a technical or implementation plan
- WHEN the orchestrator routes the request
- THEN Codex can use `ai-native-tech-plan` to produce Target State, Completion Contract, Capability Slices, Execution Ledger, Acceptance Criteria, Validation Commands, Goal Mode prompt, Continue prompt, and Review Checklist sections
- AND the plan defaults to complete target-state delivery unless the user explicitly requests a prototype, demo, POC, or partial target

### Requirement: AI-native scaffold defaults

Generated workflow files SHALL use AI-native planning language by default and SHALL NOT instruct new projects to establish MVP scope unless the user explicitly asked for MVP-oriented work.

#### Scenario: Scaffold a greenfield project

- GIVEN a new greenfield repository
- WHEN `scaffold_workflow.py --repo <repo> --json` runs
- THEN generated `AGENTS.md` contains AI Coding Planning Rules
- AND the active setup change uses an AI-native baseline id
- AND generated roadmap and phase plan text treats GSD phases as governance/workflow containers rather than technical completion boundaries

### Requirement: Execution ledger discipline

Execution-oriented skills SHALL require Codex to read and maintain durable execution ledgers for medium or large tasks.

#### Scenario: Resume after interruption

- GIVEN a task ledger exists in the repository
- WHEN execution resumes after interruption, compaction, or a new session
- THEN Codex reads the Target State, Completion Contract, Capability Slices, and current statuses before editing code
- AND Codex continues from the next unfinished slice
- AND Codex updates slice status only after the associated validation command succeeds or a blocker is recorded

### Requirement: Plan linting

The plugin SHALL include a lint script that detects human-style planning terms and missing AI-native plan sections in generated plans.

#### Scenario: Lint rejects a human-style plan

- GIVEN a plan file without the lint allow marker
- AND the plan contains a forbidden planning term or lacks required AI-native headings
- WHEN `lint_ai_plan.py <plan.md>` runs
- THEN the command exits non-zero and reports actionable line-level findings where applicable

#### Scenario: Lint permits policy documents

- GIVEN a document contains `ai-native-plan-lint: allow-human-planning-terms`
- WHEN `lint_ai_plan.py <document.md>` runs
- THEN forbidden planning term checks are skipped
- AND required-heading checks still run unless explicitly disabled by command-line options

### Requirement: Existing discipline integration

The plugin SHALL integrate AI-native planning with existing Superpowers, GSD, and OpenSpec routes rather than replacing them.

#### Scenario: Behavior change requires OpenSpec

- GIVEN a user asks for user-visible behavior, API, data, permission, persistence, integration, migration, error handling, or compatibility changes
- WHEN the orchestrator routes the request
- THEN OpenSpec proposal/design/spec/tasks remain required before implementation
- AND the resulting tasks include AI-native completion contracts, capability slices, and validation evidence expectations

#### Scenario: Implementation starts

- GIVEN approved OpenSpec tasks and an execution ledger
- WHEN Codex starts implementation
- THEN execution skills require Superpowers TDD where applicable
- AND final completion requires Superpowers verification-before-completion plus the AI-native Completion Contract and ledger status checks
