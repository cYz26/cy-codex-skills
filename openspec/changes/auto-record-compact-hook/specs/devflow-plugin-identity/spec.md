## MODIFIED Requirements

### Requirement: Hook configuration compatibility

Hook configuration SHALL prefer `.dev-flow.json`, SHALL read `.codex-project-orchestrator.json` as a legacy fallback when the new file is absent, and SHALL package DevFlow hook entries needed for manual `PostCompact` checkpoint recovery.

#### Scenario: New hook config overrides legacy config
- **WHEN** both `.dev-flow.json` and `.codex-project-orchestrator.json` exist in a target repo
- **THEN** hook policy reads `.dev-flow.json`

#### Scenario: Legacy hook config still works
- **WHEN** only `.codex-project-orchestrator.json` exists in a target repo
- **THEN** hook policy reads the legacy file

#### Scenario: Manual PostCompact recovery hook is packaged
- **WHEN** the development or release `hooks.json` is inspected
- **THEN** it includes a `PostCompact` compact recovery command
- **AND** that hook group matches manual compaction only
