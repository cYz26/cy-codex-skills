---
name: context-health-check
description: Use when context rot, stale goals, retries, diff spread, or subagent risk appears.
---

# Context Health Check

Use when a DevFlow task may be drifting, repeating failures, spreading its
diff, missing evidence, or approaching a checkpoint/compact boundary.

## Procedure

1. Inspect `git status`, `git diff --stat`, `.planning/devflow/STATE.md`, the
   latest verification record, and active OpenSpec change files.
   If `.planning/devflow/implementation-readiness/<change>/` exists, inspect its
   Requirement, Evidence, current Receipt, semantic bindings, and override
   state without rewriting any document.
2. Run the health check:

```bash
python3 scripts/context_health_check.py --repo <repo> --write-report --json
```

3. Interpret the decision:
   - `continue`: proceed with the next planned step.
   - `reconcile`: stop implementation and align against git diff, files, tests, and OpenSpec.
   - `checkpoint_compact`: run the existing `checkpoint-compact` flow before expanding work.
   - `checkpoint_new_thread`: create a checkpoint and use the report's minimal next context in a new thread.

## Goal and Delegation Gate

Context health repairs drift; intake or planning owns the primary Goal
Suitability Gate. If `goal.status` is `missing`, `stale`, `conflicting`, or
`weak`, use `define-goal` and require evidence, boundaries, non-goals, stop
conditions, and the Goal Quality Gate.

Evaluate subAgent usefulness at
planning, execution, context-health, and review boundaries. Recommend it for
repeated investigation pressure or command failures, independent diff spread,
or a bounded review or delegation need. Resolve every `disposition: pending`
with `record_context_health_disposition.py`.

Before changing a goal or recording any delegation disposition, read
`references/goal-and-delegation.md`. Record `accepted` only when explicit user
authorization or an approved delegated workflow exists and the Agent Task
Contract validates; otherwise record `declined` or `blocked`. A read-only
explorer or reviewer must keep its stated scope; any edit or expansion is a
Human Gate for the main agent.

## Historical Recovery and Privacy

For work that predates DevFlow events, read `references/session-recovery.md`
before importing session history. Missing usage or attribution stays unknown.
Store only sanitized metadata, never prompts, file or command bodies, or raw
tool payloads.

Readiness drift is not context drift to auto-repair. Report the stable issue
codes and exact next action; never select a provider, refresh evidence, record
an override, or promote a Requirement from this diagnostic route.
