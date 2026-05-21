# Context Fixer

<img src="./assets/context-fixer-icon.svg" alt="Context Fixer pixel icon" width="96" height="96">

Context Fixer diagnoses how Codex context is being used in a local project.
It reads local Codex session JSONL, `~/.codex/config.toml`, project `AGENTS.md`,
project-local `.codex/config.toml`, project-local skills, and workflow files,
then reports:

- context pressure from exact `token_count` telemetry;
- likely attribution from static files, dynamic tools, messages, tool arguments,
  and runtime tool output;
- compaction and checkpoint recommendations;
- chronological timeline analysis for peaks, latest valid usage, growth jumps,
  compactions, request events, and incomplete-session anomalies;
- explicit capability activity records for observed tool calls, request trace
  network activity, available request tools, and configured plugin/skill/MCP
  inventory;
- project AI configuration audit findings, including the effective project
  instruction chain.
- optional request trace attribution when a captured API request/response JSONL
  is provided.

The tool does not print prompt or chat content. Attribution is based on byte sizes
and approximate token estimates unless a Codex `token_count` event or request
trace `usage` object provides exact usage.

## Data Sources

Context Fixer uses a dual-source design:

- **Request Trace Parser**: preferred CLI path, using `--trace` input for
  already captured request/response JSONL. This gives higher-confidence API
  usage and request shape attribution without enabling proxy capture.
  Codex-focused claude-tap traces are supported when supplied as JSONL files.
- **Session Parser**: explicit fallback via `--session-only`, read-only,
  local-first parsing of Codex session JSONL/config/project files.

Proxy/tap capture is not enabled by this tool. If you use a separate tap/proxy,
scrub or redact the trace before passing it to `--trace`.

## Usage

```bash
cd tools/context-fixer
PYTHONPATH=src python3.11 -m context_fixer \
  --repo /path/to/repo \
  --trace .traces/codex-request.jsonl
```

When installed as a package, use:

```bash
context-fixer --repo /path/to/repo --trace .traces/codex-request.jsonl
```

JSON output:

```bash
PYTHONPATH=src python3.11 -m context_fixer \
  --repo /path/to/repo \
  --trace .traces/codex-request.jsonl \
  --json
```

Static web report:

```bash
PYTHONPATH=src python3.11 -m context_fixer \
  --repo /path/to/repo \
  --trace .traces/codex-request.jsonl \
  --html report.html
```

Analyze a request trace:

```bash
PYTHONPATH=src python3.11 -m context_fixer \
  --repo /path/to/repo \
  --trace .traces/codex-request.jsonl \
  --html report.html
```

Analyze a Codex trace captured by claude-tap:

```bash
claude-tap --tap-client codex

PYTHONPATH=src python3.11 -m context_fixer \
  --repo /path/to/repo \
  --trace /path/to/trace_*.jsonl \
  --html report.html
```

Context Fixer does not install, launch, or vendor claude-tap. claude-tap remains
the capture layer; Context Fixer imports the captured Codex trace and reports
sanitized attribution for Responses instructions, input messages, tool schemas,
tool results, usage, and transport metadata.

When the CLI is run without `--trace`, Context Fixer exits with Codex request
trace setup guidance instead of silently producing a lower-confidence report.
Use `--session-only` to explicitly analyze session logs without request trace
evidence. In `--session-only` mode, the first run for a repository adds a
one-time recommendation for optional Codex request trace setup. If `claude-tap`
is already on `PATH`, the recommendation shows the capture command. If it is
missing, the recommendation shows an install command. This first-run marker is
stored in the user cache (`CONTEXT_FIXER_CACHE_HOME`, `$XDG_CACHE_HOME`, or
`~/.cache/context-fixer`) and is not written into the audited repository.

Explicitly analyze session logs only:

```bash
PYTHONPATH=src python3.11 -m context_fixer \
  --repo /path/to/repo \
  --session-only
```

Analyze a specific session without request trace evidence:

```bash
PYTHONPATH=src python3.11 -m context_fixer \
  --repo /path/to/repo \
  --session-only \
  --session ~/.codex/sessions/2026/05/18/rollout-example.jsonl
```

Analyze a nested working directory for `AGENTS.md` discovery:

```bash
PYTHONPATH=src python3.11 -m context_fixer \
  --repo /path/to/repo \
  --session-only \
  --cwd /path/to/repo/packages/api
```

CI guard:

```bash
PYTHONPATH=src python3.11 -m context_fixer --repo . --trace .traces/codex-request.jsonl --fail-on-severity high
```

`codex-context-lens` remains as a compatibility console script for older local
automation.

## Name

The English product name is **Context Fixer**. The Chinese working idea
「清道夫」is kept as naming background: a professional behind-the-scenes fixer who
handles the dirty work of context, traces, logs, and configuration so the visible
AI workflow can remain polished.

The icon assets in `assets/` are original pixel-art marks for Context Fixer:
a professional fixer figure, terminal-like context blocks, and cleanup/tool
elements. They intentionally avoid protected likenesses, character names, and
franchise-specific marks.

## Report Shape

- `diagnosis`: exact token telemetry, context percentage, context headroom,
  cache hit ratio, source of truth, and compaction count.
- `data_sources`: Session Parser and Request Trace availability, file counts,
  event counts, and precision.
- `context_policy`: green/yellow/orange/red policy status, compact threshold,
  hard-warning threshold, and tool-output guidance.
- `timeline`: sanitized chronological events, peak usage, latest valid non-zero
  usage, growth jumps, compaction events, request trace events, and anomalies
  such as zero-usage or incomplete sessions.
- `activity`: sanitized capability activity, including observed session tool
  calls/results, request trace activity categories, available request/session
  tools, and configured plugins, skills, and MCP servers. Configured inventory
  is reported separately from observed calls.
- `attribution`: largest estimated contributors across project files, global
  config, skill metadata, session base instructions, dynamic tools,
  conversation-message sizes, tool arguments, tool output, request messages,
  request tool definitions, and request tool results.
- `config_audit`: enabled global plugins, global skills, MCP servers, project
  instruction files, project `.codex/config.toml`, project-local skills,
  workflow signals, and the discovered instruction chain.
- `compression`: prioritized recommendations for compaction, checkpointing,
  slimming instructions, and reducing large tool outputs.
- `html`: a self-contained dashboard with summary cards, contributor bars,
  timeline, capability activity, data sources, policy status, recommendations,
  findings, instruction chain, inventory, and sanitized JSON.

Sensitive prompt, message, tool argument, and tool output bodies are never
printed by the text or HTML renderer.

## Development

```bash
PYTHONPATH=src /opt/homebrew/bin/python3.11 -m unittest discover -s tests -v
```
