## Why

The DevFlow aggregate Stop hook applies repository-wide continuation state to
every Codex conversation in the same working directory and ignores Codex's
reentrancy signal. A side conversation can therefore inherit the main
conversation's unfinished OpenSpec queue, receive `decision: "block"`, and be
continued repeatedly even though it owns no executable work.

## What Changes

- Make the Stop hook consume the current Codex lifecycle payload before
  evaluating repository continuation policy.
- Treat a turn already continued by Stop as a valid one-shot boundary and emit
  no second blocking response.
- Keep repository-level automatic continuation out of ephemeral conversations
  that have no persistent transcript; those conversations remain read-only and
  must not consume a durable conversation's execution queue.
- Preserve blocking behavior for the first Stop attempt in a durable
  conversation with approved executable work.
- Add public command-entry regressions and a Workflow Doctor protocol self-check
  so reentrancy and conversation-scope drift are detected before release.

## Capabilities

### New Capabilities

- `stop-hook-conversation-scope`: Defines one-shot Stop continuation and the
  durable-conversation boundary for repository-level execution enforcement.

### Modified Capabilities

None. The completed `continuous-execution-contract` change remains historical;
this repair adds the missing hook lifecycle/applicability contract without
rewriting that completed change.

## Impact

- Development runtime:
  `dev/plugins/dev-flow/scripts/devflow_stop_hook.py`, a small pure scope helper,
  and Workflow Doctor reporting.
- Tests:
  `dev/plugins/dev-flow/tests/test_runtime_gates.py` and focused continuous-
  execution coverage.
- Compatibility: current Codex `Stop` fields `stop_hook_active`, `session_id`,
  and `transcript_path`; legacy payloads that omit scope fields retain existing
  fail-closed behavior.
- No dependency, workflow-state schema, transcript parser, task mutation, or
  external effect is introduced.
- Generated release promotion, installed-cache refresh, archive, commit, and
  push remain separate authorization gates.

## Skill Routing Ledger

- artifact-status: final
- kind: workflow repair and Codex Hook compatibility change
- workflow-mode: Full OpenSpec
- capability-research: required/used — current Codex Hook and side-conversation
  behavior determines the safe applicability contract.
- decision-resolution: required/used — selected one-shot and durable-transcript
  boundaries from current platform evidence; no Open Questions remain.
- decision-grilling: skipped — the user approved the diagnosed systemic repair
  and current evidence resolves the implementation choice without another
  product decision.
- implementation-planning: required/used — proposal, design, delta spec, tasks,
  validation, rollback, and write sets are durable in this change.
- architecture-guidance: required/used — separates pure hook scope from
  repository continuation policy and Doctor reporting.
- domain-language-modeling: skipped — no new business-domain vocabulary or
  invariants are introduced.
- openspec-routing: required/used — behavior and compatibility changes require
  Full OpenSpec.

## Goal Suitability Gate

Goal mode is not required. This is a bounded, single-agent OpenSpec repair with
an explicit completion contract, write set, validation surface, and stop
conditions; a second goal state would duplicate the canonical change.
