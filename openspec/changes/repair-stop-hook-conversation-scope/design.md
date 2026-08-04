## Context

See `proposal.md` for motivation. The current aggregate Stop entrypoint reads
the JSON payload but uses only `cwd`; it then evaluates the repository's active
OpenSpec source on every invocation. Current Codex behavior supplies
`stop_hook_active`, creates a new user-like continuation prompt after
`decision: "block"`, and implements side conversations as ephemeral forks.

The public Codex Hook contract documents `session_id`, `transcript_path`,
`turn_id`, `stop_hook_active`, and `last_assistant_message`, but no stable
side-conversation or parent-thread field. The transcript format is explicitly
unstable and cannot be used as a policy interface.

Capability evidence:

- `authoritative_current`: the 2026-08-04 Codex manual and
  <https://learn.chatgpt.com/docs/hooks> define Stop reentrancy and automatic
  continuation; current `openai/codex` side-chat source creates an ephemeral
  fork whose app-server thread path is null.
- `local_scan`: `devflow_stop_hook.py` consumes only `cwd`; `hooks.json` has one
  unconditional Stop entrypoint; no source test references `stop_hook_active`;
  the installed cache is a generated runtime archive and does not load
  development source dynamically.
- `comparison`: a one-shot guard alone stops the infinite loop but still forces
  one unrelated continuation in a side chat. A durable-transcript boundary
  also prevents the first side-chat block without inventing parent metadata.
  Persistent session ownership would require a state/migration contract and a
  supported parent relationship that Codex does not currently expose.
- `assumptions`: current ephemeral side forks continue to surface
  `transcript_path: null`. A future persisted side-chat implementation requires
  a new capability check rather than transcript-content parsing.
- `contract`: public command tests cover reentrant, ephemeral, durable, legacy,
  and `--json` cases; Doctor reports the same invariant matrix.

## Goals / Non-Goals

**Goals:**

- Prevent repeated Stop continuation and the first repository-continuation
  block in an ephemeral side conversation.
- Preserve the existing first-stop guard for a durable conversation that owns
  approved work.
- Keep hook scope a small pure decision before all repository checks.
- Make protocol drift visible in focused tests and Workflow Doctor output.

**Non-Goals:**

- Infer parent/child identity from transcript contents, assistant text, titles,
  or undocumented app metadata.
- Add persisted session ownership, leases, a workflow-state migration, or a
  second execution queue.
- Change continuation outcome precedence or make the Stop hook execute work.
- Promote the generated release, refresh an installed plugin cache, archive,
  commit, push, or publish a release without their separate gates.

## Decisions

### Classify hook applicability before repository inspection

Add a small pure module that returns an enforce/skip decision and a stable
reason from the hook payload. The command entrypoint calls it before
`run_stop_checks()`. `stop_hook_active is True` has first precedence;
`transcript_path` explicitly present as null has second precedence; a durable
path and an omitted legacy field enforce existing policy.

This ordering makes the fix deterministic and keeps side conversations from
even reading another conversation's execution queue. Alternative: run every
check and discard the result. Rejected because it preserves unnecessary work
and couples out-of-scope conversations to repository state.

### Use a conservative durable-transcript boundary

An explicitly null transcript path is treated as an ephemeral conversation and
cannot own repository-level automatic continuation. An absent field is not
treated as ephemeral, preserving behavior for older payloads and direct hook
tests. The rule does not claim that null universally means “side chat”; it
states that non-durable conversations are outside DevFlow's durable execution
enforcement.

Alternative: bind state to `session_id`. Rejected for this repair because the
current payload lacks a stable parent/side relationship, the active agent has
no supported API to claim its session ID in repository state, and introducing
ownership state would require compatibility and migration semantics.

Alternative: scan the transcript for the side-conversation boundary. Rejected
because Codex documents the transcript format as unstable and capability-
research forbids using it as the only policy signal.

### Keep manual diagnostics independent from live hook scope

`--json` remains an operator diagnostic over the requested repository and runs
even without a live Hook payload. Applicability only controls normal hook
stdout. This preserves existing scripts and makes validation possible without
fabricating a durable transcript.

### Share a literal invariant matrix with Workflow Doctor

The pure scope module exposes a protocol self-check over four independent
known examples: reentrant and ephemeral skip; durable and legacy enforce.
Workflow Doctor includes the structured result and promotes a failed invariant
to an issue. Public command tests remain the primary regression seam; Doctor is
operational detection, not substitute completion evidence.

## Completion Contract

- [x] Public Stop entrypoint blocks exactly once for durable unfinished work.
- [x] Reentrant and ephemeral payloads exit `0`, emit no stdout, and do not call
  repository checks.
- [x] Durable and legacy payloads retain current continuation/Human Gate
  behavior.
- [x] `--json` diagnostics remain complete and independent of hook scope.
- [x] Workflow Doctor emits a passing scope-contract report and fails closed if
  the invariant matrix is broken.
- [x] Focused and broad source tests, strict OpenSpec validation, workflow
  validation, Plugin Eval diagnostics, and diff review pass with durable
  evidence.

## Critical Path and Capability Slices

### Slice 1: Public RED scope regressions

- Add entrypoint tests at the confirmed stdin/stdout seam for reentrant,
  ephemeral, durable, legacy, and JSON diagnostic payloads.
- Observe the exact current failures before production edits.

### Slice 2: Pure scope policy and hook integration

- Add the pure classifier and protocol invariant report.
- Short-circuit only normal hook enforcement; preserve current repository
  decision code and response schema.
- Add Doctor reporting and focused GREEN verification.

### Slice 3: Integrated proof and gated release readiness

- Run focused tests, the complete source-only suite, strict OpenSpec and
  workflow validation, diff checks, source/release/cache drift inspection, and
  release-target Plugin Eval as applicable.
- Record source completion and report release/cache drift without applying it.

## Execution Ledger

| Slice | Owner | Write Set | Evidence | Human Gate | Status |
|---|---|---|---|---|---|
| Public RED scope regressions | main | focused DevFlow test files | exact observed RED command/output | none | done |
| Scope policy and Doctor | main | development scripts and focused tests | focused GREEN plus original repro | scope expansion or schema change only | done |
| Integrated proof | main | change evidence and DevFlow state | source suite, validators, Eval, diff review | release/cache/archive/commit/push | done |

Execution policy is `auto-until-terminal`; task, review, and verification
boundaries are not Human Gates. No subagent is used because this side
conversation is constrained to single-agent work, and the write set is small
and shared.

## Incidental Finding Budget and Escalation Triggers

At most one bounded RED/GREEN guard may be admitted if it is required to keep
the public Stop seam safe. New dependencies, workflow-state schema, transcript
parsing, persistent ownership, generated-release application, installed-cache
mutation, or any broader Codex compatibility decision requires replanning or a
separate Human Gate.

## Generated Artifact Strategy

No disposable output is needed for source implementation. Test temporary
directories are owned and cleaned by the existing test harness. Generated
release archives are not created or promoted under this authorization.

## Validation Commands

```bash
PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest \
  dev.plugins.dev-flow.tests.test_runtime_gates \
  dev.plugins.dev-flow.tests.test_continuous_execution_contract -v
PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest \
  dev.plugins.dev-flow.tests.test_checkpoint_compact_contract -v
PYTHONDONTWRITEBYTECODE=1 python3.12 dev/scripts/run_devflow_prepromotion_tests.py
openspec validate repair-stop-hook-conversation-scope --strict
openspec validate --all --strict
PYTHONDONTWRITEBYTECODE=1 python3.12 \
  dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo . --json
PYTHONDONTWRITEBYTECODE=1 python3.12 \
  dev/plugins/dev-flow/scripts/doctor_workflow.py --repo . --json
python3 dev/scripts/codex_auto_update_plugins_skills.py --json
plugin-eval analyze plugins/dev-flow --format markdown
git diff --check
```

## Risks / Trade-offs

- [A future Codex version persists side chats] → Re-run capability research and
  replace the applicability signal only through a new compatibility change;
  never parse transcript contents.
- [A legitimate ephemeral root conversation loses Stop enforcement] → This is
  an intentional safety boundary: non-durable conversations retain prompt-level
  orchestration but cannot own repository-level mechanical continuation.
- [Legacy payloads omit all scope fields] → Preserve existing enforcement rather
  than silently weakening older clients.
- [Doctor self-check becomes tautological] → Keep public entrypoint RED/GREEN
  tests as primary proof and use Doctor only to surface runtime invariant drift.
- [Source is fixed but installed behavior remains old] → Report source/release/
  cache drift and stop at the explicit release/cache authorization boundary.

## Migration Plan

1. Implement and verify only the development source and canonical change.
2. Run read-only release/cache drift checks and record the exact pending paths.
3. Under separate authorization, regenerate the release runtime, verify it,
   refresh only `dev-flow@cy-codex-skills`, and start a new conversation because
   active sessions may retain the loaded hook registry/runtime.

Rollback removes the additive scope module and Doctor field and restores the
prior entrypoint. No repository data or state migration is required.
