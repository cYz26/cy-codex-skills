# Archive Root Legacy Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move deprecated standalone skill directories from the repository root into a single archive directory without changing active plugin distribution paths.

**Architecture:** Active Codex plugin skills stay under `plugins/*/skills` and `dev/plugins/*/skills`. Deprecated standalone skill folders move under `archived-skills/`, while docs and tests that referenced root paths are updated to the new archive location.

**Tech Stack:** Git directory moves, Markdown docs, Python unittest fixture path update.

---

## Target State

The repository root no longer contains old standalone skill directories. All deprecated standalone skill folders that previously lived next to `README.md` are grouped under `archived-skills/`. Active marketplace plugins, development plugins, project-local `.codex/skills`, OpenSpec changes, and DevFlow runtime paths are unchanged.

## Scope / Non-Goals

- In scope: move the root-level standalone skills with `SKILL.md`, update `README.md`, update the DevFlow Agent Reach documentation test fixture.
- Out of scope: OpenSpec archive of `add-release-promotion-gate`, plugin release promotion, installed cache refresh, deleting archived skill content, changing marketplace plugin paths.

## Completion Contract

- `git pull --ff-only` confirms the local branch is current before edits.
- `archived-skills/` contains the former root-level standalone skill directories.
- No root-level deprecated skill directories with `SKILL.md` remain outside active plugin/dev paths.
- README explains that archived standalone skills are deprecated reference material.
- DevFlow tests that check Agent Reach deprecation use the archived path.
- Verification commands run and their results are recorded in `.planning/verification/`.
- `.planning/STATE.md` is updated with the latest maintenance verification context.

## Capability Slices

1. Baseline and route:
   - Confirm git sync, dependency readiness, workflow validation, and root skill inventory.
   - Decide no OpenSpec change is required because active plugin behavior and public APIs are not changed.
2. Archive root skills:
   - Move root-level deprecated standalone skill directories into `archived-skills/`.
   - Keep directory contents intact for historical reference.
3. Update references:
   - Rewrite README sections from "synced root skills" to "archived standalone skills".
   - Update the DevFlow test fixture path for Agent Reach deprecation docs.
4. Verify and record:
   - Run focused unit tests and path checks.
   - Run Plugin Eval on the archived skill collection because skill artifacts moved.
   - Record verification and update workflow state.

## Execution Ledger

- [x] Sync `main` with `origin/main`.
- [x] Identify root-level standalone skill directories and references.
- [x] Move deprecated standalone skills into `archived-skills/`.
- [x] Update README and DevFlow test fixture references.
- [x] Verify root cleanup and run focused tests.
- [x] Run Plugin Eval on `archived-skills/`.
- [x] Record verification evidence and update `.planning/STATE.md`.

## Validation Commands

```bash
git pull --ff-only
find . -maxdepth 2 -type f -name SKILL.md | sort
python3 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_dependencies.py'
python3 -m unittest discover -s dev/plugins/dev-flow/tests
python3 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo /Users/cy/Dev/agents-dev/cy-codex-skills --json
plugin-eval analyze archived-skills --format markdown
git status --short --branch
```

## Risks / Rollback

The main risk is breaking a stale root-path reference. Roll back by moving a specific directory from `archived-skills/<name>` back to `<name>` and reverting the corresponding README/test path update.

## Review Checklist

- [x] Active plugin paths in `.agents/plugins/marketplace*.json` still point at `plugins/*` or `dev/plugins/*`.
- [x] `plugins/godot-core/skills/*` and DevFlow/AgentKB/Lark plugin skills were not moved.
- [x] Archived skill content is preserved.
- [x] Verification evidence mentions the known `archive_allowed: false` OpenSpec gate as a separate non-actioned workflow boundary.
