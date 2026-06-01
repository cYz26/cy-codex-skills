---
name: kb-promote
description: Use when repeated AgentKB lessons should become playbooks, ADRs, skills, or context packs.
---

# KB Promote

Use when a preference, workflow lesson, failure pattern, or recurring answer appears often enough to become durable knowledge.

AgentKB keeps Markdown as the canonical storage format. Load the smallest sufficient context first, and make every write reviewable with Git diff.

## Context Order

1. Read the project `context-pack.md`.
2. Read `_system/promotion-policy.md`.
3. Read relevant logs, reflections, candidates, and open questions.
4. Read the target playbook, decision, skill, or proposed change only if promotion is justified.

Do not read `personal/` unless the current user request explicitly authorizes extracting from personal notes.

## Promotion Thresholds

Promote when at least one of these is true:

- The same failure pattern appears more than once.
- A review or user correction identifies a stable workflow gap.
- A lesson is broadly applicable across projects, plugins, or skills.
- The lesson needs a prevention mechanism that future agents must discover
  before acting.

Do not promote a single low-confidence incident directly into a project rule.
Keep it in a log, reflection, or `proposed-changes/` note until the evidence is
stable.

## Promotion Paths

- One-time event: task log
- Repeated pattern: reflection or playbook
- Stable workflow: playbook or skill
- Project rule: `AGENTS.md` proposed change
- Architecture decision: ADR or decisions note
- Task-start context: context-pack refresh
- Executable prevention: test, lint, runtime guard, or eval case
- Personal/work extract: `projects/<project>/candidates/`
- Team-shareable extract: `promotion/candidates/`

## Procedure

1. Cite the repeated evidence.
2. Choose the smallest durable destination that future agents will actually
   read before repeating the mistake.
3. Preserve the prevention mechanism from the reflection, or explicitly record
   why it is deferred.
4. Avoid changing accepted ADRs directly.
5. Put high-impact changes in `proposed-changes/`.
6. Review the Git diff.
