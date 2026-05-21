# Audit Context Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a context hygiene audit that reports global plugin/skill pressure, recommends project-relevant tools, and applies selected safe actions after authorization.

**Architecture:** Add `workflow_context_tools.py` as the implementation module and keep CLI wrappers thin. The audit is read-only by default; action application consumes a saved report and writes backups before changing config or project-local skill files.

**Tech Stack:** Python 3.11 standard library, existing unittest test suite, existing Codex project orchestrator script conventions.

---

### Task 1: Audit Report Tests

**Files:**
- Create: `tests/test_context_tools.py`
- Create later: `scripts/workflow_context_tools.py`

- [x] **Step 1: Write failing inventory and recommendation tests**

Create tests that build a temporary Codex home with enabled global plugins, global skills, installed cache skills, and a target repo with framework signals. Assert that `audit_context_tools` reports inventory, cleanup actions, and project-local install actions.

- [x] **Step 2: Run focused tests to verify they fail**

Run: `/opt/homebrew/bin/python3.11 -m unittest tests.test_context_tools`
Expected: FAIL because `workflow_context_tools` does not exist yet.

- [x] **Step 3: Implement audit report logic**

Create inventory scanners, project signal detection, relevance matching, context pressure scoring, recommendation generation, and action object creation in `scripts/workflow_context_tools.py`.

- [x] **Step 4: Run focused tests to verify they pass**

Run: `/opt/homebrew/bin/python3.11 -m unittest tests.test_context_tools`
Expected: PASS.

### Task 2: Authorized Apply Tests

**Files:**
- Modify: `tests/test_context_tools.py`
- Modify: `scripts/workflow_context_tools.py`

- [x] **Step 1: Write failing dry-run and apply tests**

Add tests that call action application with `apply=False` and `apply=True`. Dry-run must not change files. Apply must create a config backup, disable only the selected plugin, and copy selected installed skills into `.codex/skills/`.

- [x] **Step 2: Run focused tests to verify they fail**

Run: `/opt/homebrew/bin/python3.11 -m unittest tests.test_context_tools`
Expected: FAIL because action application is missing.

- [x] **Step 3: Implement apply helpers**

Implement report action selection, safe action filtering, config backup creation, targeted plugin disabling, global skill disabling through `[[skills.config]]`, and project-local skill copy.

- [x] **Step 4: Run focused tests to verify they pass**

Run: `/opt/homebrew/bin/python3.11 -m unittest tests.test_context_tools`
Expected: PASS.

### Task 3: CLI Wrappers And Docs

**Files:**
- Create: `scripts/audit_context_tools.py`
- Create: `scripts/apply_context_tool_actions.py`
- Modify: `README.md`

- [x] **Step 1: Add CLI smoke tests or subprocess coverage if needed**

Extend tests only if library coverage does not cover argument-sensitive behavior.

- [x] **Step 2: Implement thin CLIs**

Add JSON output, readable text output, `--repo`, `--codex-home`, `--config`, `--source-catalog`, `--source-url`, `--plan`, `--action`, `--all-safe`, and `--apply`.

- [x] **Step 3: Document usage**

Add README examples for read-only audit, saving a report, dry-run apply, and explicit apply.

- [x] **Step 4: Run verification**

Run: `/opt/homebrew/bin/python3.11 -m unittest tests.test_context_tools`
Run: `/opt/homebrew/bin/python3.11 -m unittest discover -s tests`
Expected: PASS.
