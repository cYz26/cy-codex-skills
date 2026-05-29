---
name: kb-promote
description: Use when repeated AgentKB lessons should become playbooks, ADRs, skills, or context packs.
---

# KB Promote

Use when a preference, workflow lesson, failure pattern, or recurring answer appears often enough to become durable knowledge.

AgentKB keeps Markdown as the canonical storage format. Load the smallest sufficient context first, and make every write reviewable with Git diff.

## Context Order

1. Read the project `context-pack.md`.
2. Read relevant logs, reflections, and open questions.
3. Read the target playbook, decision, skill, or proposed change only if promotion is justified.

## Promotion Paths

- One-time event: task log
- Repeated pattern: reflection or playbook
- Stable workflow: playbook or skill
- Project rule: `AGENTS.md` proposed change
- Architecture decision: ADR or decisions note
- Task-start context: context-pack refresh

## Procedure

1. Cite the repeated evidence.
2. Choose the smallest durable destination.
3. Avoid changing accepted ADRs directly.
4. Put high-impact changes in `proposed-changes/`.
5. Review the Git diff.
