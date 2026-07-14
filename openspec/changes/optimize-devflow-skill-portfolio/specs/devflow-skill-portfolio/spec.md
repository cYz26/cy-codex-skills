## ADDED Requirements

### Requirement: DevFlow maintains an evidence-backed public skill portfolio
DevFlow SHALL keep each published skill until a compatibility-safe retirement
contract proves that its public name, project links, routes, wrappers, and
consumers can be migrated without unmanaged leftovers.

#### Scenario: Current portfolio is audited
- **WHEN** the DevFlow source, release, dependency catalog, migration manifest,
  activation behavior, tests, and project links are compared
- **THEN** the same sixteen public skill names are present
- **AND** every skill is classified with a distinct workflow or adapter owner
- **AND** no skill is removed solely because static evaluation lacks usage data.

#### Scenario: A future public skill retirement is proposed
- **WHEN** a later change proposes removing or extracting a managed skill name
- **THEN** that change MUST define trusted-link dry-run, explicit apply,
  rollback, alias, custom-path preservation, and idempotent state migration
- **AND** existing projects MUST NOT be left with orphaned managed skill links.

### Requirement: Supporting resources are progressively disclosed and reachable
Every documentation or output resource bundled under a DevFlow skill SHALL be
named directly by that skill's `SKILL.md`, and the skill SHALL state when the
resource is needed.

#### Scenario: Skill resources are inspected
- **WHEN** files below a skill's `references/` or `assets/` directory are listed
- **THEN** every file path is referenced by the owning `SKILL.md`
- **AND** conditional operational detail is loaded only for the matching branch
- **AND** essential authorization, stop, and verification rules remain in the
  main skill body.

#### Scenario: A duplicated resource has no live link
- **WHEN** a supporting file has no inbound link, no unique live contract, and
  duplicates the skill body or canonical DevFlow guidance
- **THEN** the file is removed from source and generated release assets
- **AND** focused tests prove that retained resources remain discoverable.

### Requirement: DevFlow refresh remains a focused orchestration facade
The `dev-flow-refresh` skill SHALL own global-before-project sequencing while
delegating updater, migration, setup, doctor, provider-cleanup, and AGENTS drift
details to their focused owners or directly linked conditional references.

#### Scenario: DevFlow refresh is selected
- **WHEN** a DevFlow installation or project workflow needs refresh
- **THEN** the main skill defines the global-first order, discovery boundary,
  authorization gate, and final evidence
- **AND** it does not duplicate the complete procedures already owned by
  `codex-updater`, `plugin-project-migration`, `project-setup`, or
  `workflow-doctor`.

### Requirement: Natural-language skill routing remains stable
This optimization SHALL preserve the current invocation policy of fifteen
implicitly discoverable DevFlow skills and explicit-only
`claude-code-delegate`.

#### Scenario: Invocation metadata is inspected
- **WHEN** DevFlow skill metadata and `agents/openai.yaml` files are compared
- **THEN** only `claude-code-delegate` disables implicit invocation
- **AND** no static-budget optimization disables natural-language routing for
  another DevFlow skill.
