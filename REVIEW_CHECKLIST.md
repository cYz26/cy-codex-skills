# Review Checklist

## Correctness

- [ ] Acceptance criteria checked line-by-line
- [ ] Failure mode or regression path covered
- [ ] No unverified success claims

## Test / Verification

- [ ] Required validation commands ran fresh
- [ ] TDD RED/GREEN evidence attached when required
- [ ] Build, lint, and test outputs were read

## Scope Control

- [ ] No unrelated refactor
- [ ] No unmanaged dependency change
- [ ] Shared canonical files updated only by their owner

## Continuous Execution

- [ ] The active Full OpenSpec task list, or the configured fallback ledger,
  is the single execution source
- [ ] No item, phase, review, verification, or checkpoint boundary was treated
  as a Human Gate without a concrete decision or authority
- [ ] Every non-terminal completion receipt returned to the orchestrator with
  the next continuation outcome
- [ ] External effects remain separately authorized and unexecuted unless the
  exact gate was approved

## Incidental Findings

- [ ] Every incidental finding has one lifecycle disposition and a durable
  `TASK_LEDGER.md` record when deferred or blocked
- [ ] No required behavior or failing acceptance criterion is labeled
  `DEFER_AND_CONTINUE`
- [ ] No unresolved `BLOCKED_AWAITING_HUMAN` finding remains
- [ ] The completion claim discloses residual findings and asks the human to
  accept, reject, or defer each recommended follow-up
- [ ] No follow-up work started before normal intake and approval

## Implementation Readiness

- [ ] Any project-selected external provider has an active-plan-bound v1
  Requirement; no selection was inferred from chat or repository presence
- [ ] Requirement, Evidence, current Receipt, consumer, semantic plan, target,
  provider artifact, capabilities, limitations, and evaluator bindings match
- [ ] Ready is composed with ordinary authority and is not treated as task,
  dependency, credential, release, cache, migration, Git, or archive approval
- [ ] Override and unresolved states fail closed without discovery, automatic
  fallback, provider installation, activation, or command execution

## Release / Archive Readiness

- [ ] Project Refresh Impact is `changed`, `verified-unchanged`, or
  `not-applicable` with fresh tracked-input and schema/migration evidence
- [ ] Immutable config targets, supported fixture paths, packaged CLI/Skill
  references, and source/release/cache contract identities pass their gates
- [ ] TASK_LEDGER entries closed
- [ ] Evidence linked in `.planning/devflow/STATE.md`
- [ ] Knowledge update decision recorded
