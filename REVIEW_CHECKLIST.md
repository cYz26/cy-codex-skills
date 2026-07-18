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

## Incidental Findings

- [ ] Every incidental finding has one lifecycle disposition and a durable
  `TASK_LEDGER.md` record when deferred or blocked
- [ ] No required behavior or failing acceptance criterion is labeled
  `DEFER_AND_CONTINUE`
- [ ] No unresolved `BLOCKED_AWAITING_HUMAN` finding remains
- [ ] The completion claim discloses residual findings and asks the human to
  accept, reject, or defer each recommended follow-up
- [ ] No follow-up work started before normal intake and approval

## Release / Archive Readiness

- [ ] TASK_LEDGER entries closed
- [ ] Evidence linked in `.planning/devflow/STATE.md`
- [ ] Knowledge update decision recorded
