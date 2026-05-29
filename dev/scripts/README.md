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

The updater refreshes clean Git mirrors, OpenAI curated plugin caches, OpenAI
curated skills, and known external tooling such as Agent Reach, Lark, GSD, and
OpenSpec. It skips local copies that differ from their previous upstream mirror
instead of overwriting them.

Use Python 3.11 or newer; the script uses the standard-library `tomllib` module.
