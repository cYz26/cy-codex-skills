# Task: <task name>

## Metadata

- Created: <yyyy-mm-dd>
- Owner: Codex / User
- Status: todo
- Source Request: <short summary>

## Skill Routing Ledger

- kind: <new-feature | bug-fix | workflow-repair | docs-only | tooling | other>
- workflow mode: <Full OpenSpec | Lightweight Ledger | Prototype Mode>
- capability-research: required/used/skipped - <reason>
- brainstorming: required/used/skipped - <reason>
- writing-plans: required/used/skipped/pending - <reason>
- openspec/gsd: required/used/skipped - <reason>
- Open Questions: <none | unresolved questions require brainstorming or explicit draft status>

## Target State

<Describe the complete final state.>

## Scope / Non-Goals

### In Scope

- <item>

### Non-Goals

- <item>

## Architecture Decisions

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| <decision> | <rationale> | <alternative> |

## Completion Contract

- [ ] <criterion>
- [ ] <validation evidence>

## Capability Slices

### Slice 1: <name>

**Status:** todo

**Goal**
- <goal>

**Files / Modules**
- <path or module>

**Implementation**
- [ ] <step>

**Tests**
- [ ] <test>

**Validation Commands**
```bash
<command>
```

**Done When**
- [ ] <done criterion>

**Risks / Rollback**
- <risk and rollback>

## Execution Log

| Time | Slice | Action | Result | Evidence |
|---|---|---|---|---|
| <time> | <slice> | <action> | <result> | <evidence> |

## Blockers

| Blocker | Impact | Options | Recommended Decision |
|---|---|---|---|
| <blocker> | <impact> | <options> | <decision> |

## Acceptance Criteria

- [ ] <criterion>

## Validation Commands

```bash
<command>
```

## Final Verification

- [ ] lint
- [ ] typecheck
- [ ] unit tests
- [ ] integration tests
- [ ] build
- [ ] smoke test
- [ ] docs updated
- [ ] review completed

## Local Reference Update Reminder

- [ ] If this task changed major Codex plugins or skills, remind the user to
  update local Codex references before relying on the changed behavior locally.
- [ ] Start dry-run: `python3 dev/scripts/codex_auto_update_plugins_skills.py --json`.
- [ ] Report release asset sync, installed plugin cache refresh needs, and
  project-local skill links migration.
- [ ] Apply only after explicit update intent or confirmation; record skipped
  local reference update reason and residual risk.

## Final Result

<Fill after completion.>
