---
name: lark-feishu-ops
description: Use when Feishu/Lark/lark-cli platform work is needed through one entry point: docs, IM, contacts, calendar, meetings, sheets, Base, Wiki, Drive, whiteboard, approvals, attendance, mail, OKR, slides, tasks, auth, and OpenAPI operations.
metadata:
  requires:
    bins: ["lark-cli", "npx"]
---

# Lark Feishu Ops

## Overview

Use this as the single main-agent entry for Feishu/Lark platform work. The main agent decides
business intent, then chooses direct `lark-cli` for bounded low-risk reads or FeishuOps for
isolation, lazy domain-skill guidance, progress tracking, or side-effect safety.

Do not install or load all official `lark-*` domain skills into the main agent context. Direct mode
may use `lark-cli` and focused CLI help. FeishuOps may read official `lark-*` skill files or
`lark-cli <domain> --help` only when that domain is actually needed.

Read `references/feishuops-protocol.md` only after the dispatch policy chooses FeishuOps or when
compact request, context handoff, progress waiting, evidence-pack, follow-up, or output details are needed.

## Before First Use

Run the plugin doctor:

```bash
python3 ../../scripts/lark_feishu_ops_doctor.py --json
```

When reviewing a repository's Lark skill setup, pass the repo path:

```bash
python3 ../../scripts/lark_feishu_ops_doctor.py --repo <repo> --json
```

The doctor checks CLI health/auth/update state, global official `lark-*` skill exposure, and
project-local scattered Lark skills. Use `--force-update-check` or `--update-check-policy always`
for explicit maintenance; use `--skip-update-check` only when update checks are intentionally out
of scope.

If the doctor reports `checks.lark_cli.update_action.requires_confirmation`, surface the action to
the user and wait for explicit confirmation before running `lark-cli update --json`. After a
confirmed update, run:

```bash
python3 ../../scripts/lark_feishu_ops_sync.py --after-cli-update --json
```

To let the sync script perform the confirmed update and then validate state:

```bash
python3 ../../scripts/lark_feishu_ops_sync.py --apply-cli-update --json
```

Use `--refresh-installed-plugin` only when the user authorized refreshing the installed Codex plugin
cache. Lark CLI releases require source changes only when compatibility checks show command,
schema, risk, auth/profile, official-skill, or dispatch-policy drift.

If the doctor reports official `lark-*` skills globally active for Codex, and the user asked to
reduce main-agent context, run:

```bash
python3 ../../scripts/lark_feishu_ops_doctor.py --apply-codex-global-unload --json
```

Then rerun the doctor. This unloads official global `lark-*` skills from Codex only; it does not
remove `lark-cli` or Feishu credentials. Start a new Codex thread after cleanup so the skill list is
rebuilt without those global skills.

Project-local scattered Lark skills are advisory-only; keep `lark-feishu-ops` as the single
project-local Feishu/Lark entry point when project-local activation is needed.

## When To Use

Use this skill for:

- Reading, creating, updating, or searching Feishu docs/wiki/docx.
- Sending Feishu messages, broadcasts, test-login unblock notifications, or reminders.
- Resolving Feishu users, groups, `open_id`, `union_id`, or `chat_id`.
- Reading calendars, meeting notes, minutes, transcripts, shared docs, or recordings.
- Reading/writing sheets, Base records, Wiki nodes, Drive files, or whiteboards.
- Managing approvals, attendance data, mail, OKR, slides, tasks, events, or domain workflows exposed by `lark-cli`.
- Calling Feishu OpenAPI through `lark-cli schema` or `lark-cli api`.
- Handling `lark-cli` auth, scope, user/bot identity, profile, update notice, or high-risk write confirmation.

Do not use this skill for:

- Product requirement judgment, PRD clarification content, technical design reasoning, app code changes, or test verdicts.
- Replacing a repository-specific source-document snapshot/freeze script. Use the repository's own snapshot tool when OpenSpec or a similar workflow requires frozen source evidence.

## Dispatch Policy

Main-agent direct `lark-cli` is allowed when all of these are true:

- The operation is read-only, bounded, and easy to validate.
- The needed command is obvious from this skill, focused `lark-cli <domain> --help`, or prior verified command knowledge.
- The request is single-domain or a deliberately small adjacent batch.
- The output can be summarized or converted into an evidence pack without loading official `lark-*` skills into the parent context.
- No auth login, profile switch, scope expansion, high-risk confirmation, write, destructive action, raw OpenAPI exploration, broad pagination, or large attachment/media download is needed.
- The user did not explicitly ask for `FeishuOps`, subagents, or delegated execution.

Use direct mode for dependency/auth status, one known document fetch, one bounded sheet range, one
known Base query, or focused command help. The parent still owns the final answer and evidence.

Escalate to `FeishuOps` when any of these are true:

- The user explicitly asks to use `FeishuOps`, a subagent, delegation, or this plugin's subagent path.
- The operation writes, sends, creates, updates, deletes, confirms, joins/leaves meetings, changes profile/auth/scope, or otherwise has side effects.
- The task is cross-domain, multi-step, permission-sensitive, raw-OpenAPI-heavy, or likely to need official `lark-*` skill guidance.
- The source is large, paginated, embedded-resource-heavy, or may need follow-up reads across docs, Sheets, Base, Drive, Wiki, whiteboard, minutes, mail, IM, tasks, approvals, or OpenAPI.
- Several related questions may be asked about the same resource and subagent context reuse would reduce repeated setup.
- The main agent cannot produce a reliable evidence pack from a small bounded CLI result.

If the user explicitly requested FeishuOps/subagent routing, do not silently run direct
main-agent `lark-cli` instead. Report the subagent blocker or ask for explicit permission to use
direct mode.

## FeishuOps Protocol

After the dispatch policy chooses FeishuOps:

1. Read `references/feishuops-protocol.md`.
2. Run the agent-context helper or equivalent resolver so the compact request carries
   `guidance_sources` for the needed Lark domains.
3. Pass a compact request with `question`, `handoff_context`, `target`, `dispatch_hints`,
   `guidance_sources`, and expected output.
4. Keep parent business judgment in the parent thread.
5. Treat discovered embedded resources as `next_resources` unless the request explicitly asks to expand them.
6. Monitor progress using idle-timeout semantics from the reference.

`guidance_sources` are metadata, not global activation. Available official `lark-*` skill sources
may be injected into the FeishuOps subagent as file guidance for that one request. Missing official
skills must be reported as `missing` and paired with `lark-cli <domain> --help`, `lark-cli schema`,
or `lark-cli api` fallback guidance instead of being claimed as loaded.

Unsupported domains are not assumed to have official skill guidance. If a domain is not present as
an installed official `lark-*` skill and `lark-cli <domain> --help` does not exist, return a blocker
or use an explicitly authorized raw OpenAPI fallback.

## Validation

After changing this plugin:

```bash
python3 ../../scripts/lark_feishu_ops_doctor.py --json
python3 ../../scripts/lark_feishu_ops_doctor.py --strict --json
python3 ../../scripts/lark_feishu_ops_sync.py --after-cli-update --json
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
- Treating the plugin as a replacement for `lark-cli`; it is a routing and safety layer.
- Letting FeishuOps decide product or technical content instead of only executing platform operations.
- Letting a narrow read operation silently expand into embedded sheet/Base/Drive/meeting reads.
- Treating a still-active subagent as failed because it has not returned a final result yet.
- Falling back to direct main-agent `lark-cli` execution without telling the user when FeishuOps was requested.
- Spawning a fresh FeishuOps subagent for every related question when the current one is still open and can accept a bounded follow-up.
- Guessing Feishu IDs instead of resolving them through CLI.
- Assuming global skill unload affects the already-running thread. It takes effect in a new thread.
