---
name: crawl4ai
description: Use when web pages or HTTP(S) URLs should be crawled, browser-rendered, or converted into Markdown with Crawl4AI for research, source intake, summarization, review, or downstream knowledge-base workflows; use MarkItDown instead for local PDFs, Office files, archives, downloaded documents, and attachments.
---

# Crawl4AI

## Overview

Crawl live web pages with Crawl4AI and return reviewable Markdown. Keep this
skill focused on HTTP(S) pages; use document-oriented converters for local
files and downloaded artifacts.

## Workflow

1. Confirm the input is a user-provided URL or a narrowly scoped set of URLs.
2. Check whether Crawl4AI is available before promising extraction.
3. Use `scripts/crawl4ai_fetch.py` for repeatable command execution and JSON
   reporting when a reusable artifact is useful.
4. Preserve the original URL, fetched Markdown, command status, and any skipped
   reason in the target workflow.
5. Use AgentKB `kb-import` only when the user wants the result stored in an
   AgentKB vault; otherwise keep the output in the current task's artifact path.

## Runtime Detection

The helper resolves Crawl4AI in this order:

1. `CRAWL4AI_CMD`
2. `AGENT_KB_CRAWL4AI_CMD`
3. `~/.codex/crawl4ai-venv/bin/crwl`
4. `~/.codex/agent-kb/crawl4ai-venv/bin/crwl`
5. `crwl` on `PATH`

Install a dedicated runtime when Crawl4AI is missing:

```bash
/opt/homebrew/bin/python3.12 -m venv ~/.codex/crawl4ai-venv
~/.codex/crawl4ai-venv/bin/python -m pip install -U crawl4ai
~/.codex/crawl4ai-venv/bin/crawl4ai-setup
~/.codex/crawl4ai-venv/bin/crawl4ai-doctor
```

Do not install dependencies automatically unless the user asked for setup. Do
not configure a global MCP server without separately validating Codex transport
compatibility.

## Commands

Check availability:

```bash
python3 scripts/crawl4ai_fetch.py --check --json
```

Fetch Markdown:

```bash
python3 scripts/crawl4ai_fetch.py --url https://example.com --json
```

Write only the `content` field into downstream Markdown files unless the target
workflow asks for a JSON receipt.

## Boundaries

- Use Crawl4AI for live web pages where JavaScript rendering, cleanup, and
  Markdown generation are useful.
- Use MarkItDown for local PDFs, Office files, archives, attachments, and
  downloaded documents.
- Do not broaden a single URL request into site crawling unless the user gives
  an explicit scope and limit.
- Avoid authenticated, private, or internal URLs unless the user has provided
  clear authorization and the output destination is appropriate.
- Treat failed, empty, or unavailable Crawl4AI output as a skipped/degraded
  state rather than inventing content.

## AgentKB Integration

When the user wants crawled pages to enter an AgentKB vault, use `kb-import`.
AgentKB consumes the same command conventions and records raw URL metadata,
extracted Markdown, source summaries, receipts, and registry entries. This
skill remains the reusable Crawl4AI guidance for non-AgentKB contexts.
