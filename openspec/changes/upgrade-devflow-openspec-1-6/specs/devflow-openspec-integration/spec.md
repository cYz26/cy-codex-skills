## ADDED Requirements

### Requirement: Released OpenSpec version contract
DevFlow SHALL pin OpenSpec CLI `1.6.0`, require Node `>=20.19.0`, and report a
missing or different CLI version as dependency drift before relying on OpenSpec
for Full OpenSpec workflows.

#### Scenario: Supported CLI is present
- **WHEN** dependency diagnostics execute with OpenSpec `1.6.0` on a supported Node runtime
- **THEN** the OpenSpec dependency is verified with its pinned install and update commands

#### Scenario: CLI version is stale
- **WHEN** dependency diagnostics execute with OpenSpec `1.5.0`
- **THEN** DevFlow reports required dependency drift and recommends only the pinned `1.6.0` repair command

### Requirement: Isolated official skill generation
DevFlow SHALL generate official OpenSpec Codex skills using an isolated staging
project, isolated XDG configuration, isolated Codex home, disabled telemetry,
and the core profile without reading or modifying the user's real OpenSpec
delivery/profile or global Codex prompts.

#### Scenario: User global delivery is commands-only
- **WHEN** project activation runs while the user's real OpenSpec configuration selects commands-only delivery
- **THEN** six official core skills are still generated for the project and no file under the real `$CODEX_HOME/prompts` is created, changed, or removed

#### Scenario: Activation dry-run
- **WHEN** project activation runs in dry-run mode
- **THEN** it reports isolated generation and project skill targets without invoking OpenSpec or writing staging, project, or global files

### Requirement: Complete verified core workflow set
DevFlow SHALL accept generated OpenSpec skills only when the exact released core
set is present: `openspec-propose`, `openspec-explore`,
`openspec-apply-change`, `openspec-update-change`, `openspec-sync-specs`, and
`openspec-archive-change`; every skill MUST identify OpenSpec and
`generatedBy: "1.6.0"`.

#### Scenario: Complete 1.6 output
- **WHEN** isolated generation returns all six correctly identified skills
- **THEN** DevFlow materializes project-local copies under `.agents/skills`

#### Scenario: Wrong or incomplete output
- **WHEN** any required skill is absent, additional core output is present, or generated metadata names a different version
- **THEN** activation fails before mutating project OpenSpec skill targets and reports the contract mismatch

### Requirement: Safe OpenSpec skill refresh
DevFlow SHALL refresh only OpenSpec-generated project skill copies and MUST
preserve custom or unverified target content.

#### Scenario: Existing generated 1.5 skill
- **WHEN** refresh runs against a project target identified as an OpenSpec-generated `1.5.0` copy
- **THEN** the target is replaced by the verified `1.6.0` generated copy

#### Scenario: Existing custom wrapper
- **WHEN** an OpenSpec-named target lacks verified OpenSpec-generated provenance
- **THEN** DevFlow leaves it unchanged and reports a manual source conflict

### Requirement: OpenSpec 1.6 workflow routing
DevFlow SHALL expose the six released core workflows, route planning-artifact
revision to `openspec-update-change`, and use OpenSpec status/instructions JSON
path context when reconciling artifacts.

#### Scenario: Existing change needs planning revision
- **WHEN** the user asks to revise an existing OpenSpec change without implementing code
- **THEN** DevFlow routes to `openspec-update-change` and keeps implementation delegated to the approved apply path

#### Scenario: CLI returns action context
- **WHEN** status or instructions returns `planningHome`, `changeRoot`, `artifactPaths`, or `actionContext`
- **THEN** DevFlow guidance uses those values rather than inventing an artifact path

### Requirement: Pinned updater and clean failure semantics
DevFlow SHALL use the provenance-pinned OpenSpec `1.6.0` update command and MUST
treat non-zero validation or archive results as failures without bypassing its
own verification and archive authorization gates.

#### Scenario: Apply-mode OpenSpec update
- **WHEN** the authorized external updater upgrades OpenSpec
- **THEN** it executes the pinned `@fission-ai/openspec@1.6.0` command and verifies the installed version

#### Scenario: OpenSpec archive is blocked
- **WHEN** OpenSpec `1.6.0` returns non-zero because validation or spec rebuild blocks archive
- **THEN** DevFlow records failure and leaves the change active
