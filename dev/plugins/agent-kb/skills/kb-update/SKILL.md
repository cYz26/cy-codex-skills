---
name: kb-update
description: Use when completed work needs durable AgentKB Markdown updates.
---

# KB Update

Use after development, research, design, maintenance, or review work that changes durable knowledge.

AgentKB keeps Markdown as the canonical storage format. Load the smallest sufficient context first, and make every write reviewable with Git diff.

## Context Order

1. Read the project `context-pack.md`.
2. Read `current-state.md`, `decisions.md`, and `open-questions.md`.
3. Read recent logs only as needed.

## Procedure

1. Append a concise task log entry.
2. Update `current-state.md` if durable project state changed.
3. Update `decisions.md` only for durable decisions.
4. Update `open-questions.md` when uncertainty remains.
5. Refresh `context-pack.md` only when it is stale or missing important current context.
6. Put high-impact or uncertain edits in `proposed-changes/`.
7. Review the Git diff before completion.

## Safety

Do not delete notes, rewrite accepted ADRs, edit archived notes, or store secrets.
