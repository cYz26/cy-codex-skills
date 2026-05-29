---
name: kb-reflect
description: Use when failures, corrections, or review findings should become AgentKB knowledge.
---

# KB Reflect

Use after failures, user corrections, review findings, repeated tool mistakes, or context misses.

AgentKB keeps Markdown as the canonical storage format. Load the smallest sufficient context first, and make every write reviewable with Git diff.

## Context Order

1. Read the project `context-pack.md`.
2. Read the relevant task log and open questions.
3. Read only the notes needed to understand the failure.

## Procedure

1. Describe what failed and why in a concise log entry.
2. Identify whether the issue is a one-time mistake, repeated pattern, missing context, unclear rule, or missing validation.
3. Decide whether to update `open-questions.md`, a playbook, `AGENTS.md` proposed change, eval case, or context-pack.
4. Keep low-confidence reflections in `proposed-changes/`.
5. Review the Git diff.

## Promotion Rule

One incident goes to a log. Repeated, stable lessons can be promoted by `kb-promote`.
