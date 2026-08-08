---
name: codex-updater
description: Use when checking, previewing, synchronizing, upgrading, verifying, or rolling back Codex Plugins, packaged Skills, marketplaces, installed caches, declarative Fleet profiles, adopted projects, or legacy workstation updaters.
---

# Codex Updater

Use one conversational entry point while keeping Fleet reconciliation and
legacy workstation maintenance as separate authority domains.

## Select Fleet or Legacy Mode

Select Fleet mode when either condition is true:

- the user names a manifest, lock, device overlay, Fleet profile, multi-device
  synchronization, adopted projects, or a Fleet receipt;
- a regular `codex-fleet.json` exists in the current working directory.

Use an explicitly named manifest as written. Do not search parent directories,
crawl disks, infer a remote from a local checkout, or adopt a project that the
user did not name. Let the Fleet CLI perform its fail-closed lexical path,
symlink, schema, identity, and adoption validation.

Select legacy mode only when no Fleet profile is selected or discovered and
the request is for workstation-wide Codex, mirror, curated-cache, or external
updater maintenance. Do not fall back to the legacy updater when a Fleet
profile is selected but invalid, blocked, or missing its runtime.

## Resolve the Fleet CLI

In Fleet mode, use the first verified entry point:

1. installed `codex-fleet` on `PATH` after `codex-fleet --help` succeeds;
2. repository wrapper `dev/scripts/codex_fleet.py`, invoked from that
   repository root with Python 3.12:

```bash
PYTHONDONTWRITEBYTECODE=1 python3.12 dev/scripts/codex_fleet.py --help
```

Treat that selected entry point as the command prefix in the examples below.
If neither entry point exists, stop and report the exact one-time installation
or source-path action. Do not install it automatically. Do not fall back to the
legacy updater.

## Run Fleet Read-Only First

Always request `--json`. Pass explicit `--manifest`, `--lock`, and `--device`
paths when the user supplies them; otherwise use the CLI defaults from the
selected profile directory. Preserve each lexical input path so the CLI can
reject symlink substitution instead of silently resolving it first.

For first-use discovery, name every candidate project explicitly and run:

```bash
codex-fleet inventory --project <id>=<absolute-path> --json
codex-fleet bootstrap --project <id>=<absolute-path> --json
```

Inventory and bootstrap without `--apply` are read-only. Show the proposed
portable manifest/lock, local device overlay, and project markers. Run
`codex-fleet bootstrap --apply` only when the current user request explicitly
authorizes adopting those exact reviewed paths.

For an existing profile, map natural-language intent as follows:

- Check, list, inspect, preview, or status: run `codex-fleet sync --json`.
- Synchronize this device to the existing lock: first run the read-only sync;
  when it has no validation, identity, or stale-plan blocker and the current
  request explicitly authorizes writes, run `codex-fleet sync --apply --json`.
- Advance remote marketplaces or update the shared lock on the designated
  update device: first run `codex-fleet sync --advance-lock --json`; only the
  exact current remote-advancement request authorizes
  `codex-fleet sync --apply --advance-lock --json`.
- Verify a receipt: run `codex-fleet verify --receipt <path> --json`.
- Roll back a receipt: first run
  `codex-fleet rollback --receipt <path> --json`. Rollback apply requires a new
  explicit user request after reviewing that preview; only then run
  `codex-fleet rollback --receipt <path> --apply --json`.

Do not treat preview exit code `2` as a crash: candidates, manual actions, and
rollback previews may use it. Decide from the structured `ok`, `status`,
actions, results, blockers, and `nextAction`. Never add `--apply` after an
invalid input, identity failure, stale plan, unavailable runtime, or lock
conflict.

After Fleet apply, report the receipt path, verified marketplace/plugin/cache
identities, refreshed and skipped projects, manual or non-reversible actions,
and restart guidance. Do not claim success from Skill prose or a subprocess
exit code alone; use the CLI JSON and fresh receipt verification.

## Run the Legacy Updater

Use the first existing script:

1. `dev/scripts/codex_auto_update_plugins_skills.py`
2. `dev/plugins/dev-flow/scripts/codex_auto_update_plugins_skills.py`
3. `../../scripts/codex_auto_update_plugins_skills.py` relative to this
   `SKILL.md`

Run repo paths from the repository root. Resolve plugin-relative paths to an
absolute path before running them.

### Dry-Run First

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

### Apply Boundary

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

## Safety

- Agent Reach is deprecated and not recommended for new use; do not check, update, or run Agent Reach as part of this workflow.
- Do not edit updater scripts while using this skill unless the user explicitly
  asks to change updater behavior.
- Do not run targeted `codex plugin add` commands unless the user asks for a
  targeted refresh after seeing dry-run/cache verification output.
- Do not let Fleet `--apply` grant workflow configuration migration, legacy
  cleanup, dependency changes, release publication, Git operations, or active
  `AGENTS.md` merge authority.
