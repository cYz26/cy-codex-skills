# Optimize DevFlow Plugin Eval Score Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Improve DevFlow's Plugin Eval results by fixing manifest, skill metadata, context-tool structure, release test signal, and verification evidence.

**Architecture:** Keep public entry points stable while splitting the context-tool implementation into focused modules. Optimize visible metadata conservatively and add compact packaged tests instead of shipping the full development test suite.

**Tech Stack:** Python stdlib, unittest, JSON/TOML handling, OpenSpec CLI, Plugin Eval CLI.

---

### Task 1: Baseline and Failing Tests

**Files:**
- Modify: `dev/plugins/dev-flow/tests/test_project_orchestrator.py`
- Modify: `dev/plugins/dev-flow/tests/test_context_tools.py`
- Create: `plugins/dev-flow/tests/test_release_smoke.py`

- [x] Add a manifest test asserting both dev and release manifests expose no more than three default prompts.
- [x] Add context-tool tests that import `audit_context_tools` and `apply_context_tool_actions` through `workflow_context_tools`.
- [x] Add release smoke tests for packaged manifest prompt count, context-tool audit shape, and dry-run action application.
- [x] Run focused tests and confirm at least the prompt-count/release-test expectations fail before implementation.

### Task 2: Manifest and Skill Metadata

**Files:**
- Modify: `dev/plugins/dev-flow/.codex-plugin/plugin.json`
- Modify: `plugins/dev-flow/.codex-plugin/plugin.json`
- Modify: `dev/plugins/dev-flow/skills/ai-native-tech-plan/SKILL.md`
- Modify: `plugins/dev-flow/skills/ai-native-tech-plan/SKILL.md`
- Modify: `dev/plugins/dev-flow/skills/context-tool-audit/SKILL.md`
- Modify: `plugins/dev-flow/skills/context-tool-audit/SKILL.md`

- [x] Trim default prompts to three: planning, workflow setup, and active-work verification/change flow.
- [x] Shorten `ai-native-tech-plan` trigger description while keeping target-state planning, completion contract, execution ledger, and non-MVP signals.
- [x] Shorten `context-tool-audit` trigger description while keeping global/plugin/skill context audit, cleanup, install, and authorization signals.
- [x] Run manifest and skill tests.

### Task 3: Context-Tool Module Split

**Files:**
- Create: `dev/plugins/dev-flow/scripts/workflow_context_inventory.py`
- Create: `dev/plugins/dev-flow/scripts/workflow_context_catalog.py`
- Create: `dev/plugins/dev-flow/scripts/workflow_context_recommendations.py`
- Create: `dev/plugins/dev-flow/scripts/workflow_context_actions.py`
- Modify: `dev/plugins/dev-flow/scripts/workflow_context_tools.py`
- Mirror the same files under `plugins/dev-flow/scripts/`

- [x] Move config, skill inventory, project signal, and context pressure functions into `workflow_context_inventory.py`.
- [x] Move source catalog URL/file loading and normalization into `workflow_context_catalog.py`.
- [x] Move recommendation/action construction and relevance helpers into `workflow_context_recommendations.py`.
- [x] Move action selection, dry-run/apply, backups, config editing, and project skill copying into `workflow_context_actions.py`.
- [x] Keep `workflow_context_tools.py` as the facade that orchestrates audit and re-exports action application.
- [x] Run context-tool tests after the split.

### Task 4: Full Verification and Plugin Eval

**Files:**
- Modify: `openspec/changes/optimize-devflow-plugin-eval-score/tasks.md`
- Modify: `.planning/STATE.md`
- Add: `.planning/verification/<timestamp>-*.md`

- [x] Run focused unittest targets.
- [x] Run full dev plugin unittest discovery.
- [x] Run release smoke tests.
- [x] Run release and development preflight.
- [x] Run OpenSpec strict validation.
- [x] Run Plugin Eval for release and development plugin roots.
- [x] Record evidence and summarize remaining warnings with follow-up recommendations.
