## ADDED Requirements

### Requirement: Plugin Eval Gate For Skill Changes
The workflow SHALL run Plugin Eval when creating or updating a Codex skill.

#### Scenario: Skill is created
- **WHEN** a change creates a `SKILL.md` file or a skill directory
- **THEN** verification evidence includes Plugin Eval analysis for that skill

#### Scenario: Skill is updated
- **WHEN** a change updates an existing skill's trigger, instructions, support
  files, or packaging metadata
- **THEN** verification evidence includes Plugin Eval analysis for the changed
  skill

### Requirement: Plugin Eval Gate For Plugin Changes
The workflow SHALL run Plugin Eval when creating or updating a Codex plugin.

#### Scenario: Plugin bundle changes
- **WHEN** a change updates plugin manifest, skills, scripts, assets, hooks, or
  packaging behavior
- **THEN** verification evidence includes Plugin Eval analysis for the changed
  plugin bundle or the smallest relevant changed plugin path

### Requirement: Plugin Eval Optimization Evidence
The workflow SHALL record optimization decisions from Plugin Eval findings.

#### Scenario: Plugin Eval reports findings
- **WHEN** Plugin Eval reports failures, warnings, or fix-first recommendations
- **THEN** the change either addresses them or records why they are deferred

#### Scenario: Plugin Eval reports no urgent fixes
- **WHEN** Plugin Eval reports a clean or low-risk score
- **THEN** verification evidence still records the score, key informational
  findings, and whether any optimization was applied
