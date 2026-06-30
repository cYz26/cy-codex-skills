# Crawl4AI

Reusable Codex skill for Crawl4AI-backed web page intake.

Use this plugin when live HTTP(S) pages should be fetched, rendered, and turned
into Markdown for review, summarization, or downstream knowledge-base import.
It keeps Crawl4AI separate from document converters such as MarkItDown:
Crawl4AI is for live web pages; MarkItDown is for local files, Office
documents, PDFs, and downloaded artifacts.

## Runtime

The bundled `crawl4ai_fetch.py` helper looks for Crawl4AI in this order:

1. `CRAWL4AI_CMD`
2. `AGENT_KB_CRAWL4AI_CMD`
3. `~/.codex/crawl4ai-venv/bin/crwl`
4. `~/.codex/agent-kb/crawl4ai-venv/bin/crwl`
5. `crwl` on `PATH`

Install a dedicated runtime when needed:

```bash
/opt/homebrew/bin/python3.12 -m venv ~/.codex/crawl4ai-venv
~/.codex/crawl4ai-venv/bin/python -m pip install -U crawl4ai
~/.codex/crawl4ai-venv/bin/crawl4ai-setup
~/.codex/crawl4ai-venv/bin/crawl4ai-doctor
```

The plugin does not install Crawl4AI, browsers, or Docker automatically.
