# Lark Feishu Ops

This plugin exposes a single Codex skill, `lark-feishu-ops`, for Feishu/Lark platform work.
The skill keeps official `lark-*` domain instructions and `lark-cli` details out of the main
agent context by using a hybrid route: direct main-agent `lark-cli` for bounded low-risk reads, and
a short-lived FeishuOps subagent for complex, side-effectful, cross-domain, or explicitly delegated
operations. For Feishu/Lark platform operations that use FeishuOps, the subagent should preserve
functional parity with scattered official `lark-*` skills by lazy-reading only the relevant domain
skill or `lark-cli` help inside the subagent.

## Why

Installing all official `larksuite/cli` skills globally makes every main-agent session carry a
large list of Feishu/Lark skills. This plugin keeps the main context small:

- one plugin skill is visible to the main agent
- `lark-cli` and official domain rules are checked before use
- simple bounded reads can run directly through `lark-cli`
- risky, broad, or multi-step Feishu/Lark actions are delegated to a subagent
- global official `lark-*` skills for Codex can be audited and unloaded
- project-local scattered `lark-*` skills can be audited with non-mutating cleanup recommendations

## Dispatch Model

The main agent can run `lark-cli` directly when the CLI and auth are available and the operation is
read-only, bounded, single-domain or a small adjacent batch, easy to validate, and does not require
auth/profile/scope changes, broad pagination, raw OpenAPI exploration, high-risk confirmation, or
official `lark-*` skill loading in the parent context. Examples include a known document fetch, a
bounded sheet range, a known Base query, auth status, update check, or focused command help.

The main agent should route to FeishuOps when the user explicitly asks for FeishuOps/subagents, or
when the operation writes/sends/updates/deletes, crosses domains, needs permission or profile work,
uses raw OpenAPI, expands embedded resources, drains pages, downloads larger artifacts, or may need
several related follow-up reads. In those cases the parent keeps business judgment in the parent
thread and FeishuOps owns the platform operation.

If a user explicitly asked for FeishuOps or subagent routing, do not silently fall back to direct
main-agent `lark-cli`. Report the subagent blocker or ask for permission to continue direct.

FeishuOps should receive one compact operation at a time. For example, `docs.fetch` returns the
document content, IDs, revision, and discovered embedded resources. It should not silently expand
into `sheets.read`, `base.query`, Drive downloads, whiteboard exports, or transcript reads unless
the parent explicitly requested that expansion.

When the user asks a question about a Lark resource, the parent should pass that question into
FeishuOps. The subagent then returns an evidence pack, not just a summary. For documents this means
sections and excerpts; for Sheets/Base it means ranges, schema, matched rows, and filters; for
calendar/meetings it means time windows, event IDs, attendees, summaries, transcript snippets, and
action items; for IM/mail/tasks/approvals it means object IDs, statuses, timestamps, matched
messages, and query limits. The parent uses that evidence pack to make the final judgment.

The parent should also pass a small `handoff_context` capsule instead of the whole conversation by
default. The capsule carries the user goal, relevant parent decisions, known resource IDs/revisions,
prior evidence, freshness requirements, and non-goals. FeishuOps treats that capsule as the
authoritative context for platform work and asks for the smallest missing field when it is
insufficient.

Subagents inherit normal runtime boundaries from the parent session, such as sandbox and permission
policy, default model selection, workspace access, and available local tools unless a custom agent
configuration overrides them. They do not automatically inherit the parent thread's full business
context. Pass business context explicitly through `handoff_context`, or intentionally fork context
only for exceptional cases.

Codex's subagent API gives the process primitives: spawn an agent, optionally fork the full context,
send follow-up input to an active agent, wait, resume, and close. It does not automatically define a
Lark evidence protocol or make closed subagent context durable. This plugin therefore keeps the
domain protocol explicit: the parent passes intent and context, FeishuOps returns evidence packs and
resource refs, and direct `lark-cli` remains valid when the dispatch policy says the communication
overhead is not worth it.

For repeated questions about the same resource, keep the same FeishuOps subagent open when possible
and send related follow-up requests to it. This preserves recent IDs, revisions, resource tokens,
cursors, time windows, and command choices. If the subagent has already been closed, start a new one
and include the previous evidence pack or resource refs explicitly in the new request.

The parent should monitor subagents with progress-aware waiting:

- treat command starts, command outputs, discovered resource IDs, and validation notes as progress
- use an idle timeout to detect stalls, usually 60-90 seconds after the last progress signal for
  small reads and 2-3 minutes for known slow downloads or paginated calls
- use a longer initial wait than a generic quick poll for Lark work; 2-3 minutes is reasonable when
  progress is visible
- do not close a subagent only because the final result has not arrived yet
- ask for a compact partial result before stopping active work when possible

This mirrors the narrow-worker pattern used by other plugin workflows: the parent owns final state
and follow-up dispatch; the subagent owns a bounded platform operation and returns structured
evidence.

Example acceptance shape:

1. Parent asks FeishuOps to `docs.fetch` a Harness design document.
2. Parent includes the question, such as whether the document understands Harness well.
3. FeishuOps returns title, document ID, revision, an evidence pack, and `next_resources` such as
   embedded whiteboards or Base tables without expanding them.
4. Parent uses that evidence to answer whether the document's Harness understanding is sound.

## Doctor

Run the preflight doctor before using the plugin, or when Codex still shows many `lark-*` skills:

```bash
python3 plugins/lark-feishu-ops/scripts/lark_feishu_ops_doctor.py --json
```

To also inspect the current project for project-local scattered `lark-*` skills:

```bash
python3 plugins/lark-feishu-ops/scripts/lark_feishu_ops_doctor.py --repo /path/to/repo --json
```

The project audit scans `<repo>/.codex/skills/`, treats `lark-feishu-ops` as the preferred entry
point, and reports advisory actions for scattered `lark-*` domain skills. It does not modify files.

To remove official `larksuite/cli` global skills from Codex only:

```bash
python3 plugins/lark-feishu-ops/scripts/lark_feishu_ops_doctor.py --apply-codex-global-unload --json
```

Start a new Codex thread after unloading global skills; already-loaded skill lists in the current
thread cannot be retroactively removed.
