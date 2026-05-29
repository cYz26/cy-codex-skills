# Project-Local Codex Setup

This directory keeps only the small project-local Codex configuration files that are useful to review.

Tracked files:

- `.gsd-profile`: selected GSD local profile.

Ignored files under `.codex/` are installer/runtime output from GSD, OpenSpec, Superpowers, and local plugin activation.
This includes generated `config.toml` and `hooks.json`, which contain machine-local absolute paths.
Regenerate them with:

```bash
/opt/homebrew/bin/python3.11 dev/plugins/dev-flow/scripts/activate_project_dependencies.py \
  --repo /Users/cY/dev/skills/cy-codex-skills \
  --plugin-root /Users/cY/dev/skills/cy-codex-skills/dev/plugins/dev-flow \
  --codex-home /Users/cY/.codex \
  --json
```

Then reload Codex from this repository.
