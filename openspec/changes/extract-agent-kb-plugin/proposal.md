# Extract AgentKB plugin

## Why

The knowledge-base workflow should not be owned by DevFlow, Codex, or Obsidian. The durable idea is broader: a Markdown-first knowledge base that agents can read, maintain, lint, compact, and promote through safe workflows.

The current implementation lives inside DevFlow and uses Obsidian/Codex naming (`workflow_obsidian_kb.py`, `.codex/obsidian-kb.json`, `.codex/kb-events/`). That makes the capability harder to reuse with other agents or editor surfaces such as Feishu while still keeping Markdown as the canonical storage format.

## What Changes

- Add independent `agent-kb` plugin roots under `dev/plugins/agent-kb/` and `plugins/agent-kb/`.
- Move the KB scripts, skills, hooks, docs, tests, and packaged behavior out of DevFlow into `agent-kb`.
- Rename the core model from Obsidian-specific to Markdown-first AgentKB terminology.
- Keep Markdown files as canonical storage; Obsidian is only an editor profile.
- Add plugin metadata and marketplace entries for `agent-kb`.
- Leave DevFlow as a light integration point that can mention or recommend `agent-kb`, without owning the KB implementation.

## Target State

`agent-kb` is a standalone Codex plugin that packages a Markdown-first, agent-agnostic knowledge-base workflow:

- The canonical storage format is local Markdown files with structured frontmatter/properties.
- The first storage adapter is `markdown-filesystem`.
- The first editor profile is `obsidian-compatible-markdown`.
- The first agent adapter is `codex`, expressed through Codex plugin metadata, skills, and hooks.
- Future editor integrations such as Feishu import/export/sync are explicitly adapters that convert to or from canonical Markdown, not alternate durable stores.
- DevFlow no longer contains the KB skills or core implementation; it can reference `agent-kb` as an optional companion plugin.

## Scope

- Project mode: brownfield
- Change type: refactor

## Non-Goals

- Do not implement Feishu, Notion, vector search, or external database adapters in this change.
- Do not make cloud documents the source of truth.
- Do not add production dependencies.
- Do not delete user-authored knowledge vault content.
- Do not archive previous OpenSpec changes as part of this extraction.

## Completion Contract

- [ ] `dev/plugins/agent-kb/` and `plugins/agent-kb/` contain valid plugin manifests, README, hooks, scripts, skills, tests, and assets.
- [ ] Repo marketplace files expose `agent-kb` in both release and dev marketplaces.
- [ ] AgentKB scripts use Markdown-first names and config: `.agent-kb.json` is canonical, with optional compatibility reads for legacy Codex/Obsidian config.
- [ ] Scaffold output still creates an Obsidian-compatible Markdown vault, but generated instructions describe Obsidian as an editor profile.
- [ ] Event capture defaults to a generic AgentKB event path, stores sanitized metadata only, and no-ops without configuration.
- [ ] DevFlow no longer owns KB skills/hooks/core scripts, or keeps only documented compatibility guidance.
- [ ] Tests cover independent plugin packaging, scaffold, lint, event capture, marketplace registration, and DevFlow decoupling.
- [ ] Verification evidence is recorded before archive.

## Risks

- Existing uncommitted DevFlow KB files may be mid-change; extraction must not revert unrelated DevFlow work.
- Compatibility with `.codex/obsidian-kb.json` should be deliberate so recent users have a transition path.
- Plugin duplication can create divergent KB implementations; the final state must have one owning implementation.
