---
name: kb-query
description: Use when answering from AgentKB Markdown without full-vault scans.
---

# KB Query

Use when answering a user question from an AgentKB Markdown knowledge base.

AgentKB keeps Markdown as the canonical storage format. Load the smallest sufficient context first, and make every write reviewable with Git diff.

## Context Order

1. Read the project `context-pack.md`.
2. Read `10-wiki/index.md` only if the context pack is insufficient.
3. Read the few canonical notes needed for the answer.
4. Read raw sources only for provenance or conflict resolution.

## Trust Priority

1. `AGENTS.md`
2. Accepted ADRs and decisions
3. `current-state.md`
4. `context-pack.md`
5. Canonical notes
6. Memory snippets
7. Logs, inbox, and drafts

Ignore stale or archived notes unless the user explicitly asks about them.

## Procedure

1. Answer with source-grounded synthesis.
2. Call out conflicts, low confidence, and stale context.
3. Decide whether the answer has long-term value.
4. If it does, propose or make a concise write-back to wiki, playbook, decision, or context-pack.
5. Review the Git diff for any write-back.
