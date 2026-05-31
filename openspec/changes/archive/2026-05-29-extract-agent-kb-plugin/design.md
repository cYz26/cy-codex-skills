# Design: Extract AgentKB plugin

## Target State

The repository contains a standalone `agent-kb` plugin in both development and release roots. `agent-kb` owns the Markdown-first knowledge-base implementation and packages the Codex adapter needed to use it from Codex.

The knowledge base is not Codex-bound or Obsidian-bound:

- Markdown is the canonical durable storage.
- Git diff is the audit layer for local Markdown stores.
- Obsidian is an editor profile over Markdown.
- Codex is the first agent adapter.
- Feishu and other document editors are future adapters that import, export, or sync to canonical Markdown.

## Scope / Non-Goals

In scope:

- Independent plugin scaffold for `agent-kb`.
- Markdown-filesystem storage scripts and tests.
- Codex plugin packaging: manifest, skills, hooks, README, marketplace entries.
- Obsidian-compatible profile naming and generated starter files.
- Compatibility reads for recent `.codex/obsidian-kb.json` configuration.
- DevFlow cleanup so KB behavior is no longer owned by DevFlow.

Non-goals:

- Cloud document sync.
- Feishu API integration.
- Semantic search/vector indexes.
- Migration of existing real vault content.
- New runtime dependencies.

## Architecture Decisions

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| Name the plugin `agent-kb` | Describes the reusable capability without binding to Codex or Obsidian. | `codex-kb`, `obsidian-kb`, `markdown-kb` |
| Keep Markdown as canonical storage | Matches the user's requested durable format and preserves Git review. | Store canonical knowledge in Feishu, Notion, or a database |
| Treat Obsidian as `obsidian-compatible-markdown` profile | Keeps current ergonomics while avoiding a hard dependency. | Make Obsidian the core product identity |
| Treat Codex as an adapter packaged by this Codex plugin | Codex needs skills/hooks/manifests, but core naming should remain reusable. | Keep all naming Codex-specific |
| Use `.agent-kb.json` as canonical config | Avoids Codex-specific config while allowing Codex hooks to discover the KB. | Continue only with `.codex/obsidian-kb.json` |
| Preserve legacy config reads | Recent DevFlow KB behavior used `.codex/obsidian-kb.json`; reading it avoids a harsh transition. | Break compatibility immediately |
| One owning implementation | Prevents DevFlow and AgentKB scripts from drifting. | Duplicate the KB core in both plugins |

## Completion Contract

- [ ] `agent-kb` plugin manifests are valid and use no unsupported manifest fields; hook behavior is packaged in `hooks.json`.
- [ ] `agent-kb` release and dev marketplace entries exist.
- [ ] `agent-kb` owns `workflow_agent_kb.py`, `kb_scaffold.py`, `kb_lint.py`, and `kb_event_hook.py`.
- [ ] `agent-kb` owns seven KB skills: `kb-ingest`, `kb-query`, `kb-update`, `kb-compact`, `kb-lint`, `kb-reflect`, `kb-promote`.
- [ ] Generated scaffold writes Markdown canonical notes with required frontmatter and editor/profile language.
- [ ] Lint reports missing frontmatter, missing required fields, missing core files, stale/oversized context packs, and stale raw sources.
- [ ] Event capture writes sanitized metadata only and no-ops without config.
- [ ] DevFlow tests no longer require KB skill inventory or DevFlow-owned KB package behavior.
- [ ] Verification evidence is recorded.

## Capability Slices

### Slice 1: Validation Surface

**Goal**
- Add failing tests that describe the independent plugin and DevFlow decoupling before moving code.

**Files / Modules**
- `dev/plugins/agent-kb/tests/test_agent_kb.py`
- `plugins/agent-kb/tests/test_release_smoke.py`
- `dev/plugins/dev-flow/tests/test_project_orchestrator.py`
- `plugins/dev-flow/tests/test_release_smoke.py`
- `.agents/plugins/marketplace.json`
- `.agents/plugins/marketplace.dev.json`

**Implementation**
- [ ] Add tests for plugin manifest, marketplace registration, scaffold, lint, event capture, skill inventory, and DevFlow decoupling.

**Tests**
- [ ] Watch focused tests fail before implementation.

**Validation Commands**
```bash
python3 -m unittest dev/plugins/agent-kb/tests/test_agent_kb.py
python3 -m unittest plugins/agent-kb/tests/test_release_smoke.py
```

**Done When**
- [ ] Tests fail for missing `agent-kb` package behavior.

**Risks / Rollback**
- If compatibility expectations are unclear, update this design before implementation.

### Slice 2: AgentKB Plugin Package

**Goal**
- Create the standalone plugin and move KB behavior into it.

**Files / Modules**
- `dev/plugins/agent-kb/.codex-plugin/plugin.json`
- `dev/plugins/agent-kb/README.md`
- `dev/plugins/agent-kb/hooks.json`
- `dev/plugins/agent-kb/scripts/workflow_agent_kb.py`
- `dev/plugins/agent-kb/scripts/kb_scaffold.py`
- `dev/plugins/agent-kb/scripts/kb_lint.py`
- `dev/plugins/agent-kb/scripts/kb_event_hook.py`
- `dev/plugins/agent-kb/skills/kb-*/SKILL.md`
- `dev/plugins/agent-kb/assets/`
- Matching files under `plugins/agent-kb/`

**Implementation**
- [ ] Create plugin manifests and assets.
- [ ] Rename core functions to AgentKB terminology while preserving CLI behavior.
- [ ] Use `.agent-kb.json` as canonical config.
- [ ] Read legacy `.codex/agent-kb.json` and `.codex/obsidian-kb.json` as compatibility inputs.
- [ ] Write sanitized event metadata to `.agent-kb/events/session-YYYY-MM-DD.jsonl`.
- [ ] Update README to explain Markdown canonical storage, editor profiles, storage adapters, and agent adapters.

**Tests**
- [ ] Run focused `agent-kb` tests until green.

**Validation Commands**
```bash
python3 -m unittest dev/plugins/agent-kb/tests/test_agent_kb.py
python3 -m unittest plugins/agent-kb/tests/test_release_smoke.py
```

**Done When**
- [ ] Independent dev and release plugin tests pass.

**Risks / Rollback**
- If plugin extraction breaks packaging, keep implementation contained to `agent-kb` until tests are green.

### Slice 3: DevFlow Decoupling and Release Verification

**Goal**
- Remove DevFlow ownership of KB behavior and prove both plugins package cleanly.

**Files / Modules**
- `dev/plugins/dev-flow/README.md`
- `dev/plugins/dev-flow/hooks.json`
- `dev/plugins/dev-flow/scripts/workflow_lib.py`
- `dev/plugins/dev-flow/tests/test_project_orchestrator.py`
- `plugins/dev-flow/README.md`
- `plugins/dev-flow/hooks.json`
- `plugins/dev-flow/scripts/workflow_lib.py`
- `plugins/dev-flow/tests/test_release_smoke.py`
- `.planning/STATE.md`
- `.planning/verification/`

**Implementation**
- [ ] Remove or deprecate DevFlow-owned KB scripts, hooks, and skill inventory.
- [ ] Leave DevFlow documentation pointing users to `agent-kb`.
- [ ] Update tests to assert DevFlow no longer packages KB as a native skill set.
- [ ] Record verification evidence and update workflow state.

**Tests**
- [ ] Run dev/release plugin suites.

**Validation Commands**
```bash
openspec validate extract-agent-kb-plugin --strict
python3 -m unittest discover -s dev/plugins/agent-kb/tests
python3 -m unittest discover -s plugins/agent-kb/tests
python3 -m unittest discover -s dev/plugins/dev-flow/tests
python3 -m unittest discover -s plugins/dev-flow/tests
```

**Done When**
- [ ] `agent-kb` is independently packaged and DevFlow remains healthy without owning KB implementation.

**Risks / Rollback**
- If decoupling causes compatibility churn, leave thin DevFlow guidance but keep one owning implementation in `agent-kb`.

## Execution Ledger

Track slice status in `tasks.md`. Mark items done only after the listed validation command passes or a blocker is recorded.

## Data Flow

Scaffold:

```text
kb_scaffold.py --repo <repo> --vault <vault> --project <project>
  -> workflow_agent_kb.scaffold_agent_kb
  -> writes Markdown canonical vault files
  -> writes .agent-kb.json in the target repo
  -> JSON report with written/skipped/configured paths
```

Lint:

```text
kb_lint.py --vault <vault> --project <project>
  -> scans Markdown canonical note directories
  -> reports frontmatter/core/context/raw-source findings
  -> optionally writes proposed-changes/kb-lint-YYYY-MM-DD.md
```

Event capture:

```text
Codex hook payload
  -> kb_event_hook.py
  -> discover .agent-kb.json or compatibility config
  -> append sanitized metadata to <vault>/.agent-kb/events/
```

## Compatibility

- Existing `.codex/obsidian-kb.json` may be read as a compatibility source.
- New scaffold writes `.agent-kb.json`.
- DevFlow should not require `agent-kb`; it should remain an optional companion plugin.
- No new production dependency is introduced.

## Validation Commands

```bash
openspec validate extract-agent-kb-plugin --strict
python3 -m unittest dev/plugins/agent-kb/tests/test_agent_kb.py
python3 -m unittest plugins/agent-kb/tests/test_release_smoke.py
python3 -m unittest discover -s dev/plugins/dev-flow/tests
python3 -m unittest discover -s plugins/dev-flow/tests
```

## Review Checklist

- [ ] Plugin name, manifest name, and marketplace name are all `agent-kb`.
- [ ] Markdown is described as the canonical store.
- [ ] Obsidian appears only as a profile/editor surface.
- [ ] Codex appears only as the packaged adapter.
- [ ] No Feishu sync is implemented in this change.
- [ ] Tests cover package independence and DevFlow decoupling.
