## ADDED Requirements

### Requirement: Codex Update Skill Entry
DevFlow SHALL provide a skill that activates when a user asks to check or update
Codex-referenced plugins, skills, plugin caches, marketplaces, or known external
toolchains.

#### Scenario: User asks for a check
- **WHEN** a user asks to check Codex plugin or skill updates
- **THEN** the skill directs the agent to run the canonical updater in dry-run
  JSON mode

#### Scenario: User asks for an update
- **WHEN** a user asks to update Codex plugin or skill references
- **THEN** the skill directs the agent to run dry-run first and only run apply
  mode when the latest user request explicitly asked for updates or confirms
  after seeing the dry-run report

### Requirement: Update Skill Reporting
The skill SHALL require the agent to summarize updater results by actionable
status and include plugin install refresh and cache verification findings.

#### Scenario: Dry-run report contains cache verification
- **WHEN** the updater emits plugin install or plugin cache verification results
- **THEN** the skill requires the agent to surface `plugin-install`,
  `plugin-cache-verify`, skipped items, failed items, and manual actions

### Requirement: Deprecated Tool Exclusion
The skill SHALL exclude Agent Reach from Codex update checks and updates.

#### Scenario: Agent Reach is present locally
- **WHEN** Agent Reach exists in the local environment
- **THEN** the skill still instructs the agent not to check, update, or run Agent
  Reach as part of the Codex updater workflow
