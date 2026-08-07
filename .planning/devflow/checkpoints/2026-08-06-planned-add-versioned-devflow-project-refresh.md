# Checkpoint: Versioned DevFlow Project Refresh Planned

- Timestamp: 2026-08-06T13:02:37+08:00
- Change: `add-versioned-devflow-project-refresh`
- Stage: `awaiting_human`
- Artifact status: proposal, design, delta specs, and tasks complete
- Implementation progress: 0/37 tasks

## Target and Decision

Established DevFlow projects must be able to move from a supported older
workflow configuration to the current project contract through deterministic,
redacted planning, explicit transactional apply, fresh verification, and safe
rollback. Future DevFlow releases must fail closed when project-facing surfaces
change without a matching Project Refresh Impact decision and migration or
managed-refresh coverage.

The chosen boundary is `Skill + CLI`, not either component alone:

- keep the existing `dev-flow-refresh` Skill for global-first orchestration,
  discovery, Human Gates, AGENTS review, and evidence;
- deepen the existing `plugin_project_migration.py` CLI into the one project
  planner/writer;
- do not add a second migration CLI or a second filesystem writer.

## Planning Evidence

- Current legacy workflow inspection is intentionally read-only and redacted.
- Current project migration handles managed skill links and missing
  control-plane files but does not migrate established `.dev-flow.json`.
- Current scaffolding preserves an existing `.dev-flow.json` rather than
  upgrading it.
- The current migration state does not independently identify plugin release,
  engine schema, project workflow schema, and refresh-contract identity.
- Existing apply can encounter a later conflict after earlier writes; the new
  contract requires complete preflight and transaction rollback.
- Legacy-config tests pass 9/9, project-migration tests pass 14/14,
  orchestrator tests pass 48/48, release smoke tests pass 30/30, and the current
  refresh Skill passes quick validation.

## Durable Artifacts

- `openspec/changes/add-versioned-devflow-project-refresh/proposal.md`
- `openspec/changes/add-versioned-devflow-project-refresh/design.md`
- `openspec/changes/add-versioned-devflow-project-refresh/specs/devflow-project-refresh/spec.md`
- `openspec/changes/add-versioned-devflow-project-refresh/specs/devflow-plugin-quality/spec.md`
- `openspec/changes/add-versioned-devflow-project-refresh/tasks.md`
- `.planning/devflow/STATE.md`

Strict validation for the new change passes. No Open Questions remain in the
design. The Goal Contract is durable in the design; goal-tool creation is
recorded as skipped because it requires an explicit user request.

## Risks and Gates

- Configuration values must never leak into plans, receipts, errors, history,
  or rollback artifacts.
- Planning and apply must reject ambiguous baselines, stale managed inputs,
  untrusted filesystem shapes, and incomplete rollback before the first write.
- Active `AGENTS.md` remains merge-only; legacy cleanup remains separate.
- Generated release sync, installed-cache refresh, consumer-project apply,
  dependency changes, archive, commit, push, PR, and publication are not
  authorized by plan approval.
- The unrelated Git-transport evidence edit remains untouched.

## Next Action

Obtain explicit human approval of the OpenSpec plan. On approval, begin task
1.1 with `openspec-apply-change` and `execute-task`, then continue automatically
through source verification. Stop at task 7.1 for the separate generated-
release synchronization gate.
