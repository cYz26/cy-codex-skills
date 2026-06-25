# Superpowers Upgrade Policy

DevFlow treats Superpowers as a methodology dependency, not as DevFlow-owned
runtime code.

## Version Policy

- minimum compatible version: `5.1.3`
- recommended version: `6.0.3`
- strict profile target: `6.0.3`

OpenAI curated `5.1.3` remains a compatibility fallback. Upstream
Superpowers `6.0.3` is the recommended target when a team or personal
marketplace can pin the upstream tag or audited commit.

## Boundaries

- DevFlow may diagnose missing, unsupported, fallback, upgrade-recommended,
  hook-missing, hook-untrusted, and ok states.
- DevFlow does not install or upgrade Superpowers from hooks.
- DevFlow does not trust or bypass Superpowers hooks.
- Users must review bundled hooks through `/hooks`.

## Validation

Run:

```bash
python3 plugins/dev-flow/scripts/check_dependencies.py --repo . --json
```

Strict execution requires the required skills and, for Superpowers v6 or newer,
an inspectable trusted SessionStart hook or an explicitly recorded blocker.
