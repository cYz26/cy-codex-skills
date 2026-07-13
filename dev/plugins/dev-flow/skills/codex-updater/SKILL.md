---
name: codex-updater
description: Use when checking or updating Codex plugins, Codex skills, marketplaces, plugin caches, or external updaters.
---

# Codex Updater

Use for local maintenance of Codex plugins, skills, marketplace snapshots,
plugin caches, and known external updater toolchains.

## Locate the Updater

Use the first existing script:

1. `dev/scripts/codex_auto_update_plugins_skills.py`
2. `dev/plugins/dev-flow/scripts/codex_auto_update_plugins_skills.py`
3. `../../scripts/codex_auto_update_plugins_skills.py` relative to this
   `SKILL.md`

Run repo paths from the repository root. Resolve plugin-relative paths to an
absolute path before running them.

## Dry-Run First

Run dry-run first:

```bash
python3 dev/scripts/codex_auto_update_plugins_skills.py --json
```

Add `--codex-home <path>` when the user names a Codex home. Use skip flags only
for narrower checks:

- `--skip-codex-update`
- `--skip-openai-curated-cache`
- `--skip-external-updaters`

Summarize by actionable category:

- `would-update`, `would-refresh`, `update-available`
- `unchanged`, `matches-source`
- `plugin-install`
- `plugin-cache-verify`, including `differs-from-source`,
  `source-unavailable`, and `cache-missing`
- `project-migration-sync`, including whether `plugin-project-migration` should
  be run for explicit project-local migration
- `skipped`, `failed`, `manual-required`, and the reason

## Apply Boundary

Even update requests start with dry-run. Run apply only when the latest user
request explicitly asks to update or apply and dry-run has no `failed`,
`manual-required`, or dirty/local-modification `skipped` items:

```bash
python3 dev/scripts/codex_auto_update_plugins_skills.py --apply --json
```

Otherwise, show the dry-run report and ask before `--apply`.

After apply, report updated items, unchanged items, skipped items, failures,
manual actions, installed plugin refresh results, and plugin cache verification
results. Also report project migration sync findings, but do not apply project
migrations from the updater path. Do not claim an installed plugin is refreshed
unless cache verification or apply output supports it.

For Superpowers, use only the selected source record's pinned `updateCommand`
from `docs/dependency-provenance.json`; never replace the selected channel with
a hard-coded marketplace alias. Report a hook trust action only when that
selected source record declares a SessionStart hook; do not write hook trust
state from the updater path.

## Safety

- Agent Reach is deprecated and not recommended for new use; do not check, update, or run Agent Reach as part of this workflow.
- Do not edit updater scripts while using this skill unless the user explicitly
  asks to change updater behavior.
- Do not run targeted `codex plugin add` commands unless the user asks for a
  targeted refresh after seeing dry-run/cache verification output.
