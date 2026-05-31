# devflow-updater-policy Specification

## Purpose

Define DevFlow's policy for excluding deprecated external tools from automatic plugin and skill update planning.

## ADDED Requirements
### Requirement: Deprecated external tools are excluded from update planning

DevFlow update tooling SHALL exclude deprecated external tools from both dry-run update plans and apply-mode external updater execution.

#### Scenario: Agent Reach is not planned for update
- **WHEN** `codex_auto_update_plugins_skills.py` evaluates external updaters
- **AND** an `agent-reach` executable is available
- **THEN** the result set does not include an `agent-reach` update item
- **AND** it does not call `pipx upgrade agent-reach`
- **AND** it does not call `agent-reach check-update`

### Requirement: Deprecated tool status is documented

DevFlow documentation SHALL identify tools that remain in the repository only for compatibility but are not recommended for new use.

#### Scenario: Agent Reach is marked not recommended
- **WHEN** repository or DevFlow maintenance documentation is read
- **THEN** Agent Reach is marked deprecated or not recommended
- **AND** it is not listed as a maintained automatic update target.
