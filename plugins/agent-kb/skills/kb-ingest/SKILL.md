---
name: kb-ingest
description: Use when raw AgentKB sources need durable Markdown notes.
---

# KB Ingest

Use when new material lands in `inbox/`, `raw/`, or `references/` and should become durable, agent-readable knowledge.

AgentKB keeps Markdown as the canonical storage format. Load the smallest sufficient context first, and make every write reviewable with Git diff.

## Context Order

1. Read the relevant project `context-pack.md`.
2. Read `_system/routing-rules.md` and `_system/metadata-schema.md`.
3. Read `_system/indexes/knowledge-index.md`.
3. Read only the raw source and task-relevant canonical notes.

Do not scan the full vault.
Do not read `personal/` or `archive/` unless the user explicitly authorizes it.

## Procedure

1. Preserve raw sources; do not rewrite or delete them.
2. Create or update a source summary with frontmatter.
3. Extract durable facts, concepts, entities, comparisons, and open questions.
4. Update `_system/indexes/knowledge-index.md` when navigation changes.
5. Append a concise entry to `knowledge/log.md` or the project log.
6. Put uncertain or high-impact edits in `proposed-changes/`.
7. Review the final Git diff before reporting completion.

## Output

- Source summary note
- Updated canonical notes or proposed changes
- Log entry
- Open questions when confidence is not high
