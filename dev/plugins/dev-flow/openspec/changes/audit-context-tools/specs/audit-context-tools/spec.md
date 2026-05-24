# Specification Delta: Audit context tools

## ADDED Requirements

### Requirement: Context tool audit report

The system SHALL generate an analysis report that inventories globally active Codex plugins, global skills, project-local skills, installed plugin-cache skills, detected project signals, optional source catalog matches, findings, recommendations, and executable action proposals.

#### Scenario: Reporting unrelated global tools

- GIVEN a Codex home with globally enabled plugins and global skills
- AND a target repo with project-local skills
- WHEN the user runs the context tool audit
- THEN the report includes the global inventory
- AND marks unrelated global tools as cleanup candidates
- AND includes recommendation records with stable action ids when a safe action exists

#### Scenario: Reporting project-relevant installed tools

- GIVEN a target repo with detectable framework or language signals
- AND installed plugin-cache skills that match those signals
- WHEN the user runs the context tool audit
- THEN the report recommends project-local installation actions for matching installed skills that are not already active in the project

### Requirement: Authorized action application

The system SHALL apply cleanup or installation actions only from a saved audit report and only after explicit user authorization.

#### Scenario: Dry-run is the default

- GIVEN an audit report with cleanup and installation actions
- WHEN the user runs the apply script without `--apply`
- THEN the script reports the selected actions
- AND does not change global config or project files

#### Scenario: Explicit apply creates backups and performs selected actions

- GIVEN an audit report with a `disable_global_plugin` action
- AND the user selects that action id with `--apply`
- WHEN the apply script runs
- THEN it creates a timestamped backup of `config.toml`
- AND updates only the selected plugin section to disabled

### Requirement: Safe first-version boundaries

The system SHALL avoid destructive cleanup and unsupported network behavior in the first version.

#### Scenario: Cleanup avoids deletion

- GIVEN a cleanup recommendation for global context pressure
- WHEN actions are generated
- THEN no action deletes plugin cache entries or global skill files

#### Scenario: Remote discovery is explicit

- GIVEN no source URL or source catalog path
- WHEN the audit runs
- THEN it uses local Codex home, repo, and cache data only
