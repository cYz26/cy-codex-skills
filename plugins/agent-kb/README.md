# AgentKB

AgentKB packages a personal-first, Markdown-first knowledge-base workflow for agents.

Markdown files are the canonical durable store. Git diff is the audit layer. Obsidian is the first editor profile, expressed as `obsidian-compatible-markdown`, and Codex is the first packaged agent adapter through this Codex plugin.

## Storage And Adapters

- Canonical storage: local Markdown files with structured frontmatter.
- Storage adapter: `markdown-filesystem`.
- Editor profile: `obsidian-compatible-markdown`.
- Optional editor adapter: `obsidian-cli`.
- Agent adapter: `codex`.

Markdown remains the source of truth. Obsidian CLI is an optional local adapter for Obsidian-assisted search, read, create, and daily-note workflows; it is not required for scaffold, lint, Git review, or direct Markdown writes.

## Scaffold

```bash
python3 scripts/kb_scaffold.py \
  --repo /path/to/repo \
  --vault /path/to/markdown-vault \
  --project project-name \
  --owner owner \
  --json
```

The scaffold creates:

| Directory | Purpose |
|---|---|
| `_system/` | Vault protocol: structure, routing, metadata, write policy, promotion policy, templates, indexes |
| `_agent/` | Agent receipts, logs, lint reports, evals, and context packs |
| `_bases/` | Obsidian Bases view definitions |
| `inbox/` | Quick captures, Codex captures, web clips, and unsorted input |
| `calendar/` | Daily, weekly, monthly, and meeting notes |
| `personal/` | Private personal knowledge; not read by default |
| `work/` | Work-private meetings, tasks, people, reflections, and playbooks |
| `projects/` | Project state, context packs, decisions, logs, research, candidates, and proposed changes |
| `knowledge/` | Durable concepts, comparisons, tools, summaries, and reusable knowledge |
| `promotion/` | Candidate, sanitized, reviewed, exported, rejected promotion flow |
| `references/` | External source material |
| `assets/` | Images, PDFs, attachments, and canvas files |
| `archive/` | Archived or stale notes; not read by default |

It writes `/path/to/repo/.agent-kb.json` with `vault_profile: personal-first`, `storage_adapter: markdown-filesystem`, `editor_profile: obsidian-compatible-markdown`, and optional `editor_adapter: obsidian-cli`.

Existing generated Markdown files are skipped unless `--force` is passed.

## Lint

```bash
python3 scripts/kb_lint.py \
  --vault /path/to/markdown-vault \
  --project project-name \
  --write-report \
  --json
```

Lint checks missing frontmatter, missing required fields, missing core files, missing protocol files, stale or oversized context packs, raw sources awaiting processing, stale captures, stale promotion candidates, notes requiring review, and active notes referencing archived content. Reports are written under `projects/<project>/proposed-changes/`.

## Capture And Promotion

Use `kb-capture` for free-form personal, work, project, or reusable knowledge input. It preserves raw input under `inbox/codex-captures/`, routes structured notes through `_system/routing-rules.md`, and writes routing receipts under `_agent/routing-receipts/`.

Personal notes are private by default. Project-useful extracts go to `projects/<project>/candidates/`; team-shareable material goes through `promotion/candidates/`, `promotion/sanitized/`, `promotion/reviewed/`, and `promotion/exported/`.

## Obsidian CLI

AgentKB can use Obsidian CLI when available. Enable it in Obsidian under Settings -> General -> Command line interface. AgentKB discovers `obsidian` first and falls back to `/Applications/Obsidian.app/Contents/MacOS/obsidian-cli`.

If the CLI is missing, Obsidian is not running, or a command fails, AgentKB reports the fallback reason and continues to use Markdown filesystem behavior.

## Reflect And Promote

AgentKB treats failures, corrections, and review findings as learning inputs.
Use `kb-reflect` to record the incident, root cause, generalized lesson,
prevention mechanism, validation evidence, and residual risk. Use `kb-promote`
when repeated or stable lessons should become playbooks, skill guidance,
`AGENTS.md` proposed changes, eval cases, context packs, tests, lint, or
runtime guards.

## Event Capture

`kb_event_hook.py` no-ops unless the current repository has `.agent-kb.json` or a compatibility config at `.codex/agent-kb.json` or `.codex/obsidian-kb.json`.

When enabled, hook metadata is appended to:

```text
<vault>/.agent-kb/events/session-YYYY-MM-DD.jsonl
```

The event records include event type, timestamp, tool name, status, cwd, hashes, and size metadata. They do not store raw prompt text, command output bodies, secrets, or full hook payloads.

## Skills

AgentKB includes `kb-capture`, `kb-ingest`, `kb-query`, `kb-update`, `kb-compact`, `kb-lint`, `kb-reflect`, and `kb-promote`. These skills load the smallest sufficient context first, keep updates concise, write reviewable Markdown, respect personal/private boundaries, and require Git diff review for knowledge changes.
