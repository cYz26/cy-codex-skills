## ADDED Requirements

### Requirement: Chronological Context Timeline
Context Fixer SHALL include a sanitized chronological timeline that combines session telemetry and supplied request trace evidence.

#### Scenario: Report peak and latest valid usage
- **WHEN** analyzed sessions contain multiple token events
- **THEN** the system reports both the peak usage event and the latest valid non-zero usage event

#### Scenario: Preserve historical compaction attribution
- **WHEN** analyzed sessions contain context compaction events
- **THEN** the system reports those compactions as historical timeline events rather than attributing them only to the latest run

#### Scenario: Detect misleading latest snapshots
- **WHEN** the latest discovered session has zero token usage or appears incomplete
- **THEN** the system reports a timeline anomaly and keeps the latest valid usage event separate from the raw latest session state

#### Scenario: Include request trace chronology
- **WHEN** the user supplies one or more request trace files
- **THEN** the system includes sanitized request events in the timeline with method, path, model, status, latency, and exact usage availability where present

#### Scenario: Render sanitized timeline output
- **WHEN** the user renders text, JSON, or HTML output
- **THEN** the system includes timeline summaries without printing prompt bodies, chat contents, tool argument bodies, tool output bodies, or authorization headers
