## ADDED Requirements

### Requirement: Formal release selection and exact pinning
DevFlow SHALL adopt OpenSpec only from a verified formal release and MUST pin
the exact selected version in dependency provenance, installer, updater,
diagnostics, generated-skill verification, and documentation rather than
resolving a mutable dist-tag at execution time.

#### Scenario: Latest formal release is compatible
- **WHEN** the npm `latest` version is a formal release whose engine, CLI, and generated core skills pass the compatibility gate
- **THEN** DevFlow pins that exact release and records its authoritative package and source evidence

#### Scenario: Registry later advances
- **WHEN** npm `latest` differs from the exact DevFlow pin after the change is complete
- **THEN** updater diagnostics report registry drift without silently changing the installed or required version

### Requirement: OpenSpec 1.7 dependency contract
DevFlow SHALL require OpenSpec CLI `1.7.0` with Node `>=20.19.0` and MUST report
any missing or different CLI version as dependency drift before relying on it
for a Full OpenSpec workflow.

#### Scenario: Supported 1.7 runtime is present
- **WHEN** dependency diagnosis runs with OpenSpec `1.7.0` on a supported Node runtime
- **THEN** the dependency is verified and the exact `@fission-ai/openspec@1.7.0` repair command is retained

#### Scenario: OpenSpec 1.6 remains installed
- **WHEN** dependency diagnosis runs with OpenSpec `1.6.0`
- **THEN** DevFlow reports version drift and recommends only the pinned 1.7.0 repair command

### Requirement: Exact isolated Codex core skill generation
DevFlow SHALL use isolated XDG and Codex homes, disabled telemetry, the Codex
tool, and the core profile to generate exactly `openspec-propose`,
`openspec-explore`, `openspec-apply-change`, `openspec-update-change`,
`openspec-sync-specs`, and `openspec-archive-change`, with every skill
identifying OpenSpec and `generatedBy: "1.7.0"`.

#### Scenario: OpenSpec 1.7 core generation succeeds
- **WHEN** the pinned CLI runs the isolated DevFlow generation command
- **THEN** exactly six skill trees are accepted, no Codex command file is required, and verified copies may be staged for `.agents/skills`

#### Scenario: Generated set or version differs
- **WHEN** a skill is missing, an unexpected core skill appears, a skill tree is untrusted, or metadata names another version
- **THEN** activation fails before modifying any project OpenSpec skill target

### Requirement: Atomic and ownership-safe skill refresh
DevFlow SHALL refresh all six verified OpenSpec-generated project skills as one
transaction and MUST preserve custom, ambiguous, or unverified target content.

#### Scenario: Six 1.6 generated copies are present
- **WHEN** an explicitly authorized project refresh receives a verified 1.7 generated batch
- **THEN** all six OpenSpec-generated targets become verified 1.7 copies with no mixed-version result

#### Scenario: A target is custom or ambiguous
- **WHEN** any OpenSpec-named target lacks trusted OpenSpec-generated provenance
- **THEN** DevFlow leaves it unchanged, rolls back any staged batch mutation, and reports a manual conflict

### Requirement: Canonical ownership under OpenSpec 1.7 guidance
DevFlow SHALL allow the released skills to consume current project context,
artifact rules, and operation guidance while keeping CLI state, explicit user
choices, OpenSpec artifacts, and DevFlow execution/release/archive gates as
the controlling sources of truth.

#### Scenario: Apply instructions include context or operation guidance
- **WHEN** OpenSpec 1.7 returns those optional inputs
- **THEN** the workflow considers applicable guidance without treating it as completion evidence or permission to bypass a blocked state or DevFlow gate

#### Scenario: Archive or sync is requested
- **WHEN** a released skill fetches current archive inputs or spec rules
- **THEN** DevFlow still requires its own verification and explicit archive authorization before moving or finalizing the change

### Requirement: Compatibility and rollout proof
DevFlow SHALL complete source, generated-release, runtime, and release-target
quality verification before applying the named local CLI, project-skill, or
plugin-cache refresh, and MUST verify every applied external state by readback.

#### Scenario: Source compatibility passes
- **WHEN** 1.7 generates the exact six skills and strictly validates the current repository with compatible status and instructions JSON
- **THEN** source implementation and release counterpart generation may proceed

#### Scenario: Release or runtime verification fails
- **WHEN** any focused, broad, packaged, runtime, strict OpenSpec, or Plugin Eval gate fails
- **THEN** local rollout stops and the existing installed CLI/plugin/cache state remains unchanged or is restored to its recorded prestate

#### Scenario: Named local rollout succeeds
- **WHEN** the explicitly authorized OpenSpec and DevFlow refresh completes
- **THEN** version, project skill metadata, plugin cache identity, workflow state, and dependency readiness are read back and recorded without mutating unrelated dependencies or projects
