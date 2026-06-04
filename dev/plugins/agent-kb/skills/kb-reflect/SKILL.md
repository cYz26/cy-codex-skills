---
name: kb-reflect
description: Use when failures, corrections, or review findings should become AgentKB knowledge.
---

# KB Reflect

Use after failures, user corrections, review findings, repeated tool mistakes, or context misses.
Start from `_agent/problem-signals/` or `projects/<project>/proposed-changes/problem-reflections/`
when automatic hooks or `kb_problem.py record` captured evidence.

AgentKB keeps Markdown as the canonical storage format. Load the smallest sufficient context first, and make every write reviewable with Git diff.

## Context Order

1. Read the project `context-pack.md`.
2. Read `_system/write-policy.md`.
3. Read relevant problem signals, reflection drafts, task logs, and open questions.
4. Read only the notes needed to understand the failure.

Do not read `personal/` or `archive/` unless the user explicitly authorizes it.

## Reflection Record

Capture these fields when turning an incident into durable knowledge:

- **Incident:** What failed, where, and what evidence proves it.
- **Root Cause:** The missing assumption, context, rule, guard, or validation.
- **Generalized Lesson:** The reusable rule that applies beyond this incident.
- **Prevention Mechanism:** The concrete enforcement surface, such as a test,
  lint, runtime guard, eval case, AGENTS proposed change, playbook, skill
  update, or context-pack refresh.
- **Validation:** The command, review, or runtime check that proves the
  mechanism works.
- **Residual Risk:** What remains unfixed and where follow-up should happen.

## Procedure

1. Describe what failed and why in a concise log entry.
2. Identify whether the issue is a one-time mistake, repeated pattern, missing context, unclear rule, or missing validation.
3. Extract a generalized lesson without overfitting to a single command, file,
   or person.
4. Choose a prevention mechanism. Prefer executable checks or workflow gates
   when the lesson can be enforced mechanically.
5. Decide whether to update a log, `open-questions.md`, a playbook,
   `AGENTS.md` proposed change, eval case, test, guard, skill, or context-pack.
6. Keep low-confidence reflections in `proposed-changes/`.
7. If a personal/work lesson may help a project, put the sanitized extract in `projects/<project>/candidates/`.
8. Review the Git diff.

## Promotion Rule

One incident goes to a log or reflection. Repeated, stable lessons can be
promoted by `kb-promote`.

Do not treat knowledge-base prose as the only fix when the issue can recur in
execution. Pair the reflection with a prevention mechanism or record why that
mechanism is intentionally deferred.
