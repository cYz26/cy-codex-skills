---
name: kb-lint
description: Use when auditing AgentKB frontmatter, context packs, and raw-source freshness.
---

# KB Lint

Use for knowledge-base health checks.

AgentKB keeps Markdown as the canonical storage format. Load the smallest sufficient context first, and make every write reviewable with Git diff.

## Checks

- Missing frontmatter on formal notes
- Missing required frontmatter fields
- Missing core project files
- Oversized or stale `context-pack.md`
- Raw sources that have not been processed
- Index or logs that need review

## Procedure

1. Run `python3 scripts/kb_lint.py --vault <vault> --project <project> --write-report --json` when available.
2. Treat the generated report as review guidance, not an automatic repair.
3. Put risky changes in `proposed-changes/`.
4. Apply only scoped, source-grounded fixes.
5. Review the Git diff before completion.

## Safety

Do not auto-delete, rename, move, or rewrite canonical notes.
