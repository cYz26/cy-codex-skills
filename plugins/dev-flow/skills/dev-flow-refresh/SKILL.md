---
name: dev-flow-refresh
description: Use when DevFlow has upgraded, when refreshing the local/global DevFlow plugin installation or installed cache, or when refreshing DevFlow project-local workflow configuration across active projects.
---

# DevFlow Refresh

Use this skill to refresh DevFlow itself and then refresh projects that use
DevFlow. The required order is global before project: first make the
local/global DevFlow plugin and installed cache current, then handle each
project-local configuration refresh.

## Global DevFlow Refresh

Start with the targeted local plugin refresh unless the user explicitly asks
for a broader updater workflow:

```bash
codex plugin add dev-flow@cy-codex-skills --json
```

Verify source/cache freshness before claiming the global refresh is complete.
Use the first existing checker:

```bash
python3 dev/plugins/dev-flow/scripts/doctor_workflow.py --repo <repo> --check-cache-drift --json
python3 dev/scripts/codex_auto_update_plugins_skills.py --json
```

If the user asked for the full Codex plugin/skill updater flow, use
`codex-updater` first. Keep its dry-run/apply boundary authoritative.

## Project Discovery

Refresh only projects that actually use DevFlow. A project qualifies when it
has one of these markers:

- `AGENTS.md` with DevFlow guidance
- `.planning/devflow/STATE.md`
- `openspec/config.yaml`
- `.planning/devflow/plugin-project-migration/state.json`
- `.agents/skills` entries pointing to DevFlow skills

If the user names projects, use that list. Otherwise inspect likely active repo
roots and report which projects were included or skipped.

## Read-Only Project Diagnostics

For each project, run diagnostics before applying changes:

```bash
python3 dev/plugins/dev-flow/scripts/plugin_project_migration.py --repo <project> --json
python3 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo <project> --json
python3 dev/plugins/dev-flow/scripts/doctor_workflow.py --repo <project> --check-cache-drift --json
python3 dev/plugins/dev-flow/scripts/scaffold_workflow.py --repo <project> --mode auto --dry-run --json
git -C <project> status -sb
```

For non-git projects, say that `git status` is unavailable and list changed
workflow files by path.

## Safe Project Refresh

Apply only the safe refreshes that the latest user request already authorizes.

Refresh stale project-local DevFlow skill links:

```bash
python3 dev/plugins/dev-flow/scripts/activate_project_dependencies.py \
  --repo <project> \
  --codex-home <codex-home> \
  --skip-official-installs \
  --refresh-project-skills \
  --apply \
  --json
```

If official skill layout migration has no conflicts, run dry-run first and
then apply only when project migration is in scope:

```bash
python3 dev/plugins/dev-flow/scripts/activate_project_dependencies.py \
  --repo <project> \
  --skip-official-installs \
  --migrate-official-skill-layout \
  --dry-run \
  --json
```

Do not auto-clean legacy `.codex/skills` duplicates, conflicts, or
manual-review items. Report them separately and require explicit approval before
cleanup or conflict resolution.

## AGENTS.md Boundary

Do not overwrite active `AGENTS.md` as part of ordinary skill-link refresh.

## AGENTS Drift Gate

AGENTS drift review is a required project refresh gate. Every DevFlow upgrade
must evaluate whether durable workflow rules changed for each project. Do not
rely only on `validate_workflow_state.py ok=true`;
validation checks required markers, while `scaffold_workflow.py --dry-run`
surfaces new template guidance that may need to be merged.

Compare the dry-run `AGENTS.md.generated` candidate with the active
`AGENTS.md` whenever it appears. Durable workflow rules include Workflow
Ownership, Project Control Plane, Superpowers Artifact Mapping, GSD/OpenSpec
routing, Brainstorm and Planning Flow, Goal Workflow, AI Coding Planning Rules,
Workflow Mode Routing, Plugin Eval Gate, and Local Reference Update Reminder.

Skill links, installed cache freshness, control-plane file creation, and
official skill-layout migration do not by themselves require `AGENTS.md`
changes.

Treat `AGENTS.md.generated` as a merge-required candidate, not as active
guidance. Update active `AGENTS.md` only when durable DevFlow workflow rules
changed or `validate_workflow_state.py` reports missing guidance. Merge the
durable rules, preserve project-specific rules, delete or resolve the generated
file, and rerun validation.

Keep task-specific slice boundaries, temporary non-goals, and current execution
details in OpenSpec, GSD, `.planning`, or `TASK_LEDGER.md`, not in `AGENTS.md`.

## Final Verification

After global or project refresh actions, rerun:

```bash
python3 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo <project> --json
python3 dev/plugins/dev-flow/scripts/doctor_workflow.py --repo <project> --check-cache-drift --json
python3 dev/plugins/dev-flow/scripts/plugin_project_migration.py --repo <project> --json
git -C <project> status -sb
```

Report:

- global DevFlow refresh command and cache/source result
- projects refreshed, skipped, and why
- files changed or generated
- AGENTS status: unchanged, merged, generated-deferred, or conflict
- AGENTS evidence: scaffold dry-run result, validation result, and whether
  `AGENTS.md.generated` remains
- validation and doctor results
- remaining `migration_pending`, duplicate, conflict, or manual-review items
- residual risk when AGENTS merge is deferred: the project may not inherit the
  latest DevFlow durable workflow rules
- whether Codex restart or a new session is needed to load project-local skills
