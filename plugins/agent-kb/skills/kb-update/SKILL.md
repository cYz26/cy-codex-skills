---
name: kb-update
description: Use when completed work needs durable AgentKB Markdown updates.
---

# KB Update

Use after development, research, design, maintenance, or review work that changes durable knowledge.

AgentKB keeps Markdown as the canonical storage format. Load the smallest sufficient context first, and make every write reviewable with Git diff.

## Context Order

1. Read the project `context-pack.md`.
2. Read `_system/write-policy.md` and `_system/promotion-policy.md`.
3. Read `current-state.md`, `decisions.md`, and `open-questions.md`.
4. Read recent logs only as needed.

Do not read `personal/` or `archive/` unless the user explicitly authorizes it.

## Procedure

1. Append a concise task log entry.
2. Update `current-state.md` if durable project state changed.
3. Update `decisions.md` only for durable decisions.
4. Update `open-questions.md` when uncertainty remains.
5. Refresh `context-pack.md` only when it is stale or missing important current context.
6. Move project-useful personal/work extracts into `projects/<project>/candidates/`.
7. Put high-impact or uncertain edits in `proposed-changes/`.
8. Write a routing receipt in `_agent/routing-receipts/` when routing or promotion happened.
9. Review the Git diff before completion.

## Safety

Do not delete notes, rewrite accepted ADRs, edit archived notes, or store secrets.
