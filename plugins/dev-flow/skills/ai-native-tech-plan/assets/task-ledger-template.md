# Task: <task name>

## Metadata

- Created: <yyyy-mm-dd>
- Owner: Codex / User
- Status: todo
- Source Request: <short summary>

## Skill Routing Ledger

- kind: <new-feature | bug-fix | workflow-repair | docs-only | tooling | other>
- workflow mode: <Full OpenSpec | Lightweight Ledger | Prototype Mode>
- artifact-status: draft/final - <unresolved questions require draft>
- capability-research: required/used/skipped - <reason>
- decision-resolution: required/used/skipped - <reason>
- decision-grilling: required/used/skipped - <reason>
- implementation-planning: required/used/skipped/pending - <reason>
- architecture-guidance: required/used/skipped - <reason>
- domain-language-modeling: required/used/skipped - <reason>
- openspec-routing: required/used/skipped - <reason>
- Open Questions: <none | unresolved questions require decision-resolution plus decision-grilling or explicit draft status>

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

## Continuation Policy

- Execution policy: `auto-until-terminal`
- Canonical execution source: <active OpenSpec tasks | TASK_LEDGER.md>
- Item completion outcome: <next-item selection rule>
- Genuine Human Gates: <explicit decisions or authorities; phase labels do not qualify>
- External-effect gates: <release/archive/Git/dependency/migration/destructive actions>

## Generated Artifact Strategy

- Applicability: <not-applicable | registration-only>
- Contract: <standalone pre-creation contract path | not-applicable>
- Scope: <task/run isolated root | constrained adjacent output>
- Retention: <cleanup | retain | promote>
- Evidence: <manifest, fresh plan, cleanup receipt, G41 when delegated>
- Unsafe state: <exact Human Gate rule; no retroactive ownership>

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

## Execution Ledger

| Item | Owner | Write Set | Evidence | Human Gate | Next Outcome | Status |
|---|---|---|---|---|---|---|
| <item> | <owner> | <paths> | <required proof> | <none or explicit gate> | <continuation outcome> | todo |

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
