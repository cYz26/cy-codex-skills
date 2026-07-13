# Superpowers Upgrade Policy

DevFlow treats Superpowers as an optional strict methodology provider, not as a
core dependency or DevFlow-owned runtime code. This policy is inactive for
`core` and `lean-matt` projects.

## Version Policy

- minimum compatible version: `5.1.3`
- selected version/channel: resolved from `dependency-provenance.json`
- verified source records currently include curated-remote `6.1.1`, pinned
  upstream `6.0.3`, and curated fallback `5.1.3`

OpenAI curated `5.1.3` remains a compatibility fallback. DevFlow does not
silently switch an existing project between curated and upstream channels.

## Boundaries

- DevFlow may diagnose missing, unsupported, fallback, upgrade-recommended,
  hook-missing, hook-untrusted, and ok states only when the strict provider is
  selected. Unselected availability remains advisory and action-free.
- DevFlow updater apply mode may run only the selected source record's pinned
  `updateCommand`. If no unique source is selected, it stops with
  `source-selection-required`.
- DevFlow hooks do not install or upgrade Superpowers.
- DevFlow does not trust or bypass Superpowers hooks.
- Users must review bundled hooks through `/hooks` only when the selected
  distribution declares a hook.

## Validation

Run:

```bash
python3 plugins/dev-flow/scripts/check_dependencies.py --repo . --json
```

Strict execution requires hash-matching required skills. A SessionStart hook is
required and trust-checked only when the selected source manifest and source
record declare that hook; hookless curated distributions remain valid.
