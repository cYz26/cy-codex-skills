# Tasks: Harden Codex Plugin and Skill Updater

## Target State

The updater has one canonical implementation, reports real dry-run evidence where practical, verifies installed plugin cache state, and can refresh configured installed plugins in apply mode.

## Completion Contract

- [x] Add failing tests for Git dry-run update availability.
- [x] Add failing tests for installed plugin refresh planning and apply behavior.
- [x] Add failing tests for plugin cache verification statuses.
- [x] Add failing tests or assertions that root updater delegates to DevFlow implementation.
- [x] Implement canonical updater behavior and release-copy sync.
- [x] Update docs and verification evidence.
- [x] Run focused and full relevant verification.

## Capability Slices

### Slice 1: Tests

**Status:** done

**Implementation**
- [x] Test dry-run `update_git_repo` distinguishes unchanged vs would-update.
- [x] Test enabled configured plugins produce `plugin-install` dry-run items and `codex plugin add` apply calls.
- [x] Test plugin cache verification reports matching and differing cache/source trees.
- [x] Test repository updater wrapper delegates to DevFlow updater.

**Validation Commands**
```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_dependencies.py -k update
```

### Slice 2: Updater implementation

**Status:** done

**Implementation**
- [x] Add remote comparison to Git dry-run checks.
- [x] Add configured installed plugin discovery and refresh planning/apply.
- [x] Add source/cache verification results for installed plugin caches.
- [x] Keep Agent Reach excluded.
- [x] Sync dev and release DevFlow scripts.

**Validation Commands**
```bash
python3 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_dependencies.py'
```

### Slice 3: Wrapper, docs, and final verification

**Status:** done

**Implementation**
- [x] Replace root updater with a wrapper around DevFlow's canonical updater.
- [x] Update README guidance to describe plugin cache refresh and verification.
- [x] Record verification evidence.

**Validation Commands**
```bash
python3 -m unittest discover -s plugins/dev-flow/tests
openspec validate harden-codex-updater --strict
```

## Execution Ledger

| Slice | Status | Evidence |
|---|---|---|
| Tests | done | Initial focused run failed on old Git dry-run, missing plugin refresh/cache verification functions, and root updater fork. |
| Updater implementation | done | `python3 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_dependencies.py'` passed. |
| Wrapper, docs, and final verification | done | Release tests, all DevFlow tests, dry-run assertion, and OpenSpec validation passed. |

## Final Verification

- [x] Focused updater tests pass.
- [x] DevFlow dev dependency tests pass.
- [x] Release smoke tests pass.
- [x] OpenSpec validates in strict mode.

## Verification Evidence

- RED: `python3 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_dependencies.py'` failed on missing plugin refresh/cache verification functions, inaccurate Git dry-run status, and root updater drift.
- GREEN: `python3 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_dependencies.py'` passed: 20 tests.
- `python3 -m unittest discover -s plugins/dev-flow/tests` passed: 9 tests.
- `python3 -m unittest discover -s dev/plugins/dev-flow/tests` passed: 61 tests.
- `openspec validate --all --strict` passed: 12 items.
- `git diff --check` on updater-related files passed.
- Dry-run assertion passed: update report includes `plugin-install` and `plugin-cache-verify`, excludes `agent-reach`, and reports `dev-flow@cy-codex-skills` cache as `differs-from-source`.
- Verification record: `.planning/verification/20260530230009-harden-codex-updater.md`.
