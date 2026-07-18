## Why

DevFlow tells workers to stop on scope expansion and to report residual risks,
but it does not define one end-to-end lifecycle for incidental findings. As a
result, agents can over-invest in a non-critical problem, lose deferred work in
chat or local state, or finish without asking the human whether the recorded
follow-up should become the next change.

## What Changes

- Add three normative incidental-finding dispositions:
  `CONTINUE_WITH_MINIMAL_GUARD`, `DEFER_AND_CONTINUE`, and
  `BLOCKED_AWAITING_HUMAN`.
- Require every non-trivial plan to define its critical path, incidental-
  finding budget, and structural escalation triggers.
- Reuse tracked `TASK_LEDGER.md` as the cross-change Finding Register, with
  evidence, impact, current mitigation, disposition reason, recommended
  follow-up, and human disposition. Do not add another state store.
- Require execution to classify a finding before expanding work, preserve
  required Completion Contract behavior, and fail closed on severe or
  authorization-expanding findings.
- Require completion and archive review to disclose residual findings, explain
  why deferred items do not block completion, and request explicit human
  confirmation before starting a follow-up change.
- Package the lifecycle in DevFlow skills and generated project templates with
  source-package tests. Release promotion and installed-cache refresh remain
  separate authorization gates.

## Capabilities

### New Capabilities

- `incidental-finding-lifecycle`: Critical-path protection, finding
  classification, durable follow-up recording, human escalation, and
  completion-time follow-up confirmation.

### Modified Capabilities

None.

## Impact

- Updates DevFlow planning, intake, execution, completion, and orchestration
  skill guidance under `dev/plugins/dev-flow/skills/`.
- Updates root control-plane guidance and generated AGENTS, engineering policy,
  task ledger, evidence, review, and OpenSpec plan templates.
- Adds focused source-package contract coverage without a runtime dependency,
  hook, new project file, migration, destructive action, or automatic write.
- Leaves generated `plugins/dev-flow/`, plugin release, archive, commit, push,
  and installed cache unchanged until separately authorized.

## Skill Routing Ledger

- `artifact-status`: final — the user confirmed the lifecycle and requested
  implementation.
- `kind`: workflow behavior change.
- `workflow-mode`: Full OpenSpec — public planning, execution, and completion
  behavior changes.
- `capability-research`: skipped — the solution depends only on current local
  DevFlow contracts already inspected; no unstable external capability is
  involved.
- `decision-resolution`: used — the conversation resolved classification,
  persistence, completion reporting, and severe-stop behavior.
- `decision-grilling`: skipped — no Open Questions remain after the user
  confirmed the desired mechanism.
- `implementation-planning`: used — this change requires coordinated skill,
  template, test, and verification slices.
- `architecture-guidance`: used — the design must avoid a second state store
  and preserve OpenSpec/DevFlow ownership.
- `domain-language-modeling`: used — the three dispositions and Finding
  Register fields are new workflow-domain concepts with invariants.
- `openspec-routing`: used — behavior and compatibility changes are canonical
  in this OpenSpec change.
