---
name: kb-capture
description: Use when free-form input should enter the personal-first AgentKB vault.
---

# KB Capture

Use when the user gives loose notes, ideas, work observations, project context, or reusable knowledge that should be preserved and routed.

AgentKB keeps Markdown as the canonical storage format. Load the smallest sufficient context first, and make every write reviewable with Git diff.

## Required Context

1. Read `AGENTS.md`.
2. Read `_system/kb-structure.md`.
3. Read `_system/routing-rules.md`.
4. Read `_system/metadata-schema.md`.
5. Read `_system/write-policy.md`.
6. Read `_system/promotion-policy.md`.
7. Read project `context-pack.md` only when the capture references a project.

Do not read `personal/` or `archive/` unless the user explicitly authorizes it in the current request.

## Procedure

1. Preserve the original input under `inbox/codex-captures/YYYY-MM-DD-HHmm-<slug>.md`.
2. Classify the capture as personal, work, project, reusable knowledge, reference, or promotion candidate.
3. Create or append the structured note in the target directory.
4. Put project-useful extracts in `projects/<project>/candidates/` when they need review before becoming project context.
5. Put team-shareable material in `promotion/candidates/` before sanitization and review.
6. Write `_agent/routing-receipts/YYYY-MM-DD-HHmm-<slug>.md` with source path, output path, classification, confidence, and review state.
7. Review the Git diff.

## Output

- Raw capture
- Structured note or candidate
- Routing receipt
- Review marker when confidence is low
