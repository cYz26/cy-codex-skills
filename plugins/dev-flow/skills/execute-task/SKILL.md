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
   When DevFlow refresh-sensitive bytes change, update the approved Project
   Refresh Impact evidence, contract revision, schema/migration decision, and
   fixtures in the same item; never leave that synchronization to a later
   unowned release step.
6. Update the task, Execution Ledger, and state only after evidence passes or a
   blocker is recorded.

## Generated Artifact Contract

When the selected item will create disposable filesystem output, seal a
Generated Artifact Contract before the owning command runs. Prefer one
task/run-specific isolated root. A contract written after output exists,
self-authored worker evidence, filenames, extensions, ignore rules, or apparent
cache/build semantics never grant cleanup authority.

After the owner exits, run read-only observation and planning. Only a fresh
`AUTO_CLEAN` plan may proceed to explicit `cleanup --apply`; `WAIT_OWNER`
retries later, `RETAIN` preserves the output, and `HUMAN_GATE` stops automatic
reclamation. Keep the immutable contract, manifest, plan, and cleanup receipt
under `.planning/devflow/` and pass their references to
`record_task_evidence.py`.

For a referenced Agent Task Contract, rerun
`validate_agent_task_contract.py --worker-result <canonical-result.json>`.
G41 passes only when the worker result references a bound terminal cleanup
receipt and sets `cleanup_complete` to true. Without a Generated Artifact
Contract, existing validation behavior remains unchanged and no cleanup
authority is inferred.

## Completion Receipt and Return

Return a completion receipt for the selected item with item ID, result, changed
files, RED/GREEN evidence, focused and broader commands, residual risks,
blocker/Human Gate status, and whether another approved item is dependency-
ready. Return to `project-orchestrator` after every receipt. Completing one item
does not end the user request: the orchestrator derives the continuation outcome
and normally selects the next approved item immediately.

Do not ask for routine confirmation after an item, slice, review, or
verification boundary. If a genuine Human Gate is reached, record the exact
decision or authority needed and stop as `AWAIT_HUMAN`; otherwise the receipt is
eligible for `CONTINUE_NEXT_ITEM`, `CHECKPOINT_AND_CONTINUE`, or
`VERIFY_ACTIVE_CHANGE`.

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

Stop the item if scope, dependency, migration, public API, or acceptance
behavior would expand beyond the approved artifact. The item is complete only
after its validation command passes and its evidence is durable; that bounded
item completion returns control to the orchestrator rather than ending overall
execution.
