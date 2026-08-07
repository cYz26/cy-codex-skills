# Project Refresh Procedure

Read this file only after global DevFlow freshness is established and a
specific project qualifies for refresh.

## Read-only diagnostics

Start with the deterministic one-project plan. It writes no report, state,
candidate, cache, or project file:

```bash
python3 dev/plugins/dev-flow/scripts/plugin_project_migration.py plan \
  --repo <project> --plugin-root <verified-dev-flow-root> --json
```

Record the returned `planSha256`, exact `readSet`/`writeSet`, action IDs,
authorizations, manual actions, preserved paths, source identity, and unrelated
worktree paths. Then run supplemental read-only diagnostics when present:

```bash
python3 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo <project> --json
python3 dev/plugins/dev-flow/scripts/doctor_workflow.py --repo <project> --check-cache-drift --json
python3 dev/plugins/dev-flow/scripts/inspect_legacy_workflow_config.py --repo <project> --json
git -C <project> status -sb
```

The plan incorporates the inspector's known provider lock, legacy hook/agent,
legacy Skill, and historical planning paths as redacted preserved/manual
evidence. Do not clean any of those paths as part of refresh.

For refresh contract revision 3, also record the implementation-readiness
surface status: packaged CLI/schemas, project-local Skill links, maintained
templates, compatibility fixture identity, and any pre-existing project-owned
Requirement/Evidence/Receipt namespace. These are inspection and managed-
refresh facts only. Missing project direction remains not applicable; existing
direction remains project-owned and is never synthesized, selected, or
rewritten by refresh.

Verify that the isolated, generated OpenSpec
1.7 skills and the DevFlow project-local Skill sources match the named plugin
identity before authorizing a project write.

For a non-Git project, report that `git status` is unavailable and list changed
workflow paths explicitly.

## Explicit sealed apply

Apply only the reviewed dependency-closed actions and named authorizations from
that exact plan. A complete apply commonly uses:

```bash
python3 dev/plugins/dev-flow/scripts/plugin_project_migration.py apply \
  --repo <project> --plugin-root <verified-dev-flow-root> \
  --expect-plan <sha256:...> \
  --allow project-refresh-apply \
  --allow workflow-config-migration --json
```

Repeat `--action <id>` to apply an explicitly selected safe subset. A safe
subset remains `applied_incomplete` while another action, authorization, or
manual item remains. Stale plans, unknown actions, incomplete dependencies,
ownership conflicts, path overlap, unsafe symlink ancestry, or changed before
fingerprints fail before the first project write.

The compatibility command remains available for older callers:

```bash
python3 dev/plugins/dev-flow/scripts/plugin_project_migration.py \
  --repo <project> --apply --json
```

It uses the same transaction engine for safe managed Skill links and missing
control-plane files, but never selects a `.dev-flow.json` rewrite or grants
`workflow-config-migration` authority.

## AGENTS Drift Gate

The planner checks the same durable markers as workflow validation. When an
authorized plan creates `AGENTS.md.generated`, compare it with active
`AGENTS.md`. Merge only
durable workflow rules, including Workflow Ownership, Project Control Plane,
Matt Methodology Contract, capability routing, and completion gates. Preserve
project-specific guidance. An existing divergent candidate is a conflict and is
never overwritten. Merge or retain the candidate explicitly, replan, then
rerun validation. Skill-link and cache freshness alone do not justify changing
`AGENTS.md`.

## Verification and rollback

Verify the apply receipt afresh:

```bash
python3 dev/plugins/dev-flow/scripts/plugin_project_migration.py verify \
  --repo <project> --plugin-root <verified-dev-flow-root> \
  --receipt <apply-receipt-path> --json
```

Verification covers managed-path readback, configuration schema, migration
sync, workflow validation, cache-drift diagnosis, AGENTS disposition, and
migration-state identity. `verified_incomplete` is attention, not completion.
For revision 3, verification additionally reports whether already-existing
readiness artifacts are current for the active consumer context; it does not
write or repair those artifacts and does not turn their state into provider or
ordinary implementation authority.

Rollback is receipt-bound and requires a second explicit apply flag:

```bash
python3 dev/plugins/dev-flow/scripts/plugin_project_migration.py rollback \
  --repo <project> --plugin-root <verified-dev-flow-root> \
  --receipt <apply-receipt-path> --json
python3 dev/plugins/dev-flow/scripts/plugin_project_migration.py rollback \
  --repo <project> --plugin-root <verified-dev-flow-root> \
  --receipt <apply-receipt-path> --apply --json
```

Rollback refuses a path edited after apply. Promotion or verification failure
returns `verification_failed_rolled_back` after complete restoration, or
`rollback_failed` with retained transaction evidence for manual recovery.
Receipt rollback is repository-, state-, and action-set-bound. Never edit or
copy a receipt between projects. Never delete receipts or retained recovery
evidence as routine cleanup; a retained transaction blocks later apply until a
human completes and records recovery.

For non-Git projects, diagnostics remain available and create-if-absent actions
may still be planned, but any rewrite requiring a Git rollback blob is
manual-only. Record changed files, receipts, migration status, AGENTS
disposition, skipped checks, conflicts, rollback status, and restart/new-session
need.
