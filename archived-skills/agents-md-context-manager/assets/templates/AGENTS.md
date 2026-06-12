# AGENTS.md

## Project overview
- Goal:
- Scope:
- Out of scope:
- Product design source of truth: `<path-to-design-doc>`

## Tech stack
- Languages:
- Frameworks:
- Package/build tools:
- Data/storage:

## Architecture
- Module boundaries:
- Data flow:
- Integration points:

## Commands
- Install: `<command>`
- Dev: `<command>`
- Test: `<command>`
- Build: `<command>`

## Code style
- Formatting/linting:
- Naming conventions:
- File organization rules:

## Patterns to follow
1.
2.
3.

## Things to avoid
1.
2.
3.

## Task linkage
- Work directory: `docs/work/<task-id>-<feature>/`
- Active pointer: `docs/work/.current`
- Required files: `meta.yaml`, `spec.md`, `status.md`, `decisions.md`, `learning-log.md`
- Resolve priority:
  1. user-provided task id/url
  2. `.current` pointer
  3. branch parsing
  4. fallback `TODO-*` task folder

## Knowledge base
- Index: `knowledge/index.md`
- Source registry: `knowledge/sources.yaml`
- Change log: `knowledge/changelog.md`
- Local snapshots: `knowledge/authoritative/`
- Project knowledge: `knowledge/project/`
- Design docs (canonical): `knowledge/project/design/`
- Review cadence: `7` days

## Self-Improvement Protocol
- Capture triggers:
  - unexpected command, tool, or integration failure
  - user correction or clarified requirement
  - self-correction after discovering the earlier approach was wrong
  - newly discovered repo convention or undocumented rule
  - repeated workflow worth simplifying or reusing
  - missing capability that blocked task progress
- Capture surface:
  - append raw task-time learnings to `docs/work/<task>/learning-log.md`
  - each entry records `id`, `type`, `logged_at`, `status`, `trigger`, `summary`, `details`, `related_files`, `pattern_key`, `promotion_target`, and `see_also`
  - keep only derived summaries in `status.md` under `Learning Capture` and `Promotion Queue`
- Triage states:
  - `pending`: captured but not yet confirmed
  - `triaged`: confirmed and mapped to the right durable target
  - `promoted`: durable docs or candidate records were actually updated
  - `dismissed`: non-durable noise, superseded, or out of scope
- Guardrails:
  - raw learning entries must not update `AGENTS.md` directly
  - only triaged or promoted learnings may change durable docs or skill-candidate records
  - completed tasks must not leave relevant learning entries in `pending`

## Durable Knowledge Protocol
- Trigger:
  - architecture, command, packaging, or validation changes
  - repeated errors, pitfalls, or workaround patterns
  - new or changed authoritative knowledge sources
  - new durable verification evidence or changed verification status
  - repeated workflow steps that may deserve a reusable skill
- Task-close gate:
  - before marking a task complete, set `knowledge_review_status` in `docs/work/<task>/meta.yaml`
  - allowed values: `pending`, `not_needed`, `updated`, `followup_required`
  - if `followup_required`, record the missing updates in `knowledge_followups`
  - review `learning-log.md` before closing the task and resolve relevant `pending` entries first
- Update targets:
  - rules/policy changes -> `AGENTS.md`
  - implementation snapshot changes -> `knowledge/project/current-state.md`
  - durable solution guidance -> `knowledge/project/`
  - source freshness or watch mappings -> `knowledge/sources.yaml`
  - all durable changes -> `knowledge/changelog.md`
- Skill-candidate rule:
  - if a workflow or pitfall-response pattern repeats across at least two tasks or repositories and has stable inputs, outputs, and validation, add it to `skill_candidates` and promote it into the durable-knowledge candidate flow
- Review window:
  - default stale threshold is `7` days unless the repository makes it stricter

## Update protocol
- Trigger:
  - architecture or command changes
  - self-improvement capture or triage workflow changes
  - repeated errors/pattern gaps
  - new or changed authoritative knowledge sources
  - new or changed durable verification conclusions
  - repeated workflow patterns that may deserve a reusable skill
  - task workflow changes
  - design docs added/moved/rewritten
- Workflow:
  1. read existing AGENTS.md
  2. review the active task metadata, `learning-log.md`, and durable-knowledge status first
  3. edit impacted sections only
  4. update task linkage, self-improvement, and knowledge metadata if needed
  5. append update log entry
- Owner:

## Update log
- YYYY-MM-DD: initialized or updated <sections>, reason: <reason>
