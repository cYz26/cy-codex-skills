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

If the report says `goal.status` is `missing`, `stale`, or `conflicting`, do not assume memory is sufficient. Use the generated Goal Mode Prompt in a Codex surface that supports `/goal`, or persist the prompt in the next checkpoint when `/goal` cannot be executed directly.

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
