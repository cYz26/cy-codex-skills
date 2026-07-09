# Specification Delta: DevFlow Compact Gate

## ADDED Requirements

### Requirement: Pending compact is advisory for Stop hooks

DevFlow SHALL NOT stop otherwise-continuable work solely because
`compact_status` is `pending`.

#### Scenario: Pending compact exists at Stop

- **GIVEN** `.planning/STATE.md` contains `compact_status: pending`
- **AND** the checkpoint state is otherwise valid
- **WHEN** DevFlow Stop checks run
- **THEN** the checkpoint check is considered acceptable
- **AND** the result describes pending compact as an advisory compact
  recommendation.

#### Scenario: Direct checkpoint Stop policy sees pending compact

- **GIVEN** `.planning/STATE.md` contains `compact_status: pending`
- **WHEN** `stop_checkpoint_policy.py` runs for a Stop event
- **THEN** it exits successfully
- **AND** it does not instruct the agent to stop and wait for manual
  `/compact` before continuing.

### Requirement: Broken compact states still block

DevFlow SHALL continue to require action when compact state indicates an
invalid, failed, blocked, or missing checkpoint contract.

#### Scenario: Compact failed or blocked

- **GIVEN** `.planning/STATE.md` contains `compact_status: failed` or
  `compact_status: blocked`
- **WHEN** DevFlow Stop checks run
- **THEN** the checkpoint check is not acceptable
- **AND** the result tells the agent the checkpoint or compact gate requires
  action.

#### Scenario: Unsupported compact status is present

- **GIVEN** `.planning/STATE.md` contains an unsupported compact status
- **WHEN** direct checkpoint Stop policy runs
- **THEN** it reports unsupported compact status
- **AND** exits with a Stop-hook response requiring repair.
