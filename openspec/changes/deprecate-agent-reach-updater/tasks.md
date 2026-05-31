# Tasks: Deprecate Agent Reach Update Planning

## Target State

Agent Reach is absent from DevFlow automatic update detection and apply plans, while documentation clearly marks the repository skill as deprecated and not recommended for new use.

## Completion Contract

- [x] Agent Reach update planning is covered by a failing test before implementation.
- [x] DevFlow updater scripts no longer emit or execute Agent Reach update actions.
- [x] Repository and DevFlow docs mark Agent Reach deprecated/not recommended.
- [x] Existing local update automation prompt excludes Agent Reach and points at the current updater script.
- [x] Dev and release plugin copies are synchronized for changed runtime files.
- [x] OpenSpec validation and relevant tests pass.

## Capability Slices

### Slice 1: Tests

**Status:** done

**Implementation**
- [x] Add focused updater tests asserting Agent Reach is excluded from dry-run/apply external updater results.
- [x] Add or update documentation tests if existing coverage makes that practical.

**Validation Commands**
```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_dependencies.py -k agent_reach
```

### Slice 2: Implementation

**Status:** done

**Implementation**
- [x] Remove Agent Reach handling from development and release DevFlow updater scripts.
- [x] Mirror the change to the repository-level maintenance script.
- [x] Ensure remaining external updater behavior is unchanged.

**Validation Commands**
```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_dependencies.py -k agent_reach
```

### Slice 3: Documentation and verification

**Status:** done

**Implementation**
- [x] Mark Agent Reach deprecated/not recommended in repository documentation.
- [x] Remove Agent Reach from maintained automatic updater target wording.
- [x] Update the paused Codex plugins/skills automation prompt to exclude Agent Reach.
- [x] Record verification evidence.

**Validation Commands**
```bash
python3 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_dependencies.py'
python3 -m unittest discover -s plugins/dev-flow/tests -p 'test_dependencies.py'
openspec validate deprecate-agent-reach-updater --strict
```

## Execution Ledger

| Slice | Status | Evidence |
|---|---|---|
| Tests | done | `python3 -m unittest dev/plugins/dev-flow/tests/test_dependencies.py -k agent_reach` failed before implementation, then passed after implementation. |
| Implementation | done | Updater dry-run output no longer includes an `agent-reach` result item. |
| Documentation and verification | done | Dev/release tests passed, automation prompt was updated, and `openspec validate deprecate-agent-reach-updater --strict` passed. |

## Final Verification

- [x] Focused tests pass.
- [x] Relevant dev and release test suites pass.
- [x] OpenSpec change validates in strict mode.

## Verification Evidence

- RED: `python3 -m unittest dev/plugins/dev-flow/tests/test_dependencies.py -k agent_reach` failed because Agent Reach still appeared in update results and docs lacked deprecated/not recommended text.
- RED: `python3 -m unittest plugins/dev-flow/tests/test_release_smoke.py -k agent_reach` failed because release updater results included `agent-reach`.
- GREEN: `python3 -m unittest dev/plugins/dev-flow/tests/test_dependencies.py -k agent_reach` passed: 2 tests.
- GREEN: `python3 -m unittest plugins/dev-flow/tests/test_release_smoke.py -k agent_reach` passed: 1 test.
- `python3 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_dependencies.py'` passed: 15 tests.
- `python3 -m unittest discover -s plugins/dev-flow/tests` passed: 8 tests.
- `python3 dev/plugins/dev-flow/scripts/codex_auto_update_plugins_skills.py --codex-home /Users/cy/.codex --json --skip-codex-update --skip-openai-curated-cache` passed and did not include `agent-reach`.
- `/Users/cy/.codex/automations/codex-plugins-skills-update-check/automation.toml` points at the current updater path and states Agent Reach must not be checked, updated, or run.
- `openspec validate deprecate-agent-reach-updater --strict` passed.
