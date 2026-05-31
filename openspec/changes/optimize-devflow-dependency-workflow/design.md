# Design: Optimize DevFlow Dependency Workflow

## Target State

DevFlow clearly states that Superpowers supplies discipline and gates, while OpenSpec/GSD/DevFlow files are the canonical workflow artifacts. Agents using DevFlow should not preserve `docs/superpowers/specs/...` or `docs/superpowers/plans/...` as parallel sources of truth for behavior changes or phase work; those notes must be copied into `openspec/changes/<id>/...`, `.planning/phases/...`, or a DevFlow ledger before implementation.

Dependency setup and update checks become more reliable:

- `gsd-progress` is included in dependency checks because `workflow-doctor` uses it.
- Project-local Superpowers symlinks can be refreshed when their cached provider source changes.
- Update tooling can perform read-only version checks for GSD and OpenSpec before invoking `npx` or `npm update`.
- Context-tool audit docs use `python3`, not a machine-specific Homebrew path.

## Scope / Non-Goals

- In scope: DevFlow docs, skill instructions, templates, dependency catalog/checks, project-local skill install behavior, update check reporting, and tests.
- Non-goals: replacing Superpowers, changing OpenSpec schema behavior, changing GSD phase semantics, adding package dependencies, changing plugin manifest identity, or updating user global tool installations.

## Architecture Decisions

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| Canonical artifact mapping is documented in DevFlow guidance, not by editing Superpowers upstream | DevFlow controls this repository's workflow contract and should adapt external tools locally. | Forking or patching Superpowers skills |
| Symlink refresh is explicit via `refresh_existing` | Avoid surprising rewrites of project-local skills during normal activation. | Always rewrite mismatched symlinks |
| Read-only update checks use package metadata commands | They are safe to run during audits and do not mutate global installs. | Running `npx`/`npm update` as the check |
| Keep generated artifacts under OpenSpec/GSD/DevFlow paths | Prevents duplicate source-of-truth files. | Allow `docs/superpowers/*` as peer canonical files |

## Completion Contract

- [x] Generated `AGENTS.md` guidance includes a Superpowers artifact mapping section.
- [x] DevFlow routing skills instruct agents to map Superpowers brainstorm/plan outputs into canonical OpenSpec/GSD/DevFlow artifacts.
- [x] Dependency checks require `gsd-progress` when project GSD skills are active.
- [x] Project-local skill activation can refresh an existing symlink when requested and reports stale links otherwise.
- [x] External updater reporting can check GSD/OpenSpec current/latest versions without mutating installs.
- [x] Context-tool audit instructions use portable `python3`.
- [x] Dev and release plugin copies stay synchronized for changed files.
- [x] Focused and full DevFlow tests pass.

## Capability Slices

### Slice 1: Artifact ownership guidance

**Goal**
- Make Superpowers/OpenSpec/GSD artifact ownership unambiguous across generated instructions and DevFlow skills.

**Files / Modules**
- `dev/plugins/dev-flow/assets/templates/AGENTS.md.template`
- `dev/plugins/dev-flow/skills/project-orchestrator/SKILL.md`
- `dev/plugins/dev-flow/skills/feature-intake/SKILL.md`
- `dev/plugins/dev-flow/skills/change-plan/SKILL.md`
- `dev/plugins/dev-flow/skills/ai-native-tech-plan/SKILL.md`
- release-copy equivalents under `plugins/dev-flow/`

**Validation Commands**
```bash
python3 -m unittest dev.plugins.dev-flow.tests.test_project_orchestrator
```

### Slice 2: Dependency validation and refresh behavior

**Goal**
- Validate every used required GSD skill and make project-local skill links refreshable.

**Files / Modules**
- `dev/plugins/dev-flow/scripts/workflow_dependency_catalog.py`
- `dev/plugins/dev-flow/scripts/workflow_project_skill_install.py`
- `dev/plugins/dev-flow/scripts/workflow_project_activation.py`
- `dev/plugins/dev-flow/scripts/activate_project_dependencies.py`
- `dev/plugins/dev-flow/tests/test_dependencies.py`
- release-copy equivalents under `plugins/dev-flow/`

**Validation Commands**
```bash
python3 -m unittest dev.plugins.dev-flow.tests.test_dependencies
```

### Slice 3: Read-only update checks and portable audit docs

**Goal**
- Separate update discovery from mutation and remove host-specific Python guidance.

**Files / Modules**
- `dev/plugins/dev-flow/scripts/codex_auto_update_plugins_skills.py`
- `dev/plugins/dev-flow/skills/context-tool-audit/SKILL.md`
- tests under `dev/plugins/dev-flow/tests/`
- release-copy equivalents under `plugins/dev-flow/`

**Validation Commands**
```bash
python3 -m unittest discover -s dev/plugins/dev-flow/tests
python3 -m unittest discover -s plugins/dev-flow/tests
```

## Execution Ledger

| Slice | Status | Evidence |
|---|---|---|
| Artifact ownership guidance | done | `python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py -k superpowers_artifacts` passed |
| Dependency validation and refresh behavior | done | `python3 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_dependencies.py'` passed |
| Read-only update checks and portable audit docs | done | `python3 -m unittest discover -s dev/plugins/dev-flow/tests` and update dry-run passed |

## Approach

Use the existing DevFlow pattern: focused Python helpers, simple JSON reports, and tests that exercise scripts through temporary Codex homes and repos. Update dev source first, then mirror changed runtime files into the release plugin directory.

## Data Flow

Project activation locates provider skill sources from the plugin root or Codex plugin cache, compares them to existing project-local `.codex/skills/*` entries, and either leaves them unchanged, reports stale links, or refreshes symlinks when explicitly requested.

The updater script reads installed/local version indicators, queries package metadata with `npm view`, and reports `current`, `latest`, and `updateAvailable`. Apply mode remains the only path that runs external installers.

## Compatibility

Existing activation remains non-destructive by default. `refresh_existing` only affects symlinks that already point at a provider-owned skill path; copied or user-modified project-local skill directories remain preserved.

## Testing

Tests are added before implementation for:

- generated artifact mapping text,
- dependency coverage for `gsd-progress`,
- stale symlink reporting and refresh behavior,
- update metadata checks that do not run mutating update commands,
- portable `python3` context-tool instructions.

## Acceptance Criteria

- [x] Generated guidance prevents duplicate Superpowers/OpenSpec/GSD source-of-truth artifacts.
- [x] Dependency validation fails when `gsd-progress` is absent and passes when present.
- [x] Project-local Superpowers symlink refresh is explicit and covered by tests.
- [x] Read-only update checks report GSD/OpenSpec version state without executing package updaters.
- [x] Context-tool docs run on systems where only `python3` is available.

## Validation Commands

```bash
python3 -m unittest discover -s dev/plugins/dev-flow/tests
python3 -m unittest discover -s plugins/dev-flow/tests
python3 dev/plugins/dev-flow/scripts/check_dependencies.py --repo /Users/cy/Dev/agents-dev/cy-codex-skills --codex-home /Users/cy/.codex --json
python3 dev/plugins/dev-flow/scripts/codex_auto_update_plugins_skills.py --codex-home /Users/cy/.codex --json --skip-codex-update --skip-openai-curated-cache
```

## Final Verification

- [x] Focused tests pass.
- [x] Full DevFlow dev and release test suites pass.
- [x] Dependency check still reports ready for this repository.
- [x] OpenSpec tasks are marked complete with validation evidence.
