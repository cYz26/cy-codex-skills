# Triage And Promotion

## Overall loop
1. Capture raw learnings in `docs/work/<task>/learning-log.md`
2. Move entries from `pending` to `triaged`, `promoted`, or `dismissed`
3. Promote repo-local durable outcomes into `AGENTS.md` or `knowledge/`
4. Promote cross-task reusable workflows into `$CODEX_HOME/memories/durable-knowledge/skill-candidates/`
5. Let the 72-hour audit catch anything that stayed stale or unprocessed

## Status meanings
- `pending`: newly captured and not yet confirmed
- `triaged`: confirmed, categorized, and mapped to a durable target
- `promoted`: durable docs or candidate records were updated
- `dismissed`: not durable, duplicate, or superseded

## Promotion map
- repo rule or workflow policy -> `AGENTS.md`
- implementation snapshot -> `knowledge/project/current-state.md`
- pitfalls or wrong-fix pattern -> repo pitfalls doc
- reusable cross-task workflow -> `$CODEX_HOME/memories/durable-knowledge/skill-candidates/`

## Architecture notes
- `learning-log.md` is the raw event store; it is allowed to be noisy.
- `status.md` is the operator summary; keep it short and derived.
- `meta.yaml` is task-close bookkeeping, not the full event history.
- `AGENTS.md` and `knowledge/` are stable outputs, never the first write target for a raw learning.
- candidate memory is the cross-repo aggregation layer, not a replacement for repo-local knowledge.

## Guardrails
- Do not promote directly from a raw failure log without confirming the lesson.
- Keep `pattern_key` stable across tasks when the same workflow recurs.
- Use `see_also` to link sibling entries instead of duplicating long explanations.
