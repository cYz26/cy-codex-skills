# devflow-updater-policy Specification

## MODIFIED Requirements
### Requirement: Deprecated external tools are excluded from update planning

DevFlow update tooling SHALL exclude deprecated external tools from both dry-run update plans and apply-mode external updater execution, even after updater reliability improvements add more refresh targets.

#### Scenario: Agent Reach is not planned for update
- **WHEN** `codex_auto_update_plugins_skills.py` evaluates external updaters
- **AND** an `agent-reach` executable is available
- **THEN** the result set does not include an `agent-reach` update item
- **AND** it does not call `pipx upgrade agent-reach`
- **AND** it does not call `agent-reach check-update`
