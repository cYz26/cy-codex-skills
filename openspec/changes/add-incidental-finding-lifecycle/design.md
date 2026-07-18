## Context

DevFlow already requires approved scope, disjoint write sets, durable evidence,
and stop-on-expansion behavior. Those rules cover individual execution gates,
but they do not define what happens from the moment an incidental problem is
discovered through current-task completion and later human disposition. In
practice, a real but non-critical finding can pull an agent away from the
critical path, while a deferred finding can disappear into chat, local
`.planning` state, or an unconfirmed "future work" paragraph.

The lifecycle must work in Full OpenSpec and Lightweight Ledger modes without
creating another canonical planning system. It must distinguish a safe bounded
guard from optional hardening, stop on severe or authorization-expanding work,
and preserve the existing rule that required Completion Contract behavior may
not be deferred.

## Goals / Non-Goals

**Goals:**

- Define one exhaustive three-disposition lifecycle for incidental findings.
- Protect the active critical path with a structural finding budget and
  escalation triggers.
- Persist every deferred or blocked finding in tracked `TASK_LEDGER.md` so it
  survives task, context, and machine boundaries.
- Require severe findings to stop with evidence and one concrete human
  decision request.
- Require completion claims to disclose residual findings and ask whether a
  recommended follow-up should become the next change.
- Package the same rules in source skills and generated project templates.

**Non-Goals:**

- Automatically decide severity, edit a user's ledger, create a follow-up
  OpenSpec change, or resume execution without human input.
- Add a hook, daemon, schema, dependency, migration, separate findings file, or
  second execution queue.
- Turn every minor warning into a blocker or make non-blocking follow-up
  disposition a prerequisite for completing the current contract.
- Defer behavior that the active Completion Contract requires.
- Promote, release, install, refresh, commit, push, or archive the plugin in
  this change without a separate authorization.

## Decisions

### Use exactly three dispositions with fail-closed precedence

Every incidental finding receives one of these states:

1. `BLOCKED_AWAITING_HUMAN` when continuing would require material scope or
   authority expansion, could cause severe harm, or leaves a product decision
   unresolved.
2. `CONTINUE_WITH_MINIMAL_GUARD` when the finding blocks safe completion but a
   bounded RED/GREEN guard fits the approved contract and write set.
3. `DEFER_AND_CONTINUE` when the finding does not block the Completion Contract
   and current mitigation leaves the critical path safe.

The order is deliberate: any severe-stop trigger wins over a possible minimal
guard, and required behavior can never be relabeled as deferred. Unknown or
ambiguous severity fails closed to human review.

Alternative: use free-form severity labels. Rejected because labels such as P1
or "important" do not determine whether execution stops, continues, or records
a follow-up.

### Put the cross-change Finding Register in tracked TASK_LEDGER.md

`TASK_LEDGER.md` gains an Incidental Finding Register that is independent of
which artifact owns the active task sequence. Each finding records:

- stable finding ID and summary;
- disposition and severity;
- evidence and affected contract;
- impact and current mitigation;
- why the guard is bounded or why deferral is safe;
- recommended follow-up and trigger;
- human disposition: `pending`, `accepted`, `rejected`, or `deferred`.

OpenSpec remains canonical for active behavior and tasks. The register does not
authorize work and does not replace OpenSpec; an accepted follow-up becomes
executable only after the required OpenSpec or ledger intake is created and
approved. `.planning/devflow/` may link verification evidence but is not the
only durable record.

Alternative: add `INCIDENTAL_FINDINGS.md` or store only in `.planning`. Rejected
because the first creates another control-plane artifact and the second is not
guaranteed to survive a clone or cross-machine continuation.

### Make critical-path protection part of planning

Non-trivial plans record:

- the active Critical Path;
- the Incidental Finding Budget, normally one bounded RED/GREEN cycle within
  the approved write set;
- structural Escalation Triggers such as a new dependency, schema, public
  contract, parser or standards-conformance effort, architectural component,
  migration, external effect, destructive action, or expanded write set.

The budget is a review trigger, not a stopwatch. Once crossed, the finding must
be reclassified and the canonical plan or approval boundary updated before
production work continues.

Alternative: use elapsed-time or token budgets. Rejected because those values
vary by model and do not describe whether product scope has changed.

### Keep classification reasoned and evidence-backed rather than automated

The primary implementation surface is the DevFlow skills and templates. They
require the agent to classify, record, stop, resume, and report consistently.
Focused tests assert that the lifecycle is present across all public routing
surfaces and that development guidance remains source-of-truth.

No runtime classifier is added. Severity depends on product context and human
authority, while an automatic classifier would either miss severe cases or
over-block harmless findings. Existing validators continue to enforce their
own deterministic contracts.

Alternative: add a CLI that guesses disposition from flags or prose. Rejected
because it would duplicate the reasoning already required in intake and create
false enforcement confidence.

### Stop severe findings before mutation and resume only from durable approval

Severe triggers include data loss or corruption, security or authority bypass,
irreversible action, contradictory spec and test contracts, public behavior or
Completion Contract changes, production dependencies, schemas, migrations,
external effects, destructive work, ambiguous ownership, and unresolved
product tradeoffs.

Before stopping, the agent may finish safe read-only diagnosis. It then records
the finding, preserves current work, reports evidence, impact, why continuing
is unsafe, safe options, and a recommended decision, and asks one concrete
question. It performs no speculative fix. After the human answers, the decision
must be promoted into OpenSpec or the active ledger before work resumes.

Alternative: always attempt a minimal fix first. Rejected because a minimal
implementation can itself select an unapproved product or authority outcome.

### Separate current completion from follow-up authorization

A current task may complete with `DEFER_AND_CONTINUE` findings only when their
record proves they do not block the Completion Contract and identifies current
mitigation. The final completion claim lists all residual findings, recommended
order, and whether follow-up confirmation is pending. It explicitly asks the
human whether to accept, reject, or defer the proposed next change.

The agent must not start that follow-up until confirmed and promoted through
normal intake. Any `BLOCKED_AWAITING_HUMAN` finding blocks completion,
verification claims, archive readiness, and continuation.

Alternative: make every pending follow-up block current completion. Rejected
because optional hardening would again displace the critical path the lifecycle
is intended to protect.

## Risks / Trade-offs

- [Prompt guidance can be ignored] -> Repeat the same invariant across intake,
  planning, execution, completion, review, and generated project policy; add
  source-package contract tests.
- [The Finding Register becomes a shadow backlog] -> State that it carries no
  execution authority and requires normal intake/OpenSpec promotion.
- [Agents misuse deferral to avoid required work] -> Require an affected-
  contract field and a proof that the current Completion Contract remains safe.
- [Existing projects lack the new register] -> Do not fail migration; add the
  section non-destructively only when a finding is first recorded or the user
  explicitly refreshes project guidance.
- [A user does not answer the follow-up question] -> Keep the current task
  completion truthful and the tracked human disposition `pending`; do not start
  the follow-up.

## Migration Plan

1. Add source-package tests that define the public lifecycle surfaces.
2. Update source skills and templates plus this repository's own control plane.
3. Run source tests, strict OpenSpec validation, diff checks, and development-
   path Plugin Eval.
4. Leave `plugins/dev-flow/`, installed cache, project refresh, archive,
   release, commit, and push unchanged pending their separate authorization.

Rollback removes the additive guidance and Finding Register sections. No
runtime or project-data migration is required.

## Open Questions

None. The user explicitly selected durable recording, completion-time follow-up
confirmation, and severe human stop behavior.
