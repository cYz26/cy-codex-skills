# current-system Specification

## MODIFIED Requirements
### Requirement: Brownfield current-system baseline exists

The repository SHALL maintain a valid current-system OpenSpec baseline for repository-wide behavior, including repository-local skill deprecation status.

#### Scenario: Current-system spec is validated
- **WHEN** OpenSpec validates repository specs
- **THEN** the current-system spec includes a purpose
- **AND** it includes at least one requirements section

#### Scenario: Agent Reach is not recommended
- **WHEN** repository skill inventory is inspected
- **THEN** Agent Reach is treated as deprecated compatibility content
- **AND** it is not recommended for new use.
