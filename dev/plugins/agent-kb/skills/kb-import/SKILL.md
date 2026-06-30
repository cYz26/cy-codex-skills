---
name: kb-import
description: Use when local files, PDFs, office documents, URLs, Feishu/Lark docs, or Drive folders should enter AgentKB source intake.
---

# KB Import

Use when source material should be scanned, preserved, converted to Markdown,
and prepared for `kb-ingest`.

AgentKB keeps Markdown as the canonical durable store. Load the smallest
sufficient context first, preserve raw sources, and make every write reviewable
with Git diff.

## Required Context

1. Read the project `context-pack.md`.
2. Read `_system/routing-rules.md` and `_system/metadata-schema.md`.
3. Read `_system/write-policy.md`.

Do not read `personal/` or `archive/` unless the user explicitly authorizes it.

## Procedure

1. Preserve the user-provided path, URL, Feishu/Lark link, or Drive folder
   request before importing.
2. Run dry-run first:
   `python3 scripts/kb_import.py --vault <vault> --project <project> --source <source> --dry-run --json`.
3. Review imports, skips, duplicates, Crawl4AI URL-fetch status, MarkItDown
   status, and Feishu/Lark read commands.
4. Apply only after the plan is scoped:
   `python3 scripts/kb_import.py --vault <vault> --project <project> --source <source> --apply --json`.
5. Hand source summaries and extracted Markdown under `_agent/source-intake/`
   to `kb-ingest`.
6. Run `kb-lint` and review the Git diff.

## MarkItDown

Microsoft MarkItDown is optional but important for broad PDF, Office, HTML, and
archive coverage. It currently requires Python 3.10+; when `python3` is older,
install a dedicated runtime:
`/opt/homebrew/bin/python3.12 -m venv ~/.codex/agent-kb/markitdown-venv`
then
`~/.codex/agent-kb/markitdown-venv/bin/python -m pip install "markitdown[pdf,docx,xlsx,pptx]"`.
AgentKB auto-detects that venv's `markitdown` command, PATH `markitdown`, or
`AGENT_KB_MARKITDOWN_CMD`.

Do not pass untrusted paths or URLs directly to conversion tools; source intake
must enforce path, protocol, and size boundaries.

## Crawl4AI

Crawl4AI is optional and used only for generic HTTP(S) URL sources. The
standalone `crawl4ai` skill owns general Crawl4AI workflows; AgentKB consumes
the same runtime convention when the crawled result should enter a vault. It
turns web pages into reviewable Markdown before AgentKB writes raw URL
metadata, extracted Markdown, receipts, registry records, and source summaries.
Install a dedicated runtime when URL apply mode should fetch pages:
`/opt/homebrew/bin/python3.12 -m venv ~/.codex/crawl4ai-venv`
then
`~/.codex/crawl4ai-venv/bin/python -m pip install -U crawl4ai`
and run
`~/.codex/crawl4ai-venv/bin/crawl4ai-setup`
plus
`~/.codex/crawl4ai-venv/bin/crawl4ai-doctor`.
AgentKB auto-detects `CRAWL4AI_CMD`, `AGENT_KB_CRAWL4AI_CMD`,
`~/.codex/crawl4ai-venv/bin/crwl`,
`~/.codex/agent-kb/crawl4ai-venv/bin/crwl`, or PATH `crwl`.

Crawl4AI is not a replacement for MarkItDown. Use Crawl4AI for live web pages;
use MarkItDown for local files, downloaded documents, archives, Office files,
PDFs, and attachments.

## Feishu/Lark

Prefer native read-only `lark-cli` Markdown fetch/export paths for Feishu/Lark
cloud documents. Use document conversion only for downloaded or exported files
and attachments.

## Output

Preserved raw source, extracted Markdown when possible, source summary, source
registry entry, receipt, and `kb-ingest` handoff target.
