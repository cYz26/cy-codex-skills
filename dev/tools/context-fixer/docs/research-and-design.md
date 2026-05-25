# Context Fixer Research and Design

## Research Inputs

- OpenAI Codex documents project guidance through `AGENTS.md`, so the tool treats
  project instruction files as first-class static context sources.
- Codex discovers global and project instructions through `AGENTS.override.md`,
  `AGENTS.md`, and configured fallback names, then stops adding project
  instruction content once `project_doc_max_bytes` is reached. See
  https://developers.openai.com/codex/guides/agents-md.
- Codex CLI configuration is TOML-based; user-level config lives in
  `~/.codex/config.toml`, and trusted projects may add `.codex/config.toml`
  layers. See https://developers.openai.com/codex/config-reference.
- Codex customization has multiple context/tool layers: `AGENTS.md`, memories,
  skills, MCP, and subagents. See
  https://developers.openai.com/codex/concepts/customization.
- Codex skills use progressive disclosure: metadata is initially available,
  while full `SKILL.md` instructions are loaded only when needed. The tool
  therefore treats skill metadata/inventory pressure separately from full skill
  file size. See https://developers.openai.com/codex/skills.
- OpenAI usage telemetry includes input, cached input, output, reasoning output,
  and total token counts. The tool uses Codex local `token_count` events as exact
  pressure data and labels every other contribution as an estimate.
- Local Codex session JSONL contains `session_meta`, `turn_context`, `event_msg`,
  `response_item`, and `compacted` records. Useful context signals include
  `model_context_window`, `token_count`, `context_compacted`, `base_instructions`,
  `dynamic_tools`, function calls, and tool outputs.
- The existing `codex-project-orchestrator` plugin already has a narrower
  `audit_context_tools.py` script for global plugins and skills. This project
  generalizes that idea into a standalone context forensics tool.

## Goals

1. Diagnose current and recent context pressure from exact Codex telemetry.
2. Fuse the default Session Parser source with optional Request Trace JSONL
   evidence when available.
3. Attribute likely context contributors without exposing prompt or conversation
   content.
4. Recommend compaction boundaries, checkpointing, prompt slimming, and safer tool
   output practices.
5. Audit project AI configuration, including `AGENTS.md`, project-local skills,
   global skills, enabled plugins, MCP servers, and workflow files.

## Non-Goals

- It does not call OpenAI APIs.
- It does not mutate `~/.codex` or project files.
- It does not claim exact per-source token attribution unless Codex telemetry
  provides the number directly.
- It does not run a proxy/tap capture process. Request traces are opt-in files
  supplied by the user.

## Architecture

The implementation is a small standard-library Python CLI:

- `session.py` discovers and parses local Codex session JSONL, extracting exact
  token telemetry and estimated runtime contributors. It aggregates message,
  tool-argument, and tool-output sizes without returning their bodies.
- `trace.py` parses already captured request/response JSONL. It extracts request
  messages, tool definitions, tool results, endpoint/model metadata, and API
  `usage` objects while omitting headers and raw prompt bodies from reports.
- `static_sources.py` scans project and Codex-home files that commonly affect
  context. It also reconstructs the likely project instruction chain for a
  target `--cwd` using override, standard, and fallback instruction names.
- `analyzer.py` combines telemetry, attribution, configuration audit, and
  recommendations. If request trace usage is available, it is the highest
  priority usage source; otherwise Codex session `token_count` is used.
- `render.py` prints a readable text report and renders a self-contained HTML
  dashboard, while `cli.py` provides JSON and `--html` output for downstream
  tooling.

## Dual Source Fusion

Priority order for usage and prompt-shape evidence:

1. Request trace `usage` object and request payload shape.
2. Session JSONL `token_count`, `session_meta`, `turn_context`, and tool events.
3. Static project/global configuration scans.

The report records `data_sources` so consumers can tell whether request-trace
evidence was available. Request trace bodies are classified by role and size only:
system/developer/user/assistant messages, tool results, and tool definitions.

## Context Policy

The default `standard_coding` policy uses:

- green: below 60% of the effective context window;
- yellow: 60%-70%, prepare checkpoint and limit long logs;
- orange: 70%-80%, compact soon after checkpoint;
- red: 80%+, compact before substantial new work.

The policy block includes the recommended compact token band and a default
per-tool-output limit.

## Severity Model

- `critical`: peak input tokens reached at least 90% of the model context window.
- `high`: peak input tokens reached at least 75%.
- `medium`: peak input tokens reached at least 55%.
- `low`: below 55% or no telemetry found.

## Recommendation Rules

- Critical context pressure triggers a P0 compact/checkpoint recommendation.
- High context pressure triggers a P1 compaction-boundary recommendation.
- Large runtime tool outputs trigger recommendations to save outputs to files and
  read focused excerpts.
- Large `AGENTS.md` files trigger recommendations to keep only routing and rules
  in context and move examples or long procedures to linked docs.
- Global plugins or large skill inventories trigger a project-local activation
  audit suggestion. Skill attribution is based on metadata, not full file bodies,
  unless a later session event shows the full text was actually loaded.
- Existing compaction events trigger a checkpoint recommendation so decisions
  and verification evidence are durable outside the compressed chat history.
- Instruction chains that exceed `project_doc_max_bytes` trigger a split/slim
  recommendation.

## Privacy

The text and HTML renderers never print prompt, message, tool argument, or
tool-output bodies. JSON output contains paths, sizes, token estimates, labels,
and sanitized inventory keys only.
