# Tasks: Optimize DevFlow Dependency Workflow

## Target State

DevFlow has an explicit Superpowers/OpenSpec/GSD artifact ownership contract, validates all routed workflow dependencies, can refresh stale project-local Superpowers skill symlinks when requested, supports read-only external version checks, and documents portable context audit commands.

## Completion Contract

- [x] Canonical artifact mapping is documented in generated `AGENTS.md` and DevFlow routing skills.
- [x] Tests prove `gsd-progress` is required by dependency checks.
- [x] Tests prove stale provider symlinks are detected and refreshed only when requested.
- [x] Tests prove read-only update checks report package state without invoking mutating updaters.
- [x] Context-tool audit docs use `python3`.
- [x] Dev and release plugin copies are synchronized for runtime files.
- [x] Relevant tests and dependency checks pass.

## Capability Slices

### Slice 1: Artifact mapping guidance

**Status:** done

**Implementation**
- [x] Add a Superpowers Artifact Mapping section to `AGENTS.md.template`.
- [x] Update `project-orchestrator`, `feature-intake`, `change-plan`, and `ai-native-tech-plan` to route Superpowers outputs into canonical OpenSpec/GSD/DevFlow artifacts.
- [x] Mirror changed skill/template files to `plugins/dev-flow`.

**Validation Commands**
```bash
python3 -m unittest dev.plugins.dev-flow.tests.test_project_orchestrator
```

### Slice 2: Dependency and symlink refresh behavior

**Status:** done

**Implementation**
- [x] Add `gsd-progress` to required GSD dependency coverage.
- [x] Add explicit project-local skill refresh behavior for stale provider symlinks.
- [x] Expose refresh behavior through activation script arguments.
- [x] Mirror changed script files to `plugins/dev-flow`.

**Validation Commands**
```bash
python3 -m unittest dev.plugins.dev-flow.tests.test_dependencies
```

### Slice 3: Read-only update checks and portable docs

**Status:** done

**Implementation**
- [x] Add read-only version checks for GSD and OpenSpec update reporting.
- [x] Keep mutating external updater commands behind `--apply`.
- [x] Replace hard-coded context audit Python path with `python3`.
- [x] Mirror changed script/skill files to `plugins/dev-flow`.

**Validation Commands**
```bash
python3 -m unittest discover -s dev/plugins/dev-flow/tests
python3 -m unittest discover -s plugins/dev-flow/tests
```

## Execution Ledger

| Slice | Status | Evidence |
|---|---|---|
| Artifact mapping guidance | done | `python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py -k superpowers_artifacts` passed |
| Dependency and symlink refresh behavior | done | `python3 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_dependencies.py'` passed |
| Read-only update checks and portable docs | done | `python3 -m unittest discover -s dev/plugins/dev-flow/tests` and update dry-run passed |

## Acceptance Criteria

- [x] Superpowers outputs cannot silently become a second source of truth in DevFlow instructions.
- [x] Dependency checks cover all GSD skills used by DevFlow routing.
- [x] Stale project-local symlinks are non-destructive by default and refreshable by explicit request.
- [x] Update discovery can run safely as a read-only audit.
- [x] DevFlow context audit docs work with portable Python.

## Validation Commands

```bash
python3 -m unittest discover -s dev/plugins/dev-flow/tests
python3 -m unittest discover -s plugins/dev-flow/tests
python3 dev/plugins/dev-flow/scripts/check_dependencies.py --repo /Users/cy/Dev/agents-dev/cy-codex-skills --codex-home /Users/cy/.codex --json
python3 dev/plugins/dev-flow/scripts/codex_auto_update_plugins_skills.py --codex-home /Users/cy/.codex --json --skip-codex-update --skip-openai-curated-cache
```

## Final Verification

- [x] Focused and full tests pass.
- [x] Dependency check reports ready.
- [x] Update dry-run remains non-mutating.
- [x] OpenSpec status is apply-ready for this change.

## Verification Evidence

- `python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py -k superpowers_artifacts` passed.
- `python3 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_dependencies.py'` passed: 10 tests.
- `python3 -m unittest discover -s dev/plugins/dev-flow/tests` passed: 33 tests.
- `python3 -m unittest discover -s plugins/dev-flow/tests` passed: 2 tests.
- `openspec validate optimize-devflow-dependency-workflow --strict` passed.
- `python3 dev/plugins/dev-flow/scripts/check_dependencies.py --repo /Users/cy/Dev/agents-dev/cy-codex-skills --codex-home /Users/cy/.codex --json` returned `ok: true`, `status: ready`.
- `python3 dev/plugins/dev-flow/scripts/codex_auto_update_plugins_skills.py --codex-home /Users/cy/.codex --json --skip-codex-update --skip-openai-curated-cache` returned GSD `current: 1.42.3`, `latest: 1.42.3`, `updateAvailable: false`; OpenSpec `current: 1.3.1`, `latest: 1.3.1`, `updateAvailable: false`.
