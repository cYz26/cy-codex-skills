---
name: execute-task
description: Use when executing one approved OpenSpec task or configured lightweight ledger item.
---

# Execute Task

Execute one approved ledger item and leave fresh evidence.

## Capability Routing

Always resolve `test-first-execution` from `scripts/workflow_methodology.py`.
Resolve `root-cause-diagnosis` only for a hard bug, regression, or unexpected
behavior. Resolve `execution-orchestration` only when approved work is
delegated, parallelized, or isolated. Matt primitives add engineering
discipline but cannot replace OpenSpec tasks, DevFlow evidence, or the
Completion Contract.

Before editing, run selection-scoped diagnosis with the capabilities actually
triggered by the item, for example:

```bash
python3 scripts/check_dependencies.py --repo <repo> \
  --capability test-first-execution \
  --capability execution-orchestration --json
```

Use the same flags with `activate_project_dependencies.py` when activation is
needed. This is dry-run by default; project-local skill writes occur only in
explicit apply mode.

## Procedure

1. Read `AGENTS.md`, `.planning/devflow/STATE.md`, the active change or
   lightweight ledger, relevant source, Acceptance Criteria, and Validation
   Commands. For Full OpenSpec, read `openspec status --change <id> --json`
   and the applicable `openspec instructions <artifact> --change <id> --json`;
   use returned `artifactPaths` and `actionContext`.
2. Confirm the workflow route is executable. Full OpenSpec work proceeds
   through `openspec-apply-change`; Prototype Mode remains non-production.
3. Pick one unfinished Capability Slice or ledger item.
4. Add or update the failing test and record RED. Implement the smallest
   complete behavior, then run focused and broader checks.
5. Record changed files, commands, results, cleanup, and risks under
   `.planning/devflow/verification/`.
6. Update the task, Execution Ledger, and state only after evidence passes or a
   blocker is recorded.

## Incidental Finding Gate

Before expanding the selected item, classify the finding:

- `CONTINUE_WITH_MINIMAL_GUARD`: run at most one bounded RED/GREEN guard inside
  the approved contract and write set, then return to the Critical Path.
- `DEFER_AND_CONTINUE`: record evidence, affected contract, mitigation, reason,
  and recommended follow-up in the tracked `TASK_LEDGER.md`, then continue only
  when required behavior and acceptance remain safe.
- `BLOCKED_AWAITING_HUMAN`: stop mutation for severe harm, material scope or
  authority expansion, ambiguous ownership, or unresolved product decisions.

Required behavior and failing acceptance criteria cannot be deferred. For
`BLOCKED_AWAITING_HUMAN`, finish only safe read-only diagnosis, preserve the
work, record evidence/options/recommendation, and ask the human one concrete
decision. Promote that answer into OpenSpec or the active ledger before resuming.
The Finding Register does not authorize follow-up work.

## Delegated Execution

Delegation requires explicit authority, disjoint write sets, and a validated
Agent Task Contract. Run `scripts/validate_agent_task_contract.py` and record
its `contract_path`; shared files remain serialized
through the main agent. Each worker returns status (`DONE`,
`DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`), files changed or
inspected, tests, risks, and review needs. The main agent reviews the diff and
reruns validation.

Stop if scope, dependency, migration, public API, or acceptance behavior would
expand beyond the approved artifact. The item is complete only after its
validation command passes and its evidence is durable.
