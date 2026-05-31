# Tasks: Add Codex Updater Skill

## Target State

DevFlow exposes a `codex-updater` skill that future Codex sessions can use to
check and update Codex-referenced plugins, skills, marketplace snapshots, plugin
caches, and known external update paths through the canonical updater. The skill
defaults to dry-run reporting, requires explicit apply intent, summarizes
actionable statuses, and keeps Agent Reach excluded.

## Completion Contract

- [x] The new skill exists in development and release DevFlow plugin trees.
- [x] The skill points to the canonical updater command and JSON dry-run mode.
- [x] The skill documents apply-mode authorization boundaries.
- [x] The skill requires reporting for plugin install refresh and plugin cache
  verification results.
- [x] Agent Reach remains excluded from the skill workflow.
- [x] Tests fail before the skill exists and pass after implementation.
- [x] OpenSpec validates strictly.

## 1. Tests

- [x] 1.1 Add a development test that expects `skills/codex-updater/SKILL.md`
  to exist with trigger language for Codex plugins, skills, marketplaces, plugin
  cache verification, and external updater checks.
- [x] 1.2 Add a development test that expects the skill to use dry-run JSON first,
  require explicit apply intent before `--apply`, and exclude Agent Reach.
- [x] 1.3 Add a release smoke test that expects the release plugin to package the
  `codex-updater` skill and reference the canonical updater command.
- [x] 1.4 Run the focused tests and confirm they fail before implementation.

## 2. Skill Implementation

- [x] 2.1 Add `dev/plugins/dev-flow/skills/codex-updater/SKILL.md`.
- [x] 2.2 Sync the skill to `plugins/dev-flow/skills/codex-updater/SKILL.md`.
- [x] 2.3 Keep the skill concise and avoid extra documentation files.
- [x] 2.4 Do not add Agent Reach update behavior.

## 3. Verification

- [x] 3.1 Run focused development tests for skill packaging.
- [x] 3.2 Run release smoke tests.
- [x] 3.3 Run full DevFlow development tests.
- [x] 3.4 Run `openspec validate --all --strict`.
- [x] 3.5 Record verification evidence and residual risks.

## Verification Evidence

- RED: focused development and release tests failed before implementation because
  `skills/codex-updater/SKILL.md` did not exist.
- `python3 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_dependencies.py'`
  passed: 22 tests.
- `python3 -m unittest discover -s plugins/dev-flow/tests` passed: 22 tests.
- `python3 -m unittest discover -s dev/plugins/dev-flow/tests` passed: 71 tests.
- `openspec validate --all --strict` passed: 15 items.
- Relevant `git diff --check` passed.
- Verification record:
  `.planning/verification/20260531202037-add-codex-updater-skill.md`.
