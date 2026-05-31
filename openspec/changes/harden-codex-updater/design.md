# Design: Harden Codex Plugin and Skill Updater

## Target State

The updater provides a trustworthy local maintenance report:

- Dry-run mode distinguishes true update availability from "would try".
- Git mirrors are checked with a non-mutating remote comparison when possible.
- Installed plugins from configured marketplaces are explicitly planned for cache refresh.
- Apply mode refreshes marketplace snapshots and then reinstalls configured installed plugins with `codex plugin add <plugin@marketplace>`.
- The report includes source/cache tree comparison for installed plugin caches when source paths are discoverable.
- The root `dev/scripts/codex_auto_update_plugins_skills.py` is only a thin wrapper around the canonical DevFlow implementation.

## Scope / Non-Goals

- In scope: updater report schema additions, plugin cache refresh planning/apply behavior, Git dry-run accuracy, tests, docs, and release-copy sync.
- Non-goals: enabling paused automations, deleting duplicate marketplace config, uninstalling plugins, modifying Codex CLI behavior, or changing unrelated DevFlow hooks.

## Architecture Decisions

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| Use configured `[plugins]` selectors for refresh planning | The local config is Codex's installed/enabled source of truth. | Parse human-formatted `codex plugin list`, which is brittle. |
| Run `codex plugin add` only in apply mode | Refreshing installed cache is a mutating action and must remain explicit. | Run add during dry-run to inspect output. |
| Compare source/cache trees when both are known | This gives concrete evidence beyond installed/enabled state. | Trust marketplace upgrade or plugin list status. |
| Make root updater a wrapper | Prevents two implementations from drifting. | Keep copying features between scripts. |

## Completion Contract

- [x] Tests fail before implementation for missing plugin reinstall planning/apply behavior.
- [x] Tests fail before implementation for inaccurate Git dry-run status.
- [x] Tests fail before implementation for root updater drift.
- [x] Dry-run reports configured installed plugins as cache refresh candidates without mutating cache.
- [x] Apply mode runs `codex plugin add` for configured installed plugins after marketplace refresh.
- [x] Plugin source/cache verification reports `matches-source`, `differs-from-source`, or `source-unavailable`.
- [x] Root updater delegates to the canonical DevFlow updater.
- [x] Agent Reach remains excluded.
- [x] Relevant tests and OpenSpec validation pass.

## Capability Slices

### Slice 1: Tests

**Goal**
- Capture the reliability gaps with focused unit tests before changing behavior.

**Files / Modules**
- `dev/plugins/dev-flow/tests/test_dependencies.py`
- `plugins/dev-flow/tests/test_release_smoke.py`

**Validation Commands**
```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_dependencies.py -k update
```

### Slice 2: Canonical updater behavior

**Goal**
- Add real Git dry-run checks, plugin install refresh planning/apply, and source/cache verification.

**Files / Modules**
- `dev/plugins/dev-flow/scripts/codex_auto_update_plugins_skills.py`
- `plugins/dev-flow/scripts/codex_auto_update_plugins_skills.py`

**Validation Commands**
```bash
python3 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_dependencies.py'
```

### Slice 3: Wrapper, docs, and verification

**Goal**
- Remove implementation drift and document the new stronger guarantee.

**Files / Modules**
- `dev/scripts/codex_auto_update_plugins_skills.py`
- `dev/scripts/README.md`
- `dev/plugins/dev-flow/README.md`
- `plugins/dev-flow/README.md`

**Validation Commands**
```bash
python3 -m unittest discover -s plugins/dev-flow/tests
openspec validate harden-codex-updater --strict
```

## Compatibility

The updater remains conservative. It skips dirty Git checkouts, does not overwrite locally changed curated skill/plugin trees, and only mutates installed plugin cache in `--apply` mode. Existing JSON consumers can continue reading the `results` list; new result kinds are additive.
