# Lark Feishu Ops

Version 0.2.4 keeps the public plugin and skill name `lark-feishu-ops` while
making its routing, guidance, continuity, and readiness contracts fail closed.
It exposes one Codex skill for Feishu/Lark platform work and uses a hybrid route:
direct main-agent `lark-cli` for bounded low-risk reads, and a compact
FeishuOps subagent for delegated, unknown, broad, or side-effectful work.

## Why

Loading every official `lark-*` skill into the main thread consumes context and
can drift from the active CLI version. This plugin instead:

- keeps one plugin skill visible to the main agent;
- derives version-matched guidance from `lark-cli skills list/read`;
- permits direct execution only for explicit allowlisted reads;
- delegates unknown, raw, write, and high-risk actions to FeishuOps;
- keeps continuity metadata-only, bounded, local, and purgeable; and
- audits global skill exposure plus current `.agents/skills` and legacy
  `.codex/skills` project roots without mutating them.

## Dispatch Model

The main agent can run `lark-cli` directly only when an action is in the
explicit read allowlist and the request is read-only, bounded, single-domain,
profile-stable, easy to validate, and free of side effects. Caller hints cannot
turn an unknown, raw, write, or high-risk action into a direct read.

The main agent should route to FeishuOps when the user explicitly asked for FeishuOps or subagent routing,
or when an action is unknown,
writes/sends/updates/deletes,
uses raw OpenAPI, crosses domains, needs permission/profile work, expands
embedded resources, drains pages, downloads large artifacts, or requires a
confirmation/dry-run boundary. If the user explicitly asked for FeishuOps or
subagent routing, do not silently fall back to direct main-agent execution.

Fresh FeishuOps work must be spawned with `fork_turns: none` and receive only
the normalized request, selected guidance metadata, and minimum context
capsule. A persisted active-agent entry is only a reuse candidate: the parent
must confirm with the current Codex runtime that the agent remains active before
sending a follow-up. Complete, blocked, or failed results retire that entry.

FeishuOps should receive one bounded platform operation at a time. A
`docs.fetch`, for example, returns the requested content/evidence plus resource
IDs and revisions; embedded Sheets, Base tables, Drive files, whiteboards, or
meeting artifacts become `result.next_resources` unless explicitly requested.
The parent retains product, technical, and business judgment.

For progress-aware waiting, use the last meaningful signal rather than total
wall-clock time. A 60-90 second idle window is reasonable for small reads, and
2-3 minutes is reasonable for known slower downloads or paginated calls while
fresh progress is visible.

## Trusted Embedded Guidance

Embedded CLI guidance is authoritative. The helper reads the current
`lark-cli skills list --json` inventory and selects only allowlisted names. An
available source has this shape and never contains a local `SKILL.md` path or
caller-provided `inject_as` directive:

```json
{
  "source_type": "cli_embedded_skill",
  "domain": "docs",
  "name": "lark-doc",
  "status": "available",
  "argv": ["lark-cli", "skills", "read", "lark-doc"]
}
```

Missing embedded guidance falls back to focused `lark-cli <domain> --help` or
`lark-cli schema` metadata. Unknown mappings are reported instead of silently
using a stale path, and raw OpenAPI remains explicit and confirmation-gated.

The validated Lark CLI 1.0.88 inventory contains 27 embedded skills:

- `lark-approval`, `lark-apps`, `lark-attendance`, `lark-base`,
  `lark-calendar`, `lark-contact`, `lark-doc`, `lark-drive`, `lark-event`;
- `lark-im`, `lark-mail`, `lark-markdown`, `lark-minutes`, `lark-note`,
  `lark-okr`, `lark-openapi-explorer`, `lark-shared`, `lark-sheets`;
- `lark-skill-maker`, `lark-slides`, `lark-task`, `lark-vc`,
  `lark-vc-agent`, `lark-whiteboard`, `lark-wiki`;
- `lark-workflow-meeting-summary` and `lark-workflow-standup-report`.

Availability is still derived dynamically; this list documents the 0.2.4
compatibility baseline rather than replacing runtime inventory.

Lark CLI 1.0.88 also exposes top-level command domains that are not separate
embedded skills: `application`, `mindnotes`, `config`, `profile`, `doctor`,
`update`, `whoami`, `skills`, and `schema` (with `api` routed through the
OpenAPI guidance path). The router uses focused CLI help plus the closest
trusted embedded guidance for these domains. Any domain without a known mapping
returns a blocker instead of an empty or guessed command path.

## Agent Continuity Helper

From the plugin root:

```bash
python3 scripts/lark_feishu_ops_agent_context.py prepare \
  --repo /path/to/repo --request-json request.json --json
```

For compatibility with released versions, the helper stores repo-local state
under `.dev-flow/lark-feishu-ops/agent-context/`. This is plugin continuity
metadata, not repository workflow authority:

- `active_agents.json` stores bounded lifecycle metadata.
- `snapshots/` stores schema-v2 metadata capsules, never request/evidence bodies.

The prepare command uses the decision family `direct`, `reuse_active`, `reconstruct_from_cache`, or `fresh_subagent`; 0.2.4 emits the active case as
`reuse_active_candidate` to make its required runtime confirmation explicit.
Cache reconstruction restores
only identifiers, resource type/revision, affinity, identity/profile, risk,
timestamps, expiry, freshness, and provenance classifications; content must be
refetched when required. `require_refetch: true` always wins.

Hard limits are 64 snapshots per repository, 32 resource references per
snapshot, 256 UTF-8 bytes per retained metadata string, 32 KiB per state file,
a 30-minute active-agent idle limit, and a maximum 24-hour snapshot TTL.
Authentication/profile, contact, approval, attendance, IM, mail, Minutes/Note,
OKR, and VC domains default to no snapshot persistence. Files are atomically
replaced with mode `0600`;
expired, malformed, oversized, legacy, and excess state is pruned.
Current schema-v2 state is also allowlisted field-by-field: unknown top-level
or nested fields are rejected and removed, freshness/provenance values are
typed, and active-agent registry entries are sanitized on both write and read.
The normalized runtime request keeps the complete bounded operation capsule
needed for execution, but only metadata from that request may enter continuity
state.
`record-result` never invents a current observation: missing, malformed, or
future-dated freshness/provenance and `require_refetch: true` all decline
persistence. Snapshot TTL ordering and the full serialized 32 KiB budget are
checked before write; oversized active registries retain only the newest safe
prefix that fits instead of failing the command.

Opt out by setting `cache_policy: disabled` in the request. Purge continuity
metadata explicitly with:

```bash
python3 scripts/lark_feishu_ops_agent_context.py purge --repo /path/to/repo --json
```

The helper does not call Codex subagent primitives. The parent owns spawn,
follow-up, list, wait, interrupt, and close operations.

## Doctor and Sync

Run the read-only preflight:

```bash
python3 scripts/lark_feishu_ops_doctor.py --json
python3 scripts/lark_feishu_ops_doctor.py --repo /path/to/repo --json
```

The doctor inventories every reachable `lark-cli`, identifies the canonical
absolute executable, verifies command-specific JSON contracts, checks the
dynamic 27-skill inventory and routing coverage for every executable, separates
binary-version drift from embedded-guidance drift, separates official provenance
from global exposure, and audits current `.agents/skills` plus legacy
`.codex/skills`. Missing `npx` limits installer/global-audit operations but does
not fail normal runtime readiness.
Doctor is no-write by default. Its daily update-check cache is reused only while the cached current version
matches the executable version detected in the same run, so an authorized CLI
upgrade cannot be masked by a same-day stale result. Use
`--write-update-cache` only when persisting a successful fresh check is an
explicitly desired maintenance effect.

Explicit request identity/profile becomes `cli_execution.required_global_args`
(`--as` and `--profile`). Omitted values stay `unknown`; returned mismatch is
blocked and never cached. Lark CLI profile precedence is explicit `--profile`,
then `LARKSUITE_CLI_PROFILE`, then persisted selection. Structured JSON errors
from stderr remain available in diagnostics. Doctor recognizes both official
`separate` and `suite` Skill layouts but never switches layout implicitly.
For `suite`, provenance is trusted only when the canonical shared-root path,
top-level frontmatter, CLI-reported layout and in-sync state, nested Skill names,
and every `references/lark-*/SKILL.md` SHA-256 digest match the healthy canonical
CLI embedded inventory; otherwise exposure remains unverified. One suite
directory is not compact in the Codex manager: Codex
recursively discovers those nested Skill files. Doctor therefore reports both
filesystem compaction and `codex_recursive_exposure_count`; use the plugin-only
path when zero global Lark exposure is required.

CLI update, official-guidance synchronization, global skill unload, and
installed plugin cache refresh remain explicit confirmation-gated effects. Do
not treat a doctor recommendation as authorization. Doctor blocks Codex-only
unload without mutation when Skills live under the shared `~/.agents/skills`
canonical root; relocation or all-Agent removal needs separate approval. After
an authorized CLI update, run:

```bash
python3 scripts/lark_feishu_ops_sync.py --after-cli-update --json
```

Use `--refresh-installed-plugin` only when installed-cache refresh was
separately authorized. Development source is canonical under
`dev/plugins/lark-feishu-ops`; update the release tree only through an explicit,
reviewed development-to-release change.

The generated package also ships one bounded offline self-test for its core
fail-closed invariants. It imports only packaged modules and performs no CLI,
network, auth/profile, Feishu-resource, or continuity-state mutation:

```bash
python3 scripts/test_runtime_contract.py --json
```

## Compatibility

Version 0.2.4 binds suite provenance to explicit CLI sync evidence and embedded
content digests on top of the 0.2.3 Codex visibility correction. See
`CHANGELOG.md` for the complete operator impact.
