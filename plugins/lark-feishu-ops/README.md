# Lark Feishu Ops

This plugin exposes a single Codex skill, `lark-feishu-ops`, for Feishu/Lark platform work.
The skill keeps official `lark-*` domain instructions and `lark-cli` details out of the main
agent context by routing operations through a short-lived FeishuOps subagent.
For Feishu/Lark platform operations, FeishuOps should preserve functional parity with scattered
official `lark-*` skills by lazy-reading only the relevant domain skill or `lark-cli` help inside
the subagent.

## Why

Installing all official `larksuite/cli` skills globally makes every main-agent session carry a
large list of Feishu/Lark skills. This plugin keeps the main context small:

- one plugin skill is visible to the main agent
- `lark-cli` and official domain rules are checked before use
- Feishu/Lark actions are delegated to a subagent
- global official `lark-*` skills for Codex can be audited and unloaded
- project-local scattered `lark-*` skills can be audited with non-mutating cleanup recommendations

## Delegation Model

The main agent may technically run `lark-cli` directly when the CLI and auth are available, but that
is not the normal path for this plugin. When a user invokes Lark Feishu Ops, the main agent should
route the platform operation to FeishuOps and keep business judgment in the parent thread.

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

For repeated questions about the same resource, keep the same FeishuOps subagent open when possible
and send related follow-up requests to it. This preserves recent IDs, revisions, resource tokens,
cursors, time windows, and command choices. If the subagent has already been closed, start a new one
and include the previous evidence pack or resource refs explicitly in the new request.

The parent should monitor subagents with progress-aware waiting:

- treat command starts, command outputs, discovered resource IDs, and validation notes as progress
- use an idle timeout to detect stalls
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
