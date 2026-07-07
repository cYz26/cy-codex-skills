# devflow-refresh-skill Specification

## ADDED Requirements

### Requirement: Refresh includes AGENTS drift review

DevFlow refresh SHALL evaluate active project `AGENTS.md` guidance against the
current DevFlow core workflow and AGENTS template during project refresh.

#### Scenario: Project AGENTS guidance may be stale

- **WHEN** `dev-flow-refresh` runs project-local diagnostics after a DevFlow
  upgrade
- **THEN** the workflow requires checking scaffold dry-run output and active
  `AGENTS.md` for durable workflow guidance changes
- **AND** the final report includes an AGENTS status of `unchanged`, `merged`,
  `generated-deferred`, or `conflict`
- **AND** active `AGENTS.md` is not overwritten automatically

### Requirement: Workflow validation detects missing durable AGENTS guidance

DevFlow validation SHALL report missing durable AGENTS sections that indicate a
project has not inherited current DevFlow workflow guidance.

#### Scenario: Active AGENTS lacks current durable sections

- **WHEN** workflow validation inspects an active `AGENTS.md`
- **AND** the file lacks one or more durable sections from the current DevFlow
  AGENTS template
- **THEN** validation reports the missing guidance markers
- **AND** validation preserves the existing generated-candidate merge gate when
  `AGENTS.md.generated` is present
