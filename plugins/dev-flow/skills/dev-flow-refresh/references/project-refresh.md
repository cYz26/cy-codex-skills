# Project Refresh Procedure

Read this file only after global DevFlow freshness is established and a
specific project qualifies for refresh.

## Read-only diagnostics

Run before every project apply:

```bash
python3 dev/plugins/dev-flow/scripts/plugin_project_migration.py --repo <project> --json
python3 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo <project> --json
python3 dev/plugins/dev-flow/scripts/doctor_workflow.py --repo <project> --check-cache-drift --json
python3 dev/plugins/dev-flow/scripts/scaffold_workflow.py --repo <project> --mode auto --dry-run --json
git -C <project> status -sb
```

For a non-Git project, report that `git status` is unavailable and list changed
workflow paths explicitly.

## Safe project-local refresh

Apply only actions already authorized by the user. Preview official OpenSpec
1.6 skills through DevFlow's isolated OpenSpec staging path, then apply the
same plan:

```bash
python3 dev/plugins/dev-flow/scripts/activate_project_dependencies.py \
  --repo <project> --codex-home <codex-home> \
  --refresh-project-skills --dry-run --json
python3 dev/plugins/dev-flow/scripts/activate_project_dependencies.py \
  --repo <project> --codex-home <codex-home> \
  --refresh-project-skills --apply --json
```

To refresh only stale DevFlow links, add `--skip-official-installs`. Preview
official layout migration with `--migrate-official-skill-layout --dry-run` and
apply only when project migration is explicitly in scope. Never auto-clean
legacy `.codex/skills` duplicates, conflicts, or manual-review paths.

## AGENTS Drift Gate

`validate_workflow_state.py` checks required markers;
`scaffold_workflow.py --dry-run` surfaces new template guidance. When
`AGENTS.md.generated` appears, compare it with active `AGENTS.md`. Merge only
durable workflow rules, including Workflow Ownership, Project Control Plane,
Matt Methodology Contract, capability routing, and completion gates. Preserve
project-specific guidance, resolve or retain the generated candidate
explicitly, then rerun validation. Skill-link and cache freshness alone do not
justify changing `AGENTS.md`.

## Verification

Repeat the diagnostic commands after apply. Record changed files, migration
status, AGENTS merge disposition, conflicts, and any restart/new-session need.
