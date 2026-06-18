---
name: context-health-check
description: Use when context rot, stale goals, retries, diff spread, or subagent risk appears.
---

# Context Health Check

Use this skill when a DevFlow task may be drifting, repeating failed work, expanding diff scope, missing validation evidence, or approaching a checkpoint/compact boundary.

## Procedure

1. Inspect current workflow state and repo truth:
   - `git status`
   - `git diff --stat`
   - `.planning/STATE.md`
   - latest `.planning/verification/`
   - active OpenSpec change files
2. Run the health check:

```bash
python3 scripts/context_health_check.py --repo <repo> --write-report --json
```

3. Interpret the decision:
   - `continue`: proceed with the next planned step.
   - `reconcile`: stop implementation and align against git diff, files, tests, and OpenSpec.
   - `checkpoint_compact`: run the existing `checkpoint-compact` flow before expanding work.
   - `checkpoint_new_thread`: create a checkpoint and use the report's minimal next context in a new thread.

## Goal Handling

Context-health is not the primary trigger for goal-backed execution. DevFlow
should apply the Goal Suitability Gate during intake or planning, before
context-health drift appears. Long-running, multi-slice, migration, release,
broad-refactor, cross-context, and subagent/delegation-backed work should route
to `define-goal` before execution when the definition of done is likely to
drift.

If the report says `goal.status` is `missing`, `stale`, `conflicting`, or
`weak`, do not assume memory is sufficient. Use `define-goal` to create or
repair a measurable objective with verification evidence, scope boundaries,
non-goals, and stop conditions.

After `define-goal` shapes the objective, set it in a Codex app, IDE, or CLI
composer with `/goal <objective>`. Use `/goal` to view the current goal and
`/goal pause`, `/goal resume`, or `/goal clear` to control it. If `/goal` is
not available, enable `features.goals` in Codex config or run
`codex features enable goals`. When `/goal` cannot be executed directly,
persist the generated Goal Mode Prompt in the next checkpoint.

## Subagent Handling

Evaluate subAgent usefulness at planning, execution, context-health, and review boundaries.
A recommendation is appropriate for repeated investigation pressure,
repeated command failures, diff spread across independent domains, or a bounded review or delegation need.

Subagent recommendations are advisory. Use them only when the user explicitly
wants subagents or delegated parallel work. The generated prompt scopes the
subagent to read-only exploration, disjoint write ownership, or diff-centric
review, and the main agent remains responsible for verification and durable
workflow evidence.

## Historical Session Import

For older Codex work that predates DevFlow context-health events, import best-effort local history:

```bash
python3 scripts/context_health_import_codex_sessions.py \
  --repo <repo> \
  --codex-home ~/.codex \
  --json
```

Imported history is partial. Treat missing context usage, prompt attribution, and tool schema attribution as unknown rather than healthy.

## Privacy

DevFlow context health stores only sanitized metadata. It must not store prompt bodies, file bodies, command output bodies, or raw tool payload bodies.
