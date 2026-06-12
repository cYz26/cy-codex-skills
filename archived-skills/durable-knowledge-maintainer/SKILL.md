---
name: durable-knowledge-maintainer
description: Close out tasks or run periodic durable-knowledge reviews in any Codex repo that uses AGENTS.md + docs/work + knowledge/, keeping task metadata, long-term docs, verification state, and emerging skill candidates in sync.
---

# Durable Knowledge Maintainer

Use this skill when a task is being closed, when durable findings may have been missed, or when a repository needs a deliberate knowledge-maintenance pass instead of leaving conclusions in task notes.

## Preconditions
- The target repo should already have:
  - `AGENTS.md`
  - `docs/work/`
  - `knowledge/`
- If those surfaces do not exist yet, use `agents-md-context-manager` first.

## Read first
1. `AGENTS.md`
2. `docs/work/.current`
3. the active task's `meta.yaml`, `status.md`, `decisions.md`, and `learning-log.md`
4. `knowledge/index.md`, `knowledge/sources.yaml`, and `knowledge/changelog.md`
5. every doc named by `related_knowledge`, `knowledge_targets`, or the repo's durable-knowledge protocol

## Workflow
1. Review the task-time learnings first.
   - ignore entries already marked `dismissed`
   - resolve whether each remaining entry stays `pending`, becomes `triaged`, or should be `promoted`
   - completed tasks must not leave relevant learning entries in `pending`
2. Decide whether the task introduced a durable change.
   - architecture, command, build, packaging, or validation flow changed
   - a new workaround, pitfall, or failure mode appeared
   - verification evidence or verification status changed
   - a new authoritative source was added or refreshed
   - a repeated workflow looks reusable across tasks or repos
3. If there is no lasting change:
   - set `knowledge_review_status: not_needed`
   - set `knowledge_reviewed_at`
   - dismiss or triage any non-durable learning entries and leave a short reason in the task status or follow-up fields
4. If durable change exists, map it to the correct targets.
   - repo rules -> `AGENTS.md`
   - implementation snapshot -> `knowledge/project/current-state.md`
   - recommended default -> the repo's standard-solution doc
   - failure pattern -> the repo's pitfalls doc
   - validation state -> the repo's verification matrix or equivalent
   - source freshness -> `knowledge/sources.yaml`
   - all durable edits -> `knowledge/changelog.md`
5. Update task bookkeeping.
   - set `knowledge_review_status`
   - set `knowledge_reviewed_at`
   - fill `knowledge_targets`
   - fill `knowledge_followups` for anything still blocked
   - fill `skill_candidates` when a reusable workflow appears
   - keep `Learning Capture` and `Promotion Queue` in `status.md` aligned with the learning-log outcome
6. Enforce honest validation language.
   - missing device or tool coverage is not `verified`
   - partially checked fixes stay partial
   - blocked validation stays blocked
7. Hand off reusable workflows.
   - if a workflow has stable inputs, outputs, and validation, create or update a candidate under `$CODEX_HOME/memories/durable-knowledge/skill-candidates/`
   - preserve the learning entry ids, `pattern_key`, and trigger types in candidate provenance
   - if a matching skill already exists, update its source doc or changelog instead of duplicating it
8. Close the loop.
   - completed tasks must not leave `knowledge_review_status: pending`
   - if `knowledge_review_status: followup_required`, make the follow-up explicit and durable
9. When running a weekly review instead of a single-task closeout, explicitly check for:
   - completed tasks missing `updated` or `not_needed`
   - active tasks missing `learning-log.md`
   - learning entries still `pending` more than 24 hours after capture
   - overdue `next_review_at` source entries
   - verification rows older than 7 days that are still `pending_validation`, `partially_verified`, or `blocked_by_missing_device_or_tooling`
   - unprocessed `Potential Skills` items and `skill_candidates`

## Default cadence
- Use `7` days as the default stale-review window unless the target repo documents a tighter cadence in `AGENTS.md`.

## Hard rules
1. Do not leave durable findings only in chat or ad hoc notes.
2. Do not mark unverified or blocked work as complete evidence.
3. Do not pollute `AGENTS.md` with one-off task chatter; only keep durable rules there.
4. Do not close a task while the durable-knowledge targets are still implicit.
5. Do not promote an unstable one-off procedure into a skill candidate without evidence.
6. Do not treat raw `pending` learning entries as durable truth until they are triaged.

## Deliverables
1. The task metadata reflects the durable review result.
2. The task `learning-log.md` reflects the final triage or promotion status.
3. The right long-term docs are updated.
4. `knowledge/changelog.md` records the durable update.
5. Any reusable workflow is either linked to an existing skill or handed off as a candidate.
