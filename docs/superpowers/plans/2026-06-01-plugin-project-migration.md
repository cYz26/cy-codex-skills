# Plugin Project Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a generic `plugin-project-migration` capability that automatically detects project migration drift after plugin/skill updates and requires explicit authorization before mutating project files.

**Architecture:** Add a deterministic Python engine used by both a standalone Skill and automatic hook/updater entry points. Hooks and updater flows call sync-only checks; explicit CLI apply performs safe project-local skill refresh, writes reports, and records history.

**Tech Stack:** Python 3.11 standard library, DevFlow plugin scripts, Codex plugin hooks, OpenSpec, unittest.

---

## Files

- Create: `plugins/dev-flow/scripts/plugin_project_migration.py`
- Create: `plugins/dev-flow/scripts/plugin_project_migration_check.py`
- Create: `plugins/dev-flow/skills/plugin-project-migration/SKILL.md`
- Create: `plugins/dev-flow/skills/plugin-project-migration/agents/openai.yaml`
- Create: `plugins/dev-flow/tests/test_plugin_project_migration.py`
- Modify: `plugins/dev-flow/scripts/workflow_dependency_catalog.py`
- Modify: `plugins/dev-flow/scripts/codex_auto_update_plugins_skills.py`
- Modify: `plugins/dev-flow/hooks.json`
- Modify: `plugins/dev-flow/tests/test_release_smoke.py`
- Mirror: matching files under `dev/plugins/dev-flow/`

## Task 1: Write Failing Tests

- [x] Add tests for sync detecting missing state and stale project-local skill links.
- [x] Add tests proving sync-only checks leave `.codex/skills`, `AGENTS.md`, `openspec/`, and `.planning/` unchanged.
- [x] Add tests proving explicit apply refreshes symlink targets and writes `.dev-flow/plugin-project-migration/` report/history.
- [x] Add packaging tests proving `plugin-project-migration` is listed and explicit-only.
- [x] Run:

```bash
/opt/homebrew/bin/python3.11 -m unittest plugins/dev-flow/tests/test_plugin_project_migration.py
```

Result before implementation: failed because `plugin_project_migration` did not exist.

## Task 2: Implement Generic Engine

- [x] Add migration adapter discovery for the current plugin root, initially supporting DevFlow metadata.
- [x] Add `sync_project_migrations(repo, plugin_root, codex_home, write_report=False)`.
- [x] Add `apply_project_migrations(repo, plugin_root, codex_home, allow_dirty=False)`.
- [x] Implement safe project-local skill target refresh only when target is missing or a symlink.
- [x] Implement conflict reporting for non-symlink existing targets.
- [x] Write reports/history under `.dev-flow/plugin-project-migration/`.
- [x] Run:

```bash
/opt/homebrew/bin/python3.11 -m unittest plugins/dev-flow/tests/test_plugin_project_migration.py
```

Result after implementation: passed.

## Task 3: Add Skill and Automation Integration

- [x] Add `plugin-project-migration` Skill with sync/migrate workflow and safety boundaries.
- [x] Add explicit-only `agents/openai.yaml`.
- [x] Add the Skill to `PROJECT_ORCHESTRATOR_SKILLS`.
- [x] Add updater `project-migration-sync` result when a repo is supplied or discoverable from cwd.
- [x] Add hook command for lightweight sync-only reminder.
- [x] Run:

```bash
/opt/homebrew/bin/python3.11 -m unittest discover -s plugins/dev-flow/tests
```

Result: all DevFlow release tests passed.

## Task 4: Mirror, Validate, and Evaluate

- [x] Mirror changed files from `plugins/dev-flow` to `dev/plugins/dev-flow`.
- [x] Run:

```bash
/opt/homebrew/bin/python3.11 -m unittest discover -s dev/plugins/dev-flow/tests
openspec validate add-plugin-project-migration --strict
plugin-eval analyze plugins/dev-flow --format markdown
```

Result: tests and OpenSpec passed; Plugin Eval findings were fixed or explicitly deferred with reason.

## Self-Review

- OpenSpec requirements map to Tasks 1-4.
- No project mutation happens through hook/updater automatic paths.
- Explicit apply is limited to missing/symlink project-local skill targets in this first implementation.
- Three-way merge and broad managed-file patching remain non-goals for this change.
