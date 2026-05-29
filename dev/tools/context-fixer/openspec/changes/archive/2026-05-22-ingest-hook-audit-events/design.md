## Context

`context-fixer-hook` writes append-only sanitized JSONL containing tool name,
command preview, byte counts, estimated tokens, hashes, status, cwd, and source
field names. This change lets audits use those records when explicitly supplied
or produced by a managed collection run.

## Goals / Non-Goals

Goals:

- Parse sanitized hook event JSONL.
- Attribute hook tool input and output sizes to session growth.
- Add capability activity evidence for hook-collected tools.
- Preserve repo scoping by default.

Non-goals:

- Do not parse raw Codex hook payload bodies as normal input.
- Do not silently ingest unrelated global cache records.
- Do not install hooks automatically.

## Decisions

1. **Dedicated parser.** `hook_events.py` returns stats with contributors and
   activity events matching existing analyzer conventions.
2. **Explicit input.** `--hook-events PATH` is the CLI input. Managed collection
   may pass its generated path internally.
3. **Repo scoping.** Records with `cwd` outside the target repo are ignored by
   default. `--include-external-hook-events` is an explicit override.
4. **New categories.** Hook input and output are classified as
   `hook_tool_input` and `hook_tool_output`.

## Risks / Trade-offs

- Old or malformed hook records may exist in cache. Mitigation: skip invalid
  records and record parser findings.
- Hashes can identify repeated content. Mitigation: keep short hashes only and
  never render raw values.

## Migration Plan

1. Add parser and CLI tests.
2. Implement hook event parser.
3. Wire analyzer/CLI.
4. Update docs and run verification.
