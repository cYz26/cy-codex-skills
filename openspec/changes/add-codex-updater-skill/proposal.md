## Why

Codex plugin and skill update checks now have a reliable script, but users still
need to remember the script path and review semantics. A DevFlow skill gives the
operation a discoverable workflow entrypoint and keeps apply-mode updates behind
an explicit confirmation boundary.

## What Changes

- Add a DevFlow skill for checking and updating Codex-referenced plugins, skills,
  plugin caches, marketplaces, and known external toolchains.
- Document the safe default: run the updater in dry-run JSON mode first, summarize
  update/cache verification results, and only run `--apply` after the user asks
  to update.
- Keep Agent Reach out of the skill workflow because it is deprecated and not
  recommended for new use.
- Package the skill in both development and release DevFlow plugin trees.

## Capabilities

### New Capabilities

- `codex-updater-skill`: A skill-triggered workflow for checking and applying
  Codex plugin, skill, marketplace, cache, and external updater maintenance.

### Modified Capabilities

- None.

## Impact

- Adds `skills/codex-updater/SKILL.md` to DevFlow plugin source and release copy.
- Adds tests ensuring the skill is packaged, triggerable, safe by default, and
  points to the canonical updater script.
- No new production dependencies.
