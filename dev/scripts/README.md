# Development Scripts

This directory holds repository and workstation maintenance scripts that are not
part of any installable skill or plugin runtime.

Use `dev/scripts/` when a script operates across this repository, local Codex
homes, plugin caches, external tool installations, or multiple development
assets. Plugin-specific runtime scripts should stay under the relevant plugin's
`scripts/` directory.

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
maintains known external tooling such as Lark, GSD, and OpenSpec. It skips local
copies that differ from their previous upstream mirror instead of overwriting
them.

Agent Reach is deprecated in this repository and is not recommended for new use;
it is intentionally excluded from automatic update planning.

Use Python 3.11 or newer; the script uses the standard-library `tomllib` module.
