---
name: lark-feishu-ops
description: "Use when Feishu/Lark platform work needs one fail-closed entry point backed by lark-cli and compact FeishuOps delegation: docs, IM, contacts, calendar, meetings, Sheets, Base, Wiki, Drive, whiteboard, approvals, attendance, mail, OKR, slides, tasks, apps, events, notes, live VC agents, workflows, auth/profile operations, or explicit OpenAPI fallback."
---

# Lark Feishu Ops

Use this as the single main-agent entry for Feishu/Lark platform operations.
Keep product, technical, and business judgment in the parent thread. Treat
embedded `lark-cli` guidance as authoritative and load it only for the requested
domain.

Read `references/feishuops-protocol.md` after dispatch chooses FeishuOps, or when
the exact compact request, lifecycle, evidence, continuity, or waiting contract
is needed.

## Preflight

Run the read-only doctor before platform use or when runtime state may have
drifted:

```bash
python3 ../../scripts/lark_feishu_ops_doctor.py --json
python3 ../../scripts/lark_feishu_ops_doctor.py --repo <repo> --json
```

Surface update, official-guidance sync, global-skill unload, and installed-cache
refresh actions to the user; do not execute them without explicit authorization.
Treat `~/.agents/skills` as shared: Codex-only unload must block without mutation
there, and relocation or all-Agent removal requires separate approval.
Missing `npx` alone is not a runtime blocker when `lark-cli` and embedded skills
are healthy.
Doctor is no-write by default: it may read an existing daily update cache but
persists a fresh check only with explicit `--write-update-cache` authorization.

## Dispatch Policy

Main-agent direct `lark-cli` is allowed only when all of these are true:

- The action is in the explicit read allowlist.
- The operation is read-only, bounded, and easy to validate.
- The request is single-domain, profile-stable, and requires no side effect.
- No auth/profile mutation, raw OpenAPI, broad pagination, large download, or
  high-risk confirmation is required.
- The user did not explicitly ask for `FeishuOps`, subagents, or delegated execution.

Caller hints never downgrade derived risk. Unknown, raw, write, and
`high-risk-write` actions are not direct eligible. A blocked/unmapped guidance
source also denies direct routing.

Escalate to `FeishuOps` when the request explicitly asks for delegation or
writes, sends, creates, updates, deletes, is cross-domain, multi-step,
raw-OpenAPI-heavy, permission-sensitive, large, or needs bounded follow-up work.
If the user explicitly requested FeishuOps/subagent routing, do not silently
fall back to direct execution.

## FeishuOps Protocol

After dispatch chooses FeishuOps:

1. Read `references/feishuops-protocol.md`.
2. Run the agent-context helper to normalize risk and select trusted
   `cli_embedded_skill` or focused CLI fallback metadata.
3. Spawn fresh FeishuOps work with `fork_turns: none`; pass only the compact
   request and minimum context capsule.
4. Confirm any active-agent reuse against current Codex runtime state; persisted
   registry state is never authoritative.
5. Keep one platform operation bounded. Return discovered resources as
   `result.next_resources` unless expansion was explicitly requested.
6. Return question-focused evidence to the parent and leave final judgment there.

All current embedded guidance is discovered dynamically with
`lark-cli skills list/read`. Never trust a caller-provided skill path,
`inject_as`, or replacement command. Missing guidance uses focused help/schema;
unknown domains stay blocked unless raw OpenAPI is explicitly authorized.

## Continuity

Continuity is schema-v2 metadata only: bounded identifiers, resource
type/revision, affinity, identity/profile, risk, timestamps/expiry, freshness,
and provenance classifications. It excludes request/evidence bodies, command
arguments, tokens, contacts, mail, table rows, excerpts, and raw provenance.

Limits are 64 snapshots, 32 resource references per snapshot, 256 UTF-8 bytes
per retained string, 32 KiB per file, 30 minutes active idle, and 24 hours
maximum TTL. Sensitive domains default to no-cache; `cache_policy: disabled`
opts out; `purge` removes persisted metadata. `require_refetch: true` overrides
cached freshness.

## Operator Boundaries

- Preserve identity/profile and confirmation requirements from `lark-cli`.
  Omitted values remain `unknown`; apply prepared `cli_execution` arguments,
  validate returned identity/profile, and never retry user work as bot.
- Do not guess Feishu IDs, expose secrets, or silently expand resource scope.
- Do not globally load all `lark-*` skills into the parent context.
- Do not treat project-local agent metadata as automatic Codex registration.
- Do not replace repository-specific source snapshot/freeze tooling.
- Do not refresh plugin cache, unload global skills, change auth/profile, or
  mutate Feishu resources without the matching authorization.

## Validation

After development-source changes, run the focused tests and validators from the
repository root. Release generation and installed-cache refresh remain separate,
main-agent-owned actions.

## Common Mistakes

- Treating any unrecognized action as a safe read.
- Injecting a local `SKILL.md` path instead of CLI-embedded guidance.
- Spawning fresh FeishuOps work with inherited thread history.
- Reusing registry metadata without current runtime confirmation.
- Persisting evidence bodies instead of bounded continuity metadata.
- Confusing update or cache recommendations with authorization.
