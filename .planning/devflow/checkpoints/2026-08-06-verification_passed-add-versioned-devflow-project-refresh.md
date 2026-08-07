---
checkpoint_id: 2026-08-06-verification_passed-add-versioned-devflow-project-refresh
created_at: 2026-08-06T19:09:44+08:00
boundary: verification_passed
project_mode: brownfield
change_id: add-versioned-devflow-project-refresh
compact_recommended: true
compact_status: pending
next_stage: feature_intake
---

# Checkpoint: verification passed for add-versioned-devflow-project-refresh

## Current goal

Deliver and verify versioned reversible DevFlow Project Refresh without crossing cache, consumer-project, archive, or Git gates.

## Completed work

- Completed all 37 OpenSpec tasks including authorized generated-release promotion.
- Verified 113 focused project tests, 79 focused release tests, 499 full tests, runtime parity, Skills, strict OpenSpec, Plugin Eval, and read-only reference identities.

## Durable context written

- AGENTS.md
- .planning/devflow/STATE.md
- openspec/changes/add-versioned-devflow-project-refresh/proposal.md
- openspec/changes/add-versioned-devflow-project-refresh/design.md
- openspec/changes/add-versioned-devflow-project-refresh/tasks.md

## Key decisions

- Generated release was synchronized only through the one-time repo-and-target-bound promotion gate.
- The post-promotion fixture allowlist gap was repaired as a bounded release-contract guard.

## Open questions

- None inside this completed change; archive and external effects remain separate gates.

## Risks

- DF-IFL-001 plugin-wide static token budgets remain a non-blocking separately scoped residual.
- The unrelated Git-transport evidence diff remains user-owned and untouched.

## Validation performed

```text
command: See openspec/changes/add-versioned-devflow-project-refresh/evidence/verification.md for the exact fresh verification matrix.
result: pass
notes: Generated release is current; runtime status verified; Plugin Eval 86/B with zero failures; source, release, and named cache Project Refresh identities match.
```

## Git state

```text
branch: main
changed_files:
  - M AGENTS.md
  -  M ENGINEERING_POLICY.md
  -  M REVIEW_CHECKLIST.md
  -  M TASK_LEDGER.md
  -  M dev/plugins/dev-flow/.codex-plugin/project-migration.json
  -  M dev/plugins/dev-flow/.codex-plugin/release-sync.json
  -  M dev/plugins/dev-flow/README.md
  -  M dev/plugins/dev-flow/assets/templates/AGENTS.md.template
  -  M dev/plugins/dev-flow/assets/templates/ENGINEERING_POLICY.md.template
  -  M dev/plugins/dev-flow/assets/templates/EVIDENCE_TEMPLATE.md.template
  -  M dev/plugins/dev-flow/assets/templates/OPENSPEC_DESIGN.md.template
  -  M dev/plugins/dev-flow/assets/templates/OPENSPEC_TASKS.md.template
  -  M dev/plugins/dev-flow/assets/templates/REVIEW_CHECKLIST.md.template
  -  M dev/plugins/dev-flow/scripts/codex_auto_update_plugins_skills.py
  -  M dev/plugins/dev-flow/scripts/legacy_workflow_config.py
  -  M dev/plugins/dev-flow/scripts/plugin_project_migration.py
  -  M dev/plugins/dev-flow/scripts/verify_release_runtime.py
  -  M dev/plugins/dev-flow/scripts/workflow_doctor.py
  -  M dev/plugins/dev-flow/scripts/workflow_project_skill_install.py
  -  M dev/plugins/dev-flow/scripts/workflow_release_verification.py
  -  M dev/plugins/dev-flow/skills/ai-native-tech-plan/SKILL.md
  -  M dev/plugins/dev-flow/skills/change-plan/SKILL.md
  -  M dev/plugins/dev-flow/skills/dev-flow-refresh/SKILL.md
  -  M dev/plugins/dev-flow/skills/dev-flow-refresh/references/project-refresh.md
  -  M dev/plugins/dev-flow/skills/execute-task/SKILL.md
  -  M dev/plugins/dev-flow/skills/plugin-project-migration/SKILL.md
  -  M dev/plugins/dev-flow/skills/verify-and-archive/SKILL.md
  -  M dev/plugins/dev-flow/tests/test_legacy_workflow_config.py
  -  M dev/plugins/dev-flow/tests/test_plugin_project_migration.py
  -  M dev/plugins/dev-flow/tests/test_project_orchestrator.py
  -  M dev/plugins/dev-flow/tests/test_release_sync.py
  -  M dev/scripts/run_devflow_prepromotion_tests.py
  -  M openspec/changes/separate-git-transport-from-github-auth/evidence/implementation.md
  -  M plugins/dev-flow/.codex-plugin/project-migration.json
  -  M plugins/dev-flow/.codex-plugin/release-sync.json
  -  M plugins/dev-flow/README.md
  -  M plugins/dev-flow/assets/templates/AGENTS.md.template
  -  M plugins/dev-flow/assets/templates/ENGINEERING_POLICY.md.template
  -  M plugins/dev-flow/assets/templates/EVIDENCE_TEMPLATE.md.template
  -  M plugins/dev-flow/assets/templates/OPENSPEC_DESIGN.md.template
  -  M plugins/dev-flow/assets/templates/OPENSPEC_TASKS.md.template
  -  M plugins/dev-flow/assets/templates/REVIEW_CHECKLIST.md.template
  -  M plugins/dev-flow/scripts/devflow_runtime.MANIFEST.json
  -  M plugins/dev-flow/scripts/devflow_runtime.SOURCE_COMMIT
  -  M plugins/dev-flow/scripts/devflow_runtime.pyz
  -  M plugins/dev-flow/scripts/devflow_runtime.sha256
  -  M plugins/dev-flow/skills/ai-native-tech-plan/SKILL.md
  -  M plugins/dev-flow/skills/change-plan/SKILL.md
  -  M plugins/dev-flow/skills/dev-flow-refresh/SKILL.md
  -  M plugins/dev-flow/skills/dev-flow-refresh/references/project-refresh.md
  -  M plugins/dev-flow/skills/execute-task/SKILL.md
  -  M plugins/dev-flow/skills/plugin-project-migration/SKILL.md
  -  M plugins/dev-flow/skills/verify-and-archive/SKILL.md
  - ?? dev/plugins/dev-flow/assets/project-refresh/
  - ?? dev/plugins/dev-flow/fixtures/project-refresh/
  - ?? dev/plugins/dev-flow/schemas/project-refresh-contract.schema.json
  - ?? dev/plugins/dev-flow/schemas/project-refresh-plan.schema.json
  - ?? dev/plugins/dev-flow/schemas/project-refresh-receipt.schema.json
  - ?? dev/plugins/dev-flow/scripts/workflow_project_refresh.py
  - ?? dev/plugins/dev-flow/tests/test_project_refresh.py
  - ?? plugins/dev-flow/assets/project-refresh/
  - ?? plugins/dev-flow/fixtures/project-refresh/
  - ?? plugins/dev-flow/schemas/project-refresh-contract.schema.json
  - ?? plugins/dev-flow/schemas/project-refresh-plan.schema.json
  - ?? plugins/dev-flow/schemas/project-refresh-receipt.schema.json
```

## Next action

The next stage should start by reading:

1. `AGENTS.md`
2. `.planning/devflow/STATE.md`
3. this checkpoint file
4. relevant OpenSpec change files
5. relevant verification and task-ledger files

Then proceed to: `feature_intake`.

## Compact instruction

Compact is recommended before feature_intake; run `/compact` at a stable boundary or continue from the checkpoint if automatic compaction/recovery is available.
If compaction is unavailable or not needed, repository files and this checkpoint remain the handoff source of truth.
