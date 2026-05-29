## ADDED Requirements

### Requirement: Complete Workflow Documentation
Context Fixer SHALL document the complete product workflow in README and the
bundled skill guide.

#### Scenario: Skill documentation exposes official workflow
- **WHEN** a user opens `skills/context-fixer/SKILL.md`
- **THEN** it includes managed collection, audit, report, trace import, hook
  collector, history, Web dashboard, recommendation, remediation, and doctor
  usage

#### Scenario: README documents external tool orchestration
- **WHEN** a user reads README
- **THEN** it explains that official flows use `context-fixer collect` profiles
  to manage external tools and that manual imports are advanced/debug paths

#### Scenario: README documents Web dashboard
- **WHEN** a user reads README
- **THEN** it includes `dashboard serve`, `dashboard data`, and
  `dashboard export` examples

#### Scenario: README documents remediation safety
- **WHEN** a user reads README
- **THEN** it explains dry-run planning, explicit apply, backups, and the no
  silent mutation policy

#### Scenario: Docs stay sanitized
- **WHEN** docs describe trace, hook, history, dashboard, or remediation flows
- **THEN** they state that raw prompt, message, argument, output, file, and trace
  bodies are omitted from reports and persisted snapshots
