# AgentKB

AgentKB packages a Markdown-first knowledge-base workflow for agents.

Markdown files are the canonical durable store. Git diff is the audit layer. Obsidian is the first editor profile, expressed as `obsidian-compatible-markdown`, and Codex is the first packaged agent adapter through this Codex plugin.

## Storage And Adapters

- Canonical storage: local Markdown files with structured frontmatter.
- Storage adapter: `markdown-filesystem`.
- Editor profile: `obsidian-compatible-markdown`.
- Agent adapter: `codex`.

Future document editors such as Feishu should import, export, or sync to Markdown. They should not replace Markdown as the source of truth.

## Scaffold

```bash
python3 scripts/kb_scaffold.py \
  --repo /path/to/repo \
  --vault /path/to/markdown-vault \
  --project project-name \
  --owner owner \
  --json
```

The scaffold creates inbox, raw-source, wiki, project, decision, playbook, context-pack, log, Bases/profile, and archive folders. It writes `/path/to/repo/.agent-kb.json` with `storage_adapter: markdown-filesystem` and `editor_profile: obsidian-compatible-markdown`.

Existing generated Markdown files are skipped unless `--force` is passed.

## Lint

```bash
python3 scripts/kb_lint.py \
  --vault /path/to/markdown-vault \
  --project project-name \
  --write-report \
  --json
```

Lint checks missing frontmatter, missing required fields, missing core files, stale or oversized context packs, and raw sources awaiting processing. Reports are written under `20-projects/<project>/proposed-changes/`.

## Event Capture

`kb_event_hook.py` no-ops unless the current repository has `.agent-kb.json` or a compatibility config at `.codex/agent-kb.json` or `.codex/obsidian-kb.json`.

When enabled, hook metadata is appended to:

```text
<vault>/.agent-kb/events/session-YYYY-MM-DD.jsonl
```

The event records include event type, timestamp, tool name, status, cwd, hashes, and size metadata. They do not store raw prompt text, command output bodies, secrets, or full hook payloads.

## Skills

AgentKB includes `kb-ingest`, `kb-query`, `kb-update`, `kb-compact`, `kb-lint`, `kb-reflect`, and `kb-promote`. These skills load context packs first, keep updates concise, write reviewable Markdown, and require Git diff review for knowledge changes.
