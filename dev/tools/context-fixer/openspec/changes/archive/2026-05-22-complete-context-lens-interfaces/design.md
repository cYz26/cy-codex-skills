## Context

Context Fixer is a Python CLI with a stable legacy flag interface:
`context-fixer --repo <repo> [--trace ...|--session-only] [--json|--html]`.
The 2026-05-21 requirements describe a broader Codex Context Lens interface:
audit, sessions, inspect, trace import, recommend, report, doctor, Markdown/JSON
outputs, hook collector support, and skill/plugin workflow integration.

The project direction is to keep the existing Python package and Context Fixer
name. The new work should therefore add an interface layer over existing
`analyze_context`, `parse_session`, `parse_trace`, and render helpers rather
than replacing the analyzer.

## Goals / Non-Goals

**Goals:**

- Preserve the current legacy CLI.
- Add subcommands matching the supplied technical solution.
- Add Markdown output alongside text, JSON, and HTML.
- Add a local hook collector that can be called by Codex hooks and records
  sanitized event metadata to cache.
- Update bundled skill guidance to the new command surface.
- Add tests before implementation for public behavior.

**Non-Goals:**

- Do not implement TypeScript/Node, SQLite persistence, Tauri, or a React app.
- Do not run or install claude-tap.
- Do not automatically modify `AGENTS.md`, Codex profiles, MCP settings, hooks,
  or project files.
- Do not persist raw prompts, tool arguments, command output, file contents, or
  trace payload bodies.

## Decisions

1. **Use argparse subcommands with a legacy fallback.**

   `context_fixer.cli.main()` will detect whether the first argument is a known
   subcommand. If not, it will parse the existing legacy flags. This keeps
   backward compatibility while allowing document-aligned commands.

   Alternative considered: create a second console script only. Rejected because
   users should not need to learn two tools.

2. **Keep `analyze_context` as the shared report generator.**

   Subcommands will call `analyze_context` with different input defaults:
   `audit` and `report` analyze a project, `inspect` targets a session,
   `trace import` supplies traces, and `recommend` filters report
   recommendations. `sessions` uses `discover_sessions` and `parse_session` for
   lightweight listing.

3. **Add Markdown as a renderer, not a separate report schema.**

   `render_markdown(report)` will render sanitized report data in Markdown
   tables/lists. JSON remains the machine-readable source of truth.

4. **Implement hook collection as append-only sanitized JSONL.**

   A new module, tentatively `context_fixer.hook`, will read hook event JSON
   from stdin or `--input`, compute estimated size/tokens/hash for selected
   fields, and append a sanitized record to
   `$CONTEXT_FIXER_CACHE_HOME/hooks/events.jsonl` or the normal user cache. The
   hook command prints a short status line and never exits non-zero for malformed
   optional fields unless file writing itself fails.

5. **Skill integration is a repo artifact.**

   The existing `skills/context-fixer/SKILL.md` will be updated to prefer the
   new CLI commands and explicitly mention request traces, session-only mode,
   Markdown/HTML outputs, recommendations, and hook collection.

## Risks / Trade-offs

- [Risk] Subcommands may break legacy flag parsing. -> Mitigation: keep the
  legacy parser path and test both invocation styles.
- [Risk] Hook payloads can contain sensitive bodies. -> Mitigation: store only
  size, token estimate, hash, tool name, command preview, status, cwd/session
  metadata, and source field names; never store raw output or arguments.
- [Risk] `sessions` listing can be expensive on very large Codex homes. ->
  Mitigation: respect `--top`/`--latest-sessions` limits and parse only summary
  metadata for listed files.
- [Risk] Markdown can drift from JSON. -> Mitigation: render from the same
  sanitized report object.

## Migration Plan

1. Add CLI/subcommand and hook tests first.
2. Add Markdown renderer.
3. Refactor CLI parsing to support legacy and subcommand modes.
4. Add hook collector module and console script.
5. Update README and skill documentation.
6. Run full unittest, py_compile, OpenSpec validation, and CLI smoke commands.
