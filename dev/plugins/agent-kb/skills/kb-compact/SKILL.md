---
name: kb-compact
description: Use when context-pack.md is stale, oversized, or missing recent AgentKB work.
---

# KB Compact

Use when `context-pack.md` is too long, stale, misses recent work, or repeatedly forces an agent to read extra notes.

AgentKB keeps Markdown as the canonical storage format. Load the smallest sufficient context first, and make every write reviewable with Git diff.

## Inputs

Read only:

1. Existing `context-pack.md`
2. `overview.md`
3. `current-state.md`
4. `decisions.md`
5. `open-questions.md`
6. Recent project logs
7. `10-wiki/index.md` if navigation has changed

## Procedure

1. Remove duplicate history and stale details.
2. Preserve current goal, state, constraints, key decisions, validation commands, and open questions.
3. Keep raw history in logs, not the context pack.
4. Write a concise replacement or a proposed change if uncertain.
5. Review the Git diff.

## Output

A short, current `context-pack.md` that is sufficient for task startup.
