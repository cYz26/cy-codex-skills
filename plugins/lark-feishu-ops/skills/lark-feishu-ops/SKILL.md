---
name: lark-feishu-ops
description: Use when Feishu/Lark/lark-cli platform work should be delegated to one short-lived FeishuOps subagent instead of loading many official lark-* skills in the main agent; includes lark-cli dependency preflight, update checks, Codex global lark-skill unloading, docs, IM, contacts, calendar, meetings, sheets, Base, Wiki, Drive, whiteboard, approvals, attendance, mail, OKR, slides, tasks, apps, auth, and raw OpenAPI operations.
metadata:
  requires:
    bins: ["lark-cli", "npx"]
---

# Lark Feishu Ops

## Overview

Use this skill as the single main-agent entry for Feishu/Lark platform work. The main agent should
decide business intent and content, then delegate platform execution to a short-lived `FeishuOps`
subagent.

The plugin intentionally exposes only this thin skill. Do not install or load all official
`lark-*` domain skills into the main agent context. The subagent may read official `lark-*` skill
files or `lark-cli <domain> --help` only when that domain is actually needed.

## Before First Use

Run the plugin doctor:

```bash
python3 ../../scripts/lark_feishu_ops_doctor.py --json
```

When reviewing a repository's Lark skill setup, pass the repo path:

```bash
python3 ../../scripts/lark_feishu_ops_doctor.py --repo <repo> --json
```

The doctor checks:

- `lark-cli` is installed and runnable.
- `lark-cli doctor --offline` and `lark-cli auth status` are available.
- `lark-cli update --check --json` can report whether the CLI is current.
- Official `larksuite/cli` `lark-*` skills are not globally active for Codex.
- Project-local `.codex/skills/lark-*` skills are not scattered into the main-agent context when `--repo` is provided.

If the doctor reports official `lark-*` skills globally active for Codex, and the user asked to
reduce main-agent context, run:

```bash
python3 ../../scripts/lark_feishu_ops_doctor.py --apply-codex-global-unload --json
```

Then rerun the doctor. This unloads official global `lark-*` skills from Codex only; it does not
remove `lark-cli` or Feishu credentials. Start a new Codex thread after cleanup so the skill list is
rebuilt without those global skills.

Project-local scattered Lark skills are reported with advisory actions only. Remove or disable them
manually after reviewing the recommendation, and keep `lark-feishu-ops` as the single project-local
Feishu/Lark entry point when project-local activation is needed.

## When To Use

Use this skill for:

- Reading, creating, updating, or searching Feishu docs/wiki/docx.
- Sending Feishu messages, broadcasts, test-login unblock notifications, or reminders.
- Resolving Feishu users, groups, `open_id`, `union_id`, or `chat_id`.
- Reading calendars, meeting notes, minutes, transcripts, shared docs, or recordings.
- Reading/writing sheets, Base records, Wiki nodes, Drive files, or whiteboards.
- Managing approvals, attendance data, mail, OKR, slides, tasks, apps, events, or domain workflows exposed by `lark-cli`.
- Calling Feishu OpenAPI through `lark-cli schema` or `lark-cli api`.
- Handling `lark-cli` auth, scope, user/bot identity, profile, update notice, or high-risk write confirmation.

Do not use this skill for:

- Product requirement judgment, PRD clarification content, technical design reasoning, app code changes, or test verdicts.
- Replacing a repository-specific source-document snapshot/freeze script. Use the repository's own snapshot tool when OpenSpec or a similar workflow requires frozen source evidence.

## Delegation Contract

Pass a compact request to `FeishuOps`:

```json
{
  "action": "docs.fetch | docs.upsert | im.send | contact.resolve | calendar.agenda | vc.notes | sheets.read | base.query | wiki.node | drive.file | openapi.call | auth.check | domain.call | <lark-domain>.<operation>",
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
  "evidence_request": {
    "mode": "summary | evidence_pack | full_content",
    "focus": ["optional topics, entities, or sections to inspect"]
  },
  "content": {},
  "constraints": [],
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

`FeishuOps` is responsible for:

- Running or honoring the dependency preflight.
- Choosing the correct `lark-cli` domain and command.
- Lazy-loading official `lark-*` rules only inside the subagent.
- Preserving functional parity with scattered official `lark-*` skills by using the same official skill guidance on demand.
- Handling identity, scope, permission, profile restoration, dry-run, and high-risk write confirmation.
- Returning structured execution and validation evidence.
- Returning question-focused evidence when the parent supplies `question` or `evidence_request`.
- Returning discovered follow-up resources instead of silently expanding the task scope.

## Subagent Dispatch

Preferred dispatch:

1. Use a configured custom `feishu-ops`/`FeishuOps` subagent if the host runtime exposes it.
2. Otherwise spawn a normal short-lived subagent and inject `../../agents/runtime-prompts/feishu-ops.md` plus the compact request.

Do not hand the subagent the full main-thread history unless the Feishu operation truly needs it.
Pass only the compact JSON request and the minimum content needed for the platform operation.

The main agent may technically run `lark-cli` directly when the binary and auth are available, but
that is a fallback execution path, not the normal plugin path. If the user invoked this plugin or
asked for FeishuOps routing, do not silently fall back to direct main-agent `lark-cli` execution.
Report the subagent blocker or ask for explicit permission before continuing sequentially.

### Context Handoff

Use a context capsule instead of forwarding the whole parent conversation by default. The capsule is
the parent-owned bridge between business context and FeishuOps platform work.

Codex subagents inherit runtime boundaries such as the active model default, sandbox policy, and
live permission overrides unless a custom agent explicitly overrides what the runtime allows. They
do not automatically inherit the parent thread's full business context. Treat parent context as
explicit data that must be passed through `handoff_context` or by intentionally forking context.

Include:

- `user_goal`: the parent-level task, such as "judge whether this Harness proposal is sound".
- `question`: the exact user question FeishuOps should gather evidence for.
- `parent_context`: only facts and decisions the subagent needs, such as evaluation criteria,
  project names, known date ranges, target users/chats, or previous conclusions.
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

### Intent-Carrying Operations

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

For judgment requests such as "does this Harness design understand the concept well?" or "did this
meeting decide a launch owner?", the expected split is:

- FeishuOps queries the source and returns an evidence pack.
- The parent agent decides the final judgment and explains the tradeoffs to the user.

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

If the source is too large to return in full, FeishuOps should return relevant slices, schema or
outline notes, coverage notes, query limits, and follow-up resource references. The parent should
request another targeted read when the evidence is too thin instead of judging from a generic
summary.

For write operations, FeishuOps should return a side-effect evidence pack instead of a judgment
evidence pack: target IDs, command/request used, confirmation state, created/updated/deleted object
IDs, and read-back validation when the API supports it.

### Progress-Aware Waiting

Treat FeishuOps as active while it emits meaningful progress signals:

- commentary that names the current phase or next command
- a tool call starting
- a tool call returning output
- a new document, sheet, Base, Drive, meeting, or OpenAPI reference discovered
- a compact partial result or validation note

Use an idle timeout for stuck detection. A subagent is only stalled when no meaningful progress has
appeared for the chosen idle window. Do not close an agent merely because the overall wall-clock
wait for a final `completed` status elapsed.

Recommended parent behavior:

1. Start with a bounded wait for completion.
2. If it times out, inspect the subagent's latest visible progress before deciding.
3. Continue waiting when progress is fresh.
4. Interrupt or close only when the idle timeout is exceeded, the subagent repeats the same blocker,
   or the task has expanded beyond the compact request.
5. Ask FeishuOps for a compact partial result before closing an active task whenever possible.

Keep a separate whole-task ceiling for runaway work, but make the user-facing timeout diagnosis
about the last progress signal, not only about elapsed wall-clock time.

### Related Follow-Ups

For multiple questions about the same Feishu/Lark resource, prefer reusing the same
FeishuOps subagent while it is still open. Send a follow-up compact request to that subagent with
the new `question`, the prior resource IDs/tokens, known revisions/cursors/time windows, and any
previously returned `next_resources`.

Reuse is useful because the subagent can keep recent command choices, resource IDs, and document
shape in its context. The parent still owns the final answer and must not rely on hidden subagent
memory as the only evidence. If the subagent has been closed, start a new one and include the prior
evidence pack or resource refs explicitly in the new request.

Close FeishuOps when:

- the parent has enough evidence to answer the user's current question
- the next task is unrelated to the current Feishu/Lark resource
- the subagent is idle beyond the idle timeout
- the subagent hit a blocker that requires parent or user direction

### Task Boundaries

Use one FeishuOps request for one platform operation unless the parent intentionally batches
adjacent simple reads. The parent owns any expansion decision.

Examples:

- `docs.fetch` returns the document content, IDs, revision, and discovered embedded resources.
- `docs.fetch` must not auto-read embedded sheets, Base tables, whiteboards, images, or meeting
  artifacts unless the compact request explicitly asks it to expand those resources.
- `sheets.read` reads the sheet range(s) the parent requested.
- `vc.notes` returns discovered note/transcript/recording references and only fetches the requested
  artifacts.
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
  "residual_risk": []
}
```

## Validation

After changing this plugin:

```bash
python3 ../../scripts/lark_feishu_ops_doctor.py --json
python3 ../../scripts/lark_feishu_ops_doctor.py --strict --json
```

After unloading global official `lark-*` skills:

```bash
python3 ../../scripts/lark_feishu_ops_doctor.py --apply-codex-global-unload --json
python3 ../../scripts/lark_feishu_ops_doctor.py --strict --json
```

For plugin structure validation, run from outside the plugin:

```bash
python3 /Users/cY/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py <plugin-root>
```

## Common Mistakes

- Loading all official `lark-*` skills in the main agent before knowing the action.
- Treating the plugin as a replacement for `lark-cli`; it is a routing and safety layer over `lark-cli`.
- Letting `FeishuOps` decide product or technical content instead of only executing platform operations.
- Letting a narrow read operation silently expand into embedded sheet/Base/Drive/meeting reads.
- Treating a still-active subagent as failed because it has not returned a final result yet.
- Falling back to direct main-agent `lark-cli` execution without telling the user when FeishuOps was requested.
- Guessing Feishu IDs instead of resolving them through CLI.
- Assuming global skill unload affects the already-running thread. It takes effect in a new thread.
