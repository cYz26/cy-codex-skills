from __future__ import annotations

from datetime import date
from pathlib import Path


def vault_directories(project: str):
    return [
        "00-inbox/web-clips",
        "00-inbox/chatgpt-exports",
        "00-inbox/temp-notes",
        "01-raw/articles",
        "01-raw/papers",
        "01-raw/transcripts",
        "01-raw/screenshots",
        "01-raw/source-documents",
        "10-wiki/concepts",
        "10-wiki/entities",
        "10-wiki/comparisons",
        "10-wiki/summaries",
        f"20-projects/{project}/logs",
        f"20-projects/{project}/proposed-changes",
        "30-research/agent-adapters",
        "30-research/editor-profiles",
        "30-research/memory",
        "30-research/agent-frameworks",
        "30-research/llm-wiki",
        "40-decisions",
        "50-playbooks",
        "60-context-packs",
        "70-agent-logs",
        "80-bases",
        "90-archive",
    ]


def scaffold_files(values: dict[str, str]):
    project = values["project"]
    owner = values["owner"]
    today = values["today"]
    files = core_scaffold_files(project, owner, today)
    files.update(project_scaffold_files(project, owner, today))
    files.update(decision_and_playbook_files(project, owner))
    files.update(context_and_profile_files(project, owner, today))
    return files


def core_scaffold_files(project: str, owner: str, today: str):
    return {
        ".gitignore": gitignore_template(),
        "AGENTS.md": agents_template(project),
        "10-wiki/index.md": note(
            "wiki-index",
            project,
            "Knowledge Index",
            "This index is the navigation layer across agents plus Markdown editor profiles.\n\n"
            "## Project Context\n\n"
            f"- [[../20-projects/{project}/context-pack|{project} context pack]]\n"
            f"- [[../20-projects/{project}/current-state|Current state]]\n"
            f"- [[../20-projects/{project}/decisions|Decisions]]\n"
            f"- [[../20-projects/{project}/open-questions|Open questions]]\n\n"
            "## Core Playbooks\n\n"
            "- [[../50-playbooks/kb-ingest|KB ingest]]\n"
            "- [[../50-playbooks/kb-update|KB update]]\n"
            "- [[../50-playbooks/kb-lint|KB lint]]\n",
            note_type="wiki",
            status="active",
            owner=owner,
        ),
        "10-wiki/log.md": note(
            "log",
            project,
            "Knowledge Base Log",
            f"- {today}: Initialized the AgentKB Markdown knowledge base scaffold.\n",
            note_type="log",
            agent_writable=True,
            owner=owner,
        ),
    }


def project_scaffold_files(project: str, owner: str, today: str):
    return {
        f"20-projects/{project}/overview.md": project_note(
            project,
            "Project Overview",
            "overview",
            "Build, maintain, and safely update a Markdown-first knowledge base.",
            owner=owner,
        ),
        f"20-projects/{project}/current-state.md": project_note(
            project,
            "Current State",
            "current-state",
            "The vault has been initialized. Keep this note concise; update it when durable state changes.",
            agent_writable=True,
            owner=owner,
        ),
        f"20-projects/{project}/architecture.md": project_note(
            project,
            "Architecture",
            "architecture",
            "Markdown is canonical, Git is the review layer, Obsidian is an editor profile, "
            "Codex is one agent adapter.",
            owner=owner,
        ),
        f"20-projects/{project}/decisions.md": project_note(
            project,
            "Decisions",
            "decision",
            "- Use Markdown as the canonical durable knowledge store.\n"
            "- Treat Obsidian as an editor profile over Markdown.\n"
            "- Use context packs as task-level working context caches.\n",
            agent_writable=True,
            owner=owner,
        ),
        f"20-projects/{project}/open-questions.md": project_note(
            project,
            "Open Questions",
            "open-question",
            "- Review whether editor-profile metadata needs project-specific customization.\n",
            agent_writable=True,
            owner=owner,
        ),
        f"20-projects/{project}/context-pack.md": context_pack_template(project, today, owner),
        f"20-projects/{project}/logs/{today}.md": note(
            "task-log",
            project,
            f"Task Log {today}",
            "- Knowledge base scaffold initialized.\n",
            note_type="log",
            agent_writable=True,
            owner=owner,
        ),
    }


def decision_and_playbook_files(project: str, owner: str):
    return {
        "40-decisions/adr-0001-use-markdown-as-canonical-kb.md": adr_template(
            project,
            "adr-0001-use-markdown-as-canonical-kb",
            "Use Markdown as the canonical knowledge store",
            "accepted",
            "Markdown files are the durable source of truth, Git is the audit layer, "
            "Obsidian is one compatible editor profile; Codex is one agent adapter.",
            owner,
        ),
        "40-decisions/adr-0002-use-context-pack.md": adr_template(
            project,
            "adr-0002-use-context-pack",
            "Use Context Pack as the task cache",
            "accepted",
            "Agents start from the smallest sufficient context pack, then follow the index only when needed.",
            owner,
        ),
        "50-playbooks/kb-ingest.md": playbook_template(
            project,
            "kb-ingest",
            "Normalize raw sources into summaries, wiki notes, index entries, logs, open questions.",
            owner,
        ),
        "50-playbooks/kb-update.md": playbook_template(
            project,
            "kb-update",
            "Update logs, current state, decisions, open questions, stale context packs after work.",
            owner,
        ),
        "50-playbooks/kb-lint.md": playbook_template(
            project,
            "kb-lint",
            "Check frontmatter, stale context packs, missing core files, raw sources awaiting processing.",
            owner,
        ),
    }


def context_and_profile_files(project: str, owner: str, today: str):
    return {
        f"60-context-packs/{project}.md": context_pack_template(project, today, owner),
        f"70-agent-logs/{today}.md": note(
            "agent-log",
            project,
            f"Agent Log {today}",
            "- AgentKB workflow scaffold initialized.\n",
            note_type="log",
            agent_writable=True,
            owner=owner,
        ),
        "80-bases/Projects.base": base_template("Projects", "project, status, updated, owner, context_pack"),
        "80-bases/Decisions.base": base_template(
            "Decisions",
            "id, project, status, created, updated, confidence, related",
        ),
        "80-bases/Research.base": base_template("Research", "topic, source, confidence, updated, status, related"),
        "80-bases/ContextPacks.base": base_template(
            "Context Packs",
            "project, updated, status, word_count, stale, source_notes",
        ),
        "80-bases/OpenQuestions.base": base_template(
            "Open Questions",
            "question, project, status, owner, created, updated, related",
        ),
    }


def required_core_files(project: str):
    return [
        "AGENTS.md",
        "10-wiki/index.md",
        "10-wiki/log.md",
        f"20-projects/{project}/overview.md",
        f"20-projects/{project}/current-state.md",
        f"20-projects/{project}/decisions.md",
        f"20-projects/{project}/open-questions.md",
        f"20-projects/{project}/context-pack.md",
        "40-decisions/adr-0001-use-markdown-as-canonical-kb.md",
        "40-decisions/adr-0002-use-context-pack.md",
        "50-playbooks/kb-ingest.md",
        "50-playbooks/kb-update.md",
        "50-playbooks/kb-lint.md",
        f"60-context-packs/{project}.md",
    ]


def write_scaffold_file(path: Path, content: str, force: bool = False):
    if path.exists() and not force:
        return "skipped"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return "written"


def gitignore_template():
    return "\n".join(
        [
            ".obsidian/workspace*",
            ".obsidian/cache",
            ".obsidian/plugins/*/data.json",
            ".trash/",
            ".DS_Store",
            "*.tmp",
            "",
        ]
    )


def agents_template(project: str):
    return f"""# AGENTS.md

## Role

This repository is connected to the AgentKB Markdown knowledge base `{project}`.
Markdown is the canonical durable storage. Git is the audit layer.
Obsidian is an editor profile over Markdown. Codex is one agent adapter.

## Context Loading Order

Before starting a task:

1. Read `20-projects/{project}/context-pack.md`.
2. Read `20-projects/{project}/current-state.md`.
3. Read `20-projects/{project}/decisions.md`.
4. Read `20-projects/{project}/open-questions.md`.

Do not scan the full Markdown vault unless explicitly requested.
If context is insufficient, read `10-wiki/index.md`, then select only task-relevant canonical notes.

## Knowledge Priority

Trust information in this order:

1. This `AGENTS.md`
2. Accepted ADRs plus decisions
3. `current-state.md`
4. `context-pack.md`
5. Task-relevant canonical notes
6. Retrieved memory snippets
7. Logs, inbox, draft notes

Ignore archived/stale notes unless explicitly requested.

## After Work

After completing knowledge-bearing work:

1. Append a concise summary to `20-projects/{project}/logs/YYYY-MM-DD.md`.
2. Update `current-state.md` when durable project state changed.
3. Update `decisions.md` when a durable decision was made.
4. Update `open-questions.md` when uncertainty remains.
5. Refresh `context-pack.md` only when stale.
6. Review `git diff` before committing.

## Safety Rules

- Never delete notes.
- Never rename/move canonical notes without approval.
- Never overwrite archived notes.
- Never directly rewrite accepted ADRs.
- For large changes, write to `20-projects/{project}/proposed-changes/` first.
- Do not store secrets, API keys, credentials, sensitive personal data.
- Keep knowledge updates concise, source-grounded.
"""


def note(
    note_id: str,
    project: str,
    title: str,
    body: str,
    *,
    note_type: str,
    status: str = "active",
    confidence: str = "high",
    agent_readable: bool = True,
    agent_writable: bool = False,
    owner: str = "owner",
):
    today = date.today().isoformat()
    return f"""---
id: {note_id}
type: {note_type}
project: {project}
status: {status}
created: {today}
updated: {today}
owner: {owner}
source: agent-kb
confidence: {confidence}
agent_readable: {str(agent_readable).lower()}
agent_writable: {str(agent_writable).lower()}
tags:
  - ai-agent
  - agent-kb
  - markdown
related: []
---

# {title}

{body.rstrip()}
"""


def project_note(
    project: str,
    title: str,
    note_type: str,
    body: str,
    agent_writable: bool = False,
    owner: str = "owner",
):
    return note(note_type, project, title, body, note_type=note_type, agent_writable=agent_writable, owner=owner)


def context_pack_template(project: str, today: str, owner: str):
    return f"""---
id: context-pack-{project}
type: context-pack
project: {project}
status: active
created: {today}
updated: {today}
owner: {owner}
source: agent-kb
confidence: high
agent_readable: true
agent_writable: true
source_notes:
  - [[overview]]
  - [[current-state]]
  - [[decisions]]
  - [[open-questions]]
tags:
  - ai-agent
  - agent-kb
  - markdown
related:
  - [[current-state]]
  - [[decisions]]
  - [[open-questions]]
---

# {project} - Context Pack

## Goal

Build an AgentKB knowledge base where durable knowledge is kept in Markdown,
reviewed through Git, disclosed through a concise context pack.

## Current State

- Markdown is the canonical durable storage.
- Obsidian is an editor profile over Markdown, not the source of truth.
- Codex is one agent adapter that starts from this context pack, then follows
  the index only when more context is needed.
- Memory is optional, never the authority over durable project facts.

## Key Decisions

- Do not scan the whole vault by default.
- Write durable work results into logs, current state, decisions, open questions,
  proposed changes, refreshed context packs.
- Keep raw sources separate from canonical wiki notes.
- Review all agent writes through Git diff.

## Constraints

- Do not delete notes.
- Do not modify archived notes.
- Do not directly rewrite accepted ADRs.
- Do not store secrets, API keys, credentials, sensitive personal data.

## Open Questions

- Should this vault use custom editor-profile metadata beyond the generated starter files?
- Which repeated patterns should be promoted into playbooks/skills?
"""


def adr_template(project: str, note_id: str, title: str, status: str, body: str, owner: str):
    body_text = f"## Status\n\n{status}\n\n## Decision\n\n{body}\n"
    return note(
        note_id,
        project,
        title,
        body_text,
        note_type="decision",
        status=status,
        owner=owner,
    )


def playbook_template(project: str, name: str, body: str, owner: str):
    body_text = (
        f"## Purpose\n\n{body}\n\n"
        "## Output\n\nProduce concise, Git-reviewable Markdown updates.\n"
    )
    return note(
        name,
        project,
        name,
        body_text,
        note_type="playbook",
        agent_writable=True,
        owner=owner,
    )


def base_template(name: str, columns: str):
    return f"""# {name}

columns: {columns}
filters: edit in Obsidian Bases/another Markdown-aware editor as needed
"""
