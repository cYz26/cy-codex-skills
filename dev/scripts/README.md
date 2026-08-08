# Development Scripts

This directory holds repository and workstation maintenance scripts that are not
part of any installable skill or plugin runtime.

Use `dev/scripts/` when a script operates across this repository, local Codex
homes, plugin caches, external tool installations, or multiple development
assets. Plugin-specific runtime scripts should stay under the relevant plugin's
`scripts/` directory.

## DevFlow Pre-Promotion Tests

Run the complete source-only DevFlow gate before creating release-verification
evidence:

```bash
PYTHONDONTWRITEBYTECODE=1 python3.12 dev/scripts/run_devflow_prepromotion_tests.py
```

The runner executes every development test module except the packaged-runtime
and release-smoke modules, which require promoted generated assets. It rejects
skips and failures. After separately authorized promotion, the ordinary full
development discovery must still run those release-dependent modules.

## Codex Plugin and Skill Updater

Maintain local Codex plugins and skills:

```bash
python3.11 dev/scripts/codex_auto_update_plugins_skills.py --apply --json
```

Dry-run mode omits `--apply`:

```bash
python3.11 dev/scripts/codex_auto_update_plugins_skills.py --json
```

The DevFlow `codex-updater` skill wraps this script for chat use. It runs dry-run
checks first, summarizes plugin install refresh and cache verification results,
and only applies updates after explicit update intent or confirmation.

The updater delegates to DevFlow's canonical updater implementation. It checks
clean Git mirrors against their upstream remotes in dry-run mode, refreshes
configured plugin marketplaces, plans or applies installed plugin cache refreshes
with `codex plugin add`, verifies installed plugin caches against marketplace
sources when possible, refreshes OpenAI curated plugin caches and skills, and
maintains independently configured external tooling such as Lark and OpenSpec.
It skips local copies that differ from their previous upstream mirror instead
of overwriting them. DevFlow methodology assets are source-pinned in the plugin
and are not installed through this workstation updater.

Agent Reach is deprecated in this repository and is not recommended for new use;
it is intentionally excluded from automatic update planning.

Use Python 3.11 or newer; the script uses the standard-library `tomllib` module.

## Codex Fleet Sync

Use the independent declarative reconciler when the desired scope is only
managed marketplace snapshots, installed plugin caches, and explicitly adopted
project state:

```bash
PYTHONDONTWRITEBYTECODE=1 python3.12 dev/scripts/codex_fleet.py sync --json
```

It is dry-run by default. `sync --apply` converges to the existing portable
lock; `sync --apply --advance-lock` explicitly advances managed Git snapshots.
See `dev/tools/codex-fleet/README.md` for bootstrap, additional-device,
authorization, receipt, verification, and rollback behavior. This narrower CLI
does not inherit Codex application, external dependency, mirror, cleanup,
release, or Git publication maintenance from the legacy broad updater.
