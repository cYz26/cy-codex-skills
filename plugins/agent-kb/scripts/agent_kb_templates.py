from __future__ import annotations

from datetime import date
from pathlib import Path


def vault_directories(project: str):
    return [
        "_system/templates",
        "_system/indexes",
        "_system/schemas",
        "_agent/routing-receipts",
        "_agent/logs",
        "_agent/evals",
        "_agent/context-packs",
        "_agent/lint-reports",
        "_agent/source-intake",
        "_agent/source-intake/extracted",
        "_agent/source-intake/receipts",
        "_agent/problem-signals",
        "_bases",
        "inbox/quick-captures",
        "inbox/codex-captures",
        "inbox/web-clips",
        "inbox/chatgpt-exports",
        "inbox/unsorted",
        "calendar/daily",
        "calendar/weekly",
        "calendar/monthly",
        "calendar/meetings",
        "personal/life",
        "personal/health",
        "personal/finance",
        "personal/reading",
        "personal/ideas",
        "personal/reflections",
        "work/meetings",
        "work/tasks",
        "work/people",
        "work/reflections",
        "work/playbooks",
        "raw/articles",
        "raw/papers",
        "raw/transcripts",
        "raw/screenshots",
        "raw/source-documents",
        "knowledge/concepts",
        "knowledge/entities",
        "knowledge/comparisons",
        "knowledge/summaries",
        "knowledge/ai-agent",
        "knowledge/codex",
        "knowledge/obsidian",
        "knowledge/context-engineering",
        "knowledge/tools",
        "knowledge/playbooks",
        f"projects/{project}/logs",
        f"projects/{project}/proposed-changes",
        f"projects/{project}/proposed-changes/problem-reflections",
        f"projects/{project}/candidates",
        f"projects/{project}/research",
        "research/agent-adapters",
        "research/editor-profiles",
        "research/memory",
        "research/agent-frameworks",
        "research/llm-wiki",
        "decisions",
        "playbooks",
        "promotion/candidates",
        "promotion/sanitized",
        "promotion/reviewed",
        "promotion/exported",
        "promotion/rejected",
        "references/articles",
        "references/papers",
        "references/docs",
        "references/transcripts",
        "assets/images",
        "assets/pdfs",
        "assets/attachments",
        "assets/canvas",
        "archive",
    ]


def scaffold_files(values: dict[str, str]):
    project = values["project"]
    owner = values["owner"]
    today = values["today"]
    files = core_scaffold_files(project, owner, today)
    files.update(project_scaffold_files(project, owner, today))
    files.update(problem_capture_scaffold_files(project, owner))
    files.update(decision_and_playbook_files(project, owner))
    files.update(context_and_profile_files(project, owner, today))
    return files


def core_scaffold_files(project: str, owner: str, today: str):
    return {
        ".gitignore": gitignore_template(),
        "AGENTS.md": agents_template(project),
        "_system/kb-structure.md": protocol_template(project, "KB Structure", kb_structure_body(project)),
        "_system/routing-rules.md": protocol_template(project, "Routing Rules", routing_rules_body(project)),
        "_system/metadata-schema.md": protocol_template(project, "Metadata Schema", metadata_schema_body()),
        "_system/write-policy.md": protocol_template(project, "Write Policy", write_policy_body(project)),
        "_system/promotion-policy.md": protocol_template(project, "Promotion Policy", promotion_policy_body(project)),
        "_system/indexes/home.md": note(
            "home-index",
            project,
            "AgentKB Home",
            "This index is the human/agent entry point for the personal-first vault.\n\n"
            "## Project Context\n\n"
            f"- [[../../projects/{project}/context-pack|{project} context pack]]\n"
            f"- [[../../projects/{project}/current-state|Current state]]\n"
            f"- [[../../projects/{project}/decisions|Decisions]]\n"
            f"- [[../../projects/{project}/open-questions|Open questions]]\n\n"
            "## Protocol\n\n"
            "- [[../kb-structure|KB structure]]\n"
            "- [[../routing-rules|Routing rules]]\n"
            "- [[../metadata-schema|Metadata schema]]\n"
            "- [[../write-policy|Write policy]]\n"
            "- [[../promotion-policy|Promotion policy]]\n\n"
            "## Knowledge\n\n"
            "- [[knowledge-index|Knowledge index]]\n"
            f"- [[../../projects/_project-index|Project index]]\n",
            note_type="index",
            status="active",
            owner=owner,
        ),
        "_system/indexes/knowledge-index.md": note(
            "knowledge-index",
            project,
            "Knowledge Index",
            "This index is the navigation layer across reusable knowledge, projects, playbooks.\n\n"
            "## Durable Knowledge\n\n"
            "- [[../../knowledge/index|Knowledge home]]\n"
            "- [[../../knowledge/log|Knowledge log]]\n\n"
            "## Core Playbooks\n\n"
            "- [[../../playbooks/kb-capture|KB capture]]\n"
            "- [[../../playbooks/kb-ingest|KB ingest]]\n"
            "- [[../../playbooks/kb-update|KB update]]\n"
            "- [[../../playbooks/kb-lint|KB lint]]\n"
            "- [[../../playbooks/kb-reflect|KB reflect]]\n"
            "- [[../../playbooks/kb-promote|KB promote]]\n",
            note_type="index",
            status="active",
            owner=owner,
        ),
        "_system/templates/capture.md": capture_template(project, owner),
        "_system/templates/context-pack.md": context_pack_template(project, today, owner),
        "knowledge/index.md": note(
            "knowledge-home",
            project,
            "Knowledge Home",
            "Long-lived concepts, comparisons, tool notes, reusable playbooks live under `knowledge/`.\n",
            note_type="index",
            status="active",
            owner=owner,
        ),
        "knowledge/log.md": note(
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
        "projects/_project-index.md": note(
            "project-index",
            project,
            "Project Index",
            f"- [[{project}/overview|{project} overview]]\n"
            f"- [[{project}/context-pack|{project} context pack]]\n"
            f"- [[{project}/candidates|{project} candidates]]\n",
            note_type="index",
            status="active",
            owner=owner,
        ),
        f"projects/{project}/overview.md": project_note(
            project,
            "Project Overview",
            "overview",
            "Build, maintain, safely update a Markdown-first knowledge base.",
            owner=owner,
        ),
        f"projects/{project}/current-state.md": project_note(
            project,
            "Current State",
            "current-state",
            "The vault has been initialized. Keep this note concise; update it when durable state changes.",
            agent_writable=True,
            owner=owner,
        ),
        f"projects/{project}/architecture.md": project_note(
            project,
            "Architecture",
            "architecture",
            "Markdown is canonical, Git is the review layer, Obsidian is an editor profile, "
            "Codex is one agent adapter.",
            owner=owner,
        ),
        f"projects/{project}/decisions.md": project_note(
            project,
            "Decisions",
            "decision",
            "- Use Markdown as the canonical durable knowledge store.\n"
            "- Treat Obsidian as an editor profile over Markdown.\n"
            "- Use context packs as task-level working context caches.\n",
            agent_writable=True,
            owner=owner,
        ),
        f"projects/{project}/open-questions.md": project_note(
            project,
            "Open Questions",
            "open-question",
            "- Review whether editor-profile metadata needs project-specific customization.\n",
            agent_writable=True,
            owner=owner,
        ),
        f"projects/{project}/context-pack.md": context_pack_template(project, today, owner),
        f"projects/{project}/logs/{today}.md": note(
            "task-log",
            project,
            f"Task Log {today}",
            "- Knowledge base scaffold initialized.\n",
            note_type="log",
            agent_writable=True,
            owner=owner,
        ),
        f"projects/{project}/candidates/README.md": project_note(
            project,
            "Project Candidates",
            "candidate-index",
            "Project-useful material extracted from personal/work/knowledge notes waits here before review.",
            agent_writable=True,
            owner=owner,
        ),
    }


def problem_capture_scaffold_files(project: str, owner: str):
    return {
        f"projects/{project}/proposed-changes/problem-reflections/README.md": project_note(
            project,
            "Problem Reflection Drafts",
            "problem-reflection-index",
            "Automatic problem signals and manual problem records are reviewed here with `kb-reflect` "
            "before any lesson becomes durable knowledge.",
            agent_writable=True,
            owner=owner,
        ),
    }


def decision_and_playbook_files(project: str, owner: str):
    return {
        "playbooks/kb-capture.md": playbook_template(
            project,
            "kb-capture",
            "Preserve free-form input, route it through the vault protocol, write a routing receipt.",
            owner,
        ),
        "playbooks/kb-import.md": playbook_template(
            project,
            "kb-import",
            "Import local documents, links, Feishu/Lark docs, and Drive folders into preserved "
            "source material before kb-ingest extracts durable knowledge.",
            owner,
        ),
        "decisions/adr-0001-use-markdown-as-canonical-kb.md": adr_template(
            project,
            "adr-0001-use-markdown-as-canonical-kb",
            "Use Markdown as the canonical knowledge store",
            "accepted",
            "Markdown files are the durable source of truth, Git is the audit layer, "
            "Obsidian is one compatible editor profile; Codex is one agent adapter.",
            owner,
        ),
        "decisions/adr-0002-use-context-pack.md": adr_template(
            project,
            "adr-0002-use-context-pack",
            "Use Context Pack as the task cache",
            "accepted",
            "Agents start from the smallest sufficient context pack, then follow the index only when needed.",
            owner,
        ),
        "playbooks/kb-ingest.md": playbook_template(
            project,
            "kb-ingest",
            "Normalize raw sources into summaries, wiki notes, index entries, logs, open questions.",
            owner,
        ),
        "playbooks/kb-update.md": playbook_template(
            project,
            "kb-update",
            "Update logs, current state, decisions, open questions, stale context packs after work.",
            owner,
        ),
        "playbooks/kb-lint.md": playbook_template(
            project,
            "kb-lint",
            "Check frontmatter, stale context packs, missing core files, raw sources awaiting processing.",
            owner,
        ),
        "playbooks/kb-reflect.md": playbook_template(
            project,
            "kb-reflect",
            "Turn failures, corrections, review findings into structured reflections. "
            "Start from automatic problem signals or manual problem drafts when available. "
            "Capture the incident, root cause, generalized lesson, prevention mechanism, "
            "validation evidence, residual risk before deciding whether promotion is justified.",
            owner,
        ),
        "playbooks/kb-promote.md": playbook_template(
            project,
            "kb-promote",
            "Promote repeated or stable reflections into the smallest durable destination: "
            "playbook, skill guidance, AGENTS proposed change, eval case, context pack, "
            "test, lint, runtime guard.",
            owner,
        ),
    }


def context_and_profile_files(project: str, owner: str, today: str):
    return {
        f"_agent/context-packs/{project}.md": context_pack_template(project, today, owner),
        f"_agent/logs/{today}.md": note(
            "agent-log",
            project,
            f"Agent Log {today}",
            "- AgentKB workflow scaffold initialized.\n",
            note_type="log",
            agent_writable=True,
            owner=owner,
        ),
        "_bases/Inbox.base": base_template("Inbox", "type, lifecycle, source, created, updated, needs_review"),
        "_bases/Projects.base": base_template("Projects", "project, status, updated, owner, context_pack"),
        "_bases/Knowledge.base": base_template("Knowledge", "type, domain, topic, lifecycle, updated, confidence"),
        "_bases/Promotion.base": base_template(
            "Promotion",
            "project, lifecycle, promotion_status, updated, needs_review",
        ),
        "_bases/Decisions.base": base_template(
            "Decisions",
            "id, project, status, created, updated, confidence, related",
        ),
        "_bases/Research.base": base_template("Research", "topic, source, confidence, updated, status, related"),
        "_bases/ContextPacks.base": base_template(
            "Context Packs",
            "project, updated, status, word_count, stale, source_notes",
        ),
        "_bases/OpenQuestions.base": base_template(
            "Open Questions",
            "question, project, status, owner, created, updated, related",
        ),
    }


def required_core_files(project: str, *, personal_first: bool = True):
    if not personal_first:
        return legacy_required_core_files(project)
    return [
        "AGENTS.md",
        "_system/kb-structure.md",
        "_system/routing-rules.md",
        "_system/metadata-schema.md",
        "_system/write-policy.md",
        "_system/promotion-policy.md",
        "_system/indexes/home.md",
        "_system/indexes/knowledge-index.md",
        "knowledge/index.md",
        "knowledge/log.md",
        "projects/_project-index.md",
        f"projects/{project}/overview.md",
        f"projects/{project}/current-state.md",
        f"projects/{project}/decisions.md",
        f"projects/{project}/open-questions.md",
        f"projects/{project}/context-pack.md",
        "decisions/adr-0001-use-markdown-as-canonical-kb.md",
        "decisions/adr-0002-use-context-pack.md",
        "playbooks/kb-ingest.md",
        "playbooks/kb-update.md",
        "playbooks/kb-lint.md",
        "playbooks/kb-reflect.md",
        "playbooks/kb-promote.md",
        "playbooks/kb-capture.md",
        "playbooks/kb-import.md",
        f"_agent/context-packs/{project}.md",
    ]


def legacy_required_core_files(project: str):
    return [
        "AGENTS.md",
        "wiki/index.md",
        "wiki/log.md",
        f"projects/{project}/overview.md",
        f"projects/{project}/current-state.md",
        f"projects/{project}/decisions.md",
        f"projects/{project}/open-questions.md",
        f"projects/{project}/context-pack.md",
        "decisions/adr-0001-use-markdown-as-canonical-kb.md",
        "decisions/adr-0002-use-context-pack.md",
        "playbooks/kb-ingest.md",
        "playbooks/kb-update.md",
        "playbooks/kb-lint.md",
        "playbooks/kb-reflect.md",
        "playbooks/kb-promote.md",
        f"context-packs/{project}.md",
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


def protocol_template(project: str, title: str, body: str):
    return note(
        title.lower().replace(" ", "-"),
        project,
        title,
        body,
        note_type="protocol",
        domain="agent",
        visibility="project-private",
        lifecycle="canonical",
        agent_readable=True,
        agent_writable=False,
        owner="system",
    )


def kb_structure_body(project: str):
    return f"""This vault is a personal-first AgentKB knowledge base.

## Directory Classes

- Control plane: `_system/`, `_agent/`, `_bases/`
- Knowledge content: `inbox/`, `calendar/`, `personal/`, `work/`,
  `projects/`, `knowledge/`, `promotion/`, `references/`, `assets/`,
  `archive/`
- Runtime state: `.agent-kb/`, `.obsidian/`

## Project Path

- Primary project context: `projects/{project}/context-pack.md`
- Project candidates: `projects/{project}/candidates/`

Codex must not scan the whole vault by default.
"""


def routing_rules_body(project: str):
    return f"""## Capture First

Preserve free-form input under `inbox/codex-captures/` before creating structured notes.

## Default Routes

- Private life, health, finance, ideas, reflections: `personal/`
- Work-private meetings, tasks, people, reflections: `work/`
- Reusable concepts, comparisons, tools: `knowledge/`
- Active project knowledge: `projects/{project}/`
- Project-useful extracts awaiting review: `projects/{project}/candidates/`
- Team-shareable material awaiting sanitization: `promotion/candidates/`

Write a routing receipt under `_agent/routing-receipts/` for capture/update/promotion actions.
"""


def metadata_schema_body():
    return """## Required Properties

```yaml
type:
project:
status:
confidence:
agent_readable:
domain:
visibility:
lifecycle:
source_raw:
team_shareable:
promotion_status:
needs_review:
```

`personal/` notes default to `visibility: private`, `agent_readable: false`, `team_shareable: false`.
"""


def write_policy_body(project: str):
    return f"""## Rules

- Preserve raw input before structured writing.
- Prefer append over overwrite.
- Never delete notes.
- Never rewrite archived notes.
- Never modify private notes unless explicitly requested.
- Put high-impact/uncertain project changes in `projects/{project}/proposed-changes/`.
- Review Git diff after every knowledge write.
"""


def promotion_policy_body(project: str):
    return f"""## Flow

```text
personal/work/knowledge note
  -> projects/{project}/candidates/
  -> promotion/candidates/
  -> promotion/sanitized/
  -> promotion/reviewed/
  -> promotion/exported/
```

Personal notes are not directly shareable. Promotion requires sanitization,
source links, human review before export.
"""


def capture_template(project: str, owner: str):
    body = """## Raw Input

Paste/preserve the original input here.

## Routing

- structured_output:
- confidence:
- needs_review:
"""
    return note(
        "capture-template",
        project,
        "Capture Template",
        body,
        note_type="template",
        domain="agent",
        visibility="project-private",
        lifecycle="canonical",
        owner=owner,
    )


def agents_template(project: str):
    return f"""# AGENTS.md

## Role

This repository is connected to the AgentKB personal-first Markdown knowledge base `{project}`.
Markdown is the canonical durable storage. Git is the audit layer.
Obsidian is an editor profile over Markdown. Codex is one agent adapter.

## Required Reading

Before starting a task:

1. Read `_system/kb-structure.md`.
2. Read `_system/routing-rules.md`.
3. Read `_system/metadata-schema.md`.
4. Read `_system/write-policy.md`.
5. Read `_system/promotion-policy.md`.
6. Read `projects/{project}/context-pack.md`.
7. Read `projects/{project}/current-state.md`.
8. Read `projects/{project}/decisions.md`.
9. Read `projects/{project}/open-questions.md`.

Do not scan the full Markdown vault unless explicitly requested.
If context is insufficient, read `_system/indexes/home.md` and
`_system/indexes/knowledge-index.md`, then select only task-relevant canonical notes.

## Knowledge Priority

Trust information in this order:

1. This `AGENTS.md`
2. `_system/` protocol files
3. Accepted ADRs plus decisions
4. `current-state.md`
5. `context-pack.md`
6. Task-relevant canonical notes
7. Retrieved memory snippets
8. Logs, inbox, draft notes

Do not read `personal/` or `archive/` unless the user explicitly authorizes it in the current task.

## After Work

After completing knowledge-bearing work:

1. Append a concise summary to `projects/{project}/logs/YYYY-MM-DD.md`.
2. Update `current-state.md` when durable project state changed.
3. Update `decisions.md` when a durable decision was made.
4. Update `open-questions.md` when uncertainty remains.
5. Refresh `context-pack.md` only when stale.
6. Write `_agent/routing-receipts/` when capture, routing, update, or promotion occurred.
7. Review `_agent/problem-signals/` and `projects/{project}/proposed-changes/problem-reflections/`
   with `kb-reflect` after failures, corrections, or review findings.
8. Review `git diff` before committing.

## Safety Rules

- Never delete notes.
- Never rename/move canonical notes without approval.
- Never overwrite archived notes.
- Never directly rewrite accepted ADRs.
- For large changes, write to `projects/{project}/proposed-changes/` first.
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
    domain: str = "agent",
    visibility: str = "project-private",
    lifecycle: str = "canonical",
    status: str = "active",
    confidence: str = "high",
    agent_readable: bool = True,
    agent_writable: bool = False,
    team_shareable: bool = False,
    promotion_status: str = "none",
    needs_review: bool = False,
    source_raw: str = "",
    owner: str = "owner",
):
    today = date.today().isoformat()
    return f"""---
id: {note_id}
type: {note_type}
domain: {domain}
project: {project}
topic:
visibility: {visibility}
lifecycle: {lifecycle}
status: {status}
created: {today}
updated: {today}
owner: {owner}
source: agent-kb
source_raw: {source_raw}
confidence: {confidence}
agent_readable: {str(agent_readable).lower()}
agent_writable: {str(agent_writable).lower()}
team_shareable: {str(team_shareable).lower()}
promotion_status: {promotion_status}
needs_review: {str(needs_review).lower()}
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
