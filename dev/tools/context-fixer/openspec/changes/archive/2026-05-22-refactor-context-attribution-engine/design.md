## Context

Context Fixer is already a Python CLI with local-first static scanning, Codex
session JSONL parsing, optional request trace parsing, timeline analysis,
capability activity reporting, text/JSON output, and a self-contained HTML
dashboard. The current code grew through additive feature changes, so source
types, budget sections, top contributors, and recommendations are partly
implicit in `analyzer.py` and parser-specific labels.

The supplied 2026-05-21 requirements and technical solution describe the same
product direction with a clearer Context Lens model: baseline context,
session-growth context, turn-level deltas, request-level composition, top
offenders, and budget-driven recommendations. The implementation should align
with that model while preserving the existing Python package, `context-fixer`
CLI, `codex-context-lens` compatibility alias, sanitized reporting, and no-new
dependency posture.

## Goals / Non-Goals

**Goals:**

- Make the report expose explicit Context Lens MVP sections: `baseline`,
  `session_growth`, `turn_deltas`, `request_composition`, `top_offenders`, and
  recommendations.
- Normalize parser output into stable source categories so report consumers do
  not depend on historical free-form labels.
- Keep request trace attribution preferred when supplied, while preserving
  explicit `--session-only` behavior.
- Keep all reports sanitized and local-first.
- Improve tests around the new budget sections before changing production code.

**Non-Goals:**

- Do not rewrite the tool in TypeScript or introduce a database.
- Do not add live proxy/tap capture, hook installation, or automatic Codex
  configuration changes.
- Do not remove existing report fields in this change.
- Do not archive previous completed OpenSpec changes.

## Decisions

1. **Add a budget model beside existing report fields.**

   The analyzer will continue returning existing keys (`diagnosis`, `timeline`,
   `activity`, `attribution`, `config_audit`, and `compression`) and will add a
   `budget` section that maps the same evidence into the Context Lens
   vocabulary. This avoids a breaking report schema change while making the new
   requirements first-class.

   Alternative considered: replace `attribution` with `budget`. Rejected
   because current tests and local automation may already consume
   `attribution.top_contributors`.

2. **Normalize source categories in a small dedicated module.**

   Add a focused module, tentatively `src/context_fixer/budget.py`, for category
   mapping, section aggregation, top offender ranking, and budget recommendation
   evidence. Parsers remain responsible for extracting sanitized contributors;
   the budget module is responsible for turning contributors/events into the
   product model.

   Alternative considered: continue expanding `analyzer.py`. Rejected because
   the file is already the integration point for diagnosis, activity, timeline,
   and recommendations.

3. **Classify session events more explicitly without storing bodies.**

   `session.py` will keep adding sanitized `Contributor` records, but source
   kinds should distinguish user history, assistant history, bash output,
   generic tool output, file content, patch/diff content, web/search results,
   MCP output, tool arguments, base instructions, and developer instructions
   where the JSONL evidence makes that distinction possible.

   Alternative considered: infer categories only from labels in the analyzer.
   Rejected because stable categories are easier to test when attached close to
   parsing.

4. **Treat static sources as baseline budget inputs.**

   `static_sources.py` will classify global/project/nested instruction files,
   skill metadata, MCP inventory, Codex config, hooks, workflow files, and
   legacy AI files into baseline categories. MCP schema token estimates remain
   unknown without trace evidence, but configured MCP servers are reported as
   inventory and risk signals.

   Alternative considered: only count file byte sizes. Rejected because the
   requirements explicitly ask for enabled MCP and hook risk even when schemas
   are not available.

5. **Request trace composition remains opt-in and sanitized.**

   `trace.py` will keep parsing supplied traces only. The budget model will
   summarize instructions/system-like content, messages by role, tool
   definitions, tool results, exact usage, and metadata into
   `request_composition`.

   Alternative considered: add capture commands. Rejected because the current
   product boundary says claude-tap remains the external capture layer.

6. **Render new sections without removing old sections.**

   Text and HTML reports will include the new budget model while retaining
   existing sections. This gives users the requested Context Lens vocabulary and
   lowers compatibility risk.

## Risks / Trade-offs

- [Risk] Codex JSONL shapes vary across versions. -> Mitigation: keep tolerant
  field parsing, classify unknown tools as generic tool output, and keep raw
  sensitive bodies out of reports.
- [Risk] Token estimates are approximate. -> Mitigation: continue labeling
  estimated contributors and prefer exact request/session usage when available.
- [Risk] The new budget section duplicates some existing attribution data. ->
  Mitigation: treat this as a compatibility bridge; tests will assert that old
  and new sections are both present.
- [Risk] Refactor touches several modules. -> Mitigation: use TDD task by task,
  add tests for report shape before implementation, and run the full unittest
  suite after each meaningful step.
- [Risk] Unarchived completed changes remain in `openspec/changes`. ->
  Mitigation: leave them untouched; this change records its own scope and
  verification evidence.

## Migration Plan

1. Add tests for the new budget report sections using existing fixtures.
2. Add `budget.py` and wire it into `analyzer.py` without deleting existing
   report keys.
3. Improve parser category output only where tests require stable attribution.
4. Update renderers and README to describe the Context Lens budget sections.
5. Run full unit tests and CLI smoke checks.

Rollback is straightforward: revert this change's files. No persisted schema,
external service, or configuration migration is introduced.

## Open Questions

None for this implementation pass. Future changes can consider a dashboard
backend, hook collector, SQLite persistence, or TypeScript dashboard sharing
after the Python CLI budget model is stable.
