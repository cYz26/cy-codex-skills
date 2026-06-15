# FeishuOps Protocol Reference

Use this reference after the dispatch policy chooses FeishuOps, or when a parent agent needs the
exact compact request, evidence-pack, progress-wait, or follow-up contract.

## Compact Request

Pass a bounded request to FeishuOps:

```json
{
  "request_id": "parent-generated stable id",
  "action": "docs.fetch | docs.upsert | im.send | contact.resolve | calendar.agenda | vc.notes | sheets.read | base.query | wiki.node | drive.file | openapi.call | auth.check | domain.call | <lark-domain>.<operation>",
  "goal": "specific FeishuOps deliverable",
  "intent": "why this Feishu operation is needed",
  "question": "optional user question the parent must answer from the fetched evidence",
  "handoff_context": {
    "user_goal": "what the parent is trying to answer or accomplish",
    "parent_context": ["only facts, constraints, and decisions needed by FeishuOps"],
    "known_resources": [],
    "prior_evidence_pack": {},
    "freshness": {
      "known_revision_id": null,
      "known_cursor": null,
      "known_time_window": null,
      "require_refetch": false
    },
    "non_goals": []
  },
  "target": {},
  "dispatch_hints": {
    "explicit_subagent": false,
    "direct_allowed": true,
    "read_only": true,
    "bounded": true,
    "single_domain": true,
    "identity": "user | bot | mixed | none",
    "profile": "optional lark-cli profile"
  },
  "guidance_sources": [
    {
      "source_type": "skill",
      "domain": "docs",
      "name": "lark-doc",
      "status": "available | missing",
      "path": "optional local SKILL.md path when available",
      "inject_as": "skill_file"
    },
    {
      "source_type": "cli_help",
      "domain": "docs",
      "name": "lark-cli docs --help",
      "status": "fallback",
      "command": ["lark-cli", "docs", "--help"]
    }
  ],
  "evidence_request": {
    "mode": "summary | evidence_pack | full_content",
    "focus": ["optional topics, entities, or sections to inspect"]
  },
  "content": {},
  "constraints": [],
  "expected_output": "evidence_pack | side_effect_report | artifact | blocker",
  "success_criteria": [],
  "stop_conditions": [],
  "return_format": "json"
}
```

The parent agent remains responsible for:

- Preparing business content before `docs.upsert` or `im.send`.
- Deciding whether a side effect is desired.
- Supplying exact document URLs, time windows, target names, or message text.
- Consuming returned `doc_url`, `message_id`, table rows, or blockers.
- Owning the final user-facing answer and deciding whether discovered follow-up resources should
  be fetched.
- Passing the user's actual question or decision intent into FeishuOps when a document read will
  support later judgment.
- Deciding whether the returned evidence is sufficient for the final answer.
- Tracking subagent progress as an idle-timeout problem, not as a "no final answer yet" problem.
- Resolving action domains into `guidance_sources` before spawning FeishuOps. This resolution may
  point at an available official `lark-*` skill file, but it must not globally activate every
  official Lark skill in the parent context.

FeishuOps is responsible for:

- Running or honoring the dependency preflight.
- Choosing the correct `lark-cli` domain and command.
- Reading or honoring only the `guidance_sources` relevant to the requested domains.
- Preserving functional parity with scattered official `lark-*` skills by using available
  `guidance_sources` on demand and falling back to focused CLI help/schema guidance when a skill is
  missing.
- Reporting the `guidance_sources` it actually used in the final result.
- Handling identity, scope, permission, profile restoration, dry-run, and high-risk write confirmation.
- Returning structured execution and validation evidence.
- Returning question-focused evidence when the parent supplies `question` or `evidence_request`.
- Returning discovered follow-up resources instead of silently expanding the task scope.

## Subagent Dispatch

Only use this after the dispatch policy chooses FeishuOps.

Preferred dispatch:

1. Use a configured custom `feishu-ops`/`FeishuOps` subagent if the host runtime exposes it.
2. Otherwise spawn a normal short-lived subagent and inject `../../agents/runtime-prompts/feishu-ops.md` plus the compact request.

Do not hand the subagent the full main-thread history unless the Feishu operation truly needs it.
Pass only the compact JSON request and the minimum content needed for the platform operation.

The main agent may run `lark-cli` directly only when the dispatch policy allows direct mode. If the
policy chose FeishuOps and the subagent cannot be spawned, report the blocker or ask for explicit
permission before continuing with direct main-agent execution.

## Agent Continuity Helper

For related Lark/Feishu work, the parent can use the helper before deciding whether to run direct,
reuse an active FeishuOps subagent, reconstruct from cache, or spawn a clean subagent:

```bash
python3 ../../scripts/lark_feishu_ops_agent_context.py prepare --repo <repo> --request-json <request.json> --json
```

Runtime state is local to the repository and ignored by Git:
`.dev-flow/lark-feishu-ops/agent-context/`. It contains `active_agents.json` and `snapshots/`
context capsules, not full conversations.

The helper returns `direct`, `reuse_active`, `reconstruct_from_cache`, or `fresh_subagent`.
Use `record-active` after the parent actually spawns a FeishuOps subagent, and `record-result`
after FeishuOps returns a structured result. FeishuOps should include `context_cache_update` when
it has useful resource refs, resource maps, command shapes, missing evidence, freshness, or
provenance for future related tasks.

The helper also attaches `guidance_sources` to the normalized request. These sources are compact
provenance and injection hints: available official skill files can be passed to the subagent for the
current request, while missing skill entries require the subagent to use the paired focused
`lark-cli` help/schema fallback. A `blocker` source means the parent must authorize raw OpenAPI or
provide a supported domain mapping before FeishuOps proceeds.

The helper does not spawn, message, wait for, or close subagents. Actual Codex runtime primitives
remain the parent agent's responsibility.

## Context Handoff

Use a context capsule instead of forwarding the whole parent conversation by default. The capsule is
the parent-owned bridge between business context and FeishuOps platform work.

Codex subagents inherit runtime boundaries such as the active model default, sandbox policy, and
live permission overrides unless a custom agent explicitly overrides what the runtime allows. They
do not automatically inherit the parent thread's full business context. Treat parent context as
explicit data that must be passed through `handoff_context` or by intentionally forking context.

Include:

- `user_goal`: the parent-level task, such as "judge whether this Harness proposal is sound".
- `question`: the exact user question FeishuOps should gather evidence for.
- `parent_context`: only facts and decisions the subagent needs.
- `known_resources`: document IDs, revisions, sheet IDs, table IDs, chat IDs, message IDs,
  calendar event IDs, meeting IDs, task IDs, approval IDs, cursors, or time windows already known.
- `prior_evidence_pack`: the previous FeishuOps result when starting a fresh subagent for a related
  follow-up.
- `freshness`: whether known revisions/cursors/windows are acceptable or the subagent must re-fetch.
- `non_goals`: what FeishuOps should not decide or fetch.

Use full parent-context forking only when the platform operation cannot be described as a compact
capsule. For Lark/Feishu operations, that should be rare. Full forking increases context pressure
and can make the subagent inherit irrelevant business discussion.

When a related subagent is still active, prefer sending it a follow-up request with the new
`question` and updated `handoff_context`. When it is closed, start a new subagent and include the
prior evidence pack and resource refs explicitly; do not rely on hidden memory from closed agents.

## Codex Subagent Mechanics

Codex subagents provide useful primitives, but they do not replace this Lark-specific contract.

- Default spawned agents inherit the parent model selection unless an override is provided.
- Runtime/tool access generally follows the host session configuration, but custom agent
  definitions or host policy may narrow it. Do not assume every parent skill instruction is active
  inside the subagent.
- Use context forking only when the subagent truly needs the same conversation context as the
  parent. For normal Lark operations, prefer the compact request plus `handoff_context`.
- Pass the FeishuOps runtime prompt, needed skill file path, or concrete command guidance
  explicitly when the subagent must follow it.
- Pass `guidance_sources` explicitly; do not assume the subagent has every official Lark skill
  registered just because the parent knows about this plugin.
- Reuse an active subagent for related follow-ups by sending another compact request. After a
  subagent is closed, its hidden context is not a durable source of truth; pass prior evidence and
  resource refs explicitly.
- Waiting primitives normally report final completion or timeout. A wait timeout is not by itself
  a task failure; inspect progress signals and use the idle-timeout rules below.

The official primitives solve process mechanics: spawn, optional context fork, follow-up messages,
wait, resume, and close. This skill still must solve domain mechanics: what context to pass, what
evidence to return, when to expand resources, and when direct `lark-cli` is enough.

## Intent-Carrying Operations

Do not ask FeishuOps for only a generic summary when the parent needs to answer a specific question.
Include the user's question in the compact request so FeishuOps can inspect the Lark resource with
the right focus.

This applies across Lark domains, not only documents:

- Docs/Wiki/Drive/Markdown: return section-focused evidence and embedded resource refs.
- Sheets/Base: return the requested ranges, records, filters, row counts, schema fields, and missing
  rows/columns needed to answer the question.
- Calendar/VC/Minutes: return relevant events, attendees, time windows, summaries, transcript
  snippets, action items, and unexpanded recording/artifact refs.
- IM/Mail/Task/Approval/OKR/Attendance: return matched messages, threads, tasks, approvals, users,
  statuses, timestamps, and any query limits or permission gaps.
- OpenAPI/domain calls: return request shape, response facts, pagination/cursor state, and follow-up
  calls needed for completeness.

For judgment requests such as "does this Harness design understand the concept well?", the expected
split is that FeishuOps queries the source and returns an evidence pack, then the parent decides the
final judgment.

An evidence pack should be stronger than a summary:

```json
{
  "question": "does this document understand Harness well?",
  "coverage": "which sections were inspected and why they are relevant",
  "relevant_excerpts": [
    {
      "section": "Harness definition",
      "text": "short paraphrase or compliant excerpt",
      "supports": "what this evidence proves"
    }
  ],
  "missing_evidence": ["important points the document did not cover clearly"],
  "next_resources": []
}
```

For write operations, FeishuOps should return a side-effect evidence pack: target IDs,
command/request used, confirmation state, changed object IDs, and read-back validation when the API
supports it.

## Progress-Aware Waiting

Treat FeishuOps as active while it emits meaningful progress signals:

- commentary that names the current phase or next command
- a tool call starting
- a tool call returning output
- a new document, sheet, Base, Drive, meeting, or OpenAPI reference discovered
- a compact partial result or validation note

Use an idle timeout for stuck detection. A subagent is only stalled when no meaningful progress has
appeared for the chosen idle window. Do not close an agent merely because the overall wall-clock
wait for a final `completed` status elapsed.

Start with a bounded wait for completion. Use a longer initial wait for Lark work than a generic
quick poll; 2-3 minutes is reasonable for document, sheet, Base, or meeting reads when progress is
visible. If it times out, inspect latest progress. Continue waiting when progress is fresh.
Interrupt or close only when the idle timeout is exceeded, the subagent repeats the same blocker, or
the task has expanded beyond the compact request. Ask FeishuOps for a compact partial result before
closing active work whenever possible.

Use an idle timeout around the last meaningful progress signal, not the initial spawn time. A
practical default is 60-90 seconds of no progress for small reads and 2-3 minutes for known slow
downloads or paginated calls.

## Related Follow-Ups

For multiple questions about the same Feishu/Lark resource, prefer reusing the same FeishuOps
subagent while it is still open. Send a follow-up compact request with the new `question`, prior
resource IDs/tokens, known revisions/cursors/time windows, and any previously returned
`next_resources`.

The parent still owns the final answer and must not rely on hidden subagent memory as the only
evidence. If the subagent has been closed, start a new one and include the prior evidence pack or
resource refs explicitly in the new request.

Close FeishuOps when the parent has enough evidence, the next task is unrelated, the subagent is
idle beyond the idle timeout, or the subagent hit a blocker that requires parent or user direction.

## Task Boundaries

Use one FeishuOps request for one platform operation unless the parent intentionally batches
adjacent simple reads. The parent owns any expansion decision.

- `docs.fetch` returns the document content, IDs, revision, and discovered embedded resources.
- `docs.fetch` must not auto-read embedded sheets, Base tables, whiteboards, images, or meeting
  artifacts unless the compact request explicitly asks it to expand those resources.
- `sheets.read` reads the sheet range(s) the parent requested.
- `vc.notes` returns discovered note/transcript/recording references and only fetches requested artifacts.
- `im.search`, `mail.search`, `task.*`, `approval.*`, and other domain calls keep pagination and
  follow-up cursors explicit instead of silently draining every page.

If FeishuOps discovers more resources than requested, it should return them in `result.next_resources`
or `artifacts` with enough IDs/tokens for the parent to dispatch follow-up tasks.

## Output Expected From FeishuOps

```json
{
  "status": "PASS | BLOCKED | FAILED",
  "action": "...",
  "identity": "user | bot | mixed | none",
  "commands_or_tools_used": ["..."],
  "targets": {},
  "progress": {
    "last_signal": "short description of the latest meaningful progress",
    "state": "active | complete | blocked | failed"
  },
  "result": {
    "evidence_pack": {},
    "next_resources": []
  },
  "side_effects": [],
  "validation": {},
  "artifacts": [],
  "blockers": [],
  "residual_risk": [],
  "context_cache_update": {
    "resource_refs": [],
    "resource_map": {},
    "known_command_shapes": [],
    "missing_evidence": [],
    "freshness": {},
    "provenance": {}
  }
}
```
