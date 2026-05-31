# extract-agent-kb-plugin Specification

## Purpose
TBD - created by archiving change extract-agent-kb-plugin. Update Purpose after archive.
## Requirements
### Requirement: Standalone AgentKB plugin

The repository SHALL package AgentKB as an independent plugin named `agent-kb`.

#### Scenario: Release marketplace exposes AgentKB

- GIVEN `.agents/plugins/marketplace.json`
- WHEN the marketplace is inspected
- THEN it contains an `agent-kb` entry
- AND that entry points to `./plugins/agent-kb`
- AND it includes installation and authentication policy metadata.

#### Scenario: Development marketplace exposes AgentKB

- GIVEN `.agents/plugins/marketplace.dev.json`
- WHEN the marketplace is inspected
- THEN it contains an `agent-kb` entry
- AND that entry points to `./dev/plugins/agent-kb`.

#### Scenario: AgentKB plugin manifest is valid

- GIVEN `dev/plugins/agent-kb/.codex-plugin/plugin.json` or `plugins/agent-kb/.codex-plugin/plugin.json`
- WHEN the manifest is inspected
- THEN its `name` is `agent-kb`
- AND its display name is `AgentKB`
- AND it declares supported skills, assets, and interface metadata without unsupported manifest fields
- AND the plugin root includes `hooks.json` for hook behavior.

### Requirement: Markdown-first knowledge base storage

AgentKB SHALL treat Markdown files as the canonical durable knowledge store.

#### Scenario: Scaffold writes canonical Markdown vault

- GIVEN an empty target vault path and project name
- WHEN `kb_scaffold.py --repo <repo> --vault <vault> --project <project> --json` runs from `agent-kb`
- THEN the vault contains inbox, raw, wiki, project, decision, playbook, context-pack, log, Bases/profile, and archive directories
- AND generated formal notes contain YAML frontmatter with note type, project, status, confidence, and agent read/write policy
- AND generated instructions describe Markdown as canonical storage and Obsidian as an editor profile.

#### Scenario: Scaffold writes AgentKB config

- GIVEN an empty target repo
- WHEN scaffold runs
- THEN the repo contains `.agent-kb.json`
- AND the config includes the vault path, project, storage adapter `markdown-filesystem`, and profile `obsidian-compatible-markdown`.

#### Scenario: Scaffold preserves user edits

- GIVEN an existing generated Markdown file that has been edited
- WHEN scaffold runs again without `--force`
- THEN the report lists that file as skipped
- AND the existing file content is unchanged.

### Requirement: AgentKB lint

AgentKB SHALL provide deterministic linting for Markdown knowledge-base health.

#### Scenario: Fresh scaffold is healthy

- GIVEN a vault created by AgentKB scaffold
- WHEN `kb_lint.py --vault <vault> --project <project> --json` runs
- THEN the report has no blocking findings
- AND it includes the inspected project, context-pack path, and finding count.

#### Scenario: Missing frontmatter is reported

- GIVEN a formal wiki note without YAML frontmatter
- WHEN AgentKB lint runs with `--write-report`
- THEN the JSON report includes a finding for missing frontmatter
- AND a Markdown report is written under the project's `proposed-changes/` directory.

### Requirement: AgentKB event capture

AgentKB SHALL capture sanitized event metadata only for repos that opt into a KB vault.

#### Scenario: Hook no-ops without configuration

- GIVEN a repo with no AgentKB configuration
- WHEN `kb_event_hook.py --event user_prompt_submit` receives a hook payload
- THEN it exits successfully
- AND no KB event file is created.

#### Scenario: Hook writes generic sanitized metadata

- GIVEN `.agent-kb.json` points to a KB vault
- WHEN `kb_event_hook.py --event post_tool_use` receives a payload containing prompt text and command output
- THEN it appends one JSONL record under `<vault>/.agent-kb/events/`
- AND the record includes event type, timestamp, tool name, status, cwd, and output size metadata
- AND it does not include raw prompt text, command output body, secrets, or the full tool payload.

#### Scenario: Hook reads legacy Codex Obsidian config

- GIVEN `.codex/obsidian-kb.json` points to a KB vault
- WHEN `kb_event_hook.py --event post_tool_use` receives a hook payload
- THEN it records sanitized metadata using the AgentKB event schema
- AND it does not require the legacy config to be rewritten first.

### Requirement: AgentKB skills

AgentKB SHALL package skills that guide safe knowledge-base use and maintenance.

#### Scenario: Skill inventory exposes KB workflows

- WHEN the dev or release `agent-kb` skill directory is inspected
- THEN it includes `kb-ingest`, `kb-query`, `kb-update`, `kb-compact`, `kb-lint`, `kb-reflect`, and `kb-promote`
- AND each skill has Codex frontmatter
- AND each skill describes context-pack-first loading, Markdown canonical storage, safe writes, and Git-reviewable outputs where relevant.

### Requirement: DevFlow decoupling

DevFlow SHALL not own AgentKB core behavior after extraction.

#### Scenario: DevFlow skill inventory excludes KB workflows

- WHEN the DevFlow skill directory is inspected
- THEN it does not include `kb-ingest`, `kb-query`, `kb-update`, `kb-compact`, `kb-lint`, `kb-reflect`, or `kb-promote`.

#### Scenario: DevFlow release smoke does not import KB core

- WHEN DevFlow release smoke tests import packaged behavior
- THEN they do not import `workflow_agent_kb` or AgentKB scaffold/lint/event functions from DevFlow.
