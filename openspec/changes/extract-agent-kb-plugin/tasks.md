# Tasks: Extract AgentKB plugin

## Target State

Create a complete standalone `agent-kb` plugin that owns the Markdown-first agent knowledge-base workflow. DevFlow remains a workflow orchestrator and may reference `agent-kb`, but it must not own the KB core scripts, skills, or hook behavior.

## Completion Contract

- [x] `agent-kb` dev and release plugin roots include manifest, README, hooks, scripts, skills, assets, and tests.
- [x] Marketplace files expose `agent-kb`.
- [x] Scaffold creates a Markdown canonical vault with an Obsidian-compatible profile and `.agent-kb.json` config.
- [x] Lint identifies KB health issues and writes reviewable reports.
- [x] Event capture is opt-in and sanitized.
- [x] DevFlow is decoupled from KB implementation ownership.
- [x] Acceptance Criteria are checked.
- [x] Validation Commands have been run or documented as unavailable.
- [x] Verification evidence is recorded.
- [x] Workflow state is updated.
- [x] Plugin Eval findings are optimized to grade A with remaining static deferred-budget risk recorded.

## Capability Slices

### Slice 1: Requirements and validation surface

**Status:** done

**Goal**
- Confirm behavior boundaries and add failing tests before implementation.

**Files / Modules**
- `openspec/changes/extract-agent-kb-plugin/proposal.md`
- `openspec/changes/extract-agent-kb-plugin/design.md`
- `openspec/changes/extract-agent-kb-plugin/specs/extract-agent-kb-plugin/spec.md`
- `dev/plugins/agent-kb/tests/test_agent_kb.py`
- `plugins/agent-kb/tests/test_release_smoke.py`
- `.agents/plugins/marketplace.json`
- `.agents/plugins/marketplace.dev.json`
- DevFlow tests that currently mention KB ownership

**Implementation**
- [x] Add failing tests for independent plugin manifest and marketplace registration.
- [x] Add failing tests for scaffold, lint, event capture, and skill inventory in `agent-kb`.
- [x] Add failing tests that DevFlow no longer owns KB skills or release smoke behavior.

**Tests**
- [x] Run focused tests and confirm expected failures.

**Validation Commands**
```bash
python3 -m unittest dev/plugins/agent-kb/tests/test_agent_kb.py
python3 -m unittest plugins/agent-kb/tests/test_release_smoke.py
python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py
python3 -m unittest plugins/dev-flow/tests/test_release_smoke.py
```

**Done When**
- [x] Failing tests prove the missing independent plugin and decoupling behavior.

**Risks / Rollback**
- Return to planning if a test reveals a compatibility question not captured in design.

### Slice 2: AgentKB plugin implementation

**Status:** done

**Goal**
- Implement the standalone plugin and move KB behavior into it.

**Files / Modules**
- `dev/plugins/agent-kb/.codex-plugin/plugin.json`
- `dev/plugins/agent-kb/README.md`
- `dev/plugins/agent-kb/hooks.json`
- `dev/plugins/agent-kb/assets/agent-kb.svg`
- `dev/plugins/agent-kb/scripts/workflow_agent_kb.py`
- `dev/plugins/agent-kb/scripts/kb_scaffold.py`
- `dev/plugins/agent-kb/scripts/kb_lint.py`
- `dev/plugins/agent-kb/scripts/kb_event_hook.py`
- `dev/plugins/agent-kb/skills/kb-ingest/SKILL.md`
- `dev/plugins/agent-kb/skills/kb-query/SKILL.md`
- `dev/plugins/agent-kb/skills/kb-update/SKILL.md`
- `dev/plugins/agent-kb/skills/kb-compact/SKILL.md`
- `dev/plugins/agent-kb/skills/kb-lint/SKILL.md`
- `dev/plugins/agent-kb/skills/kb-reflect/SKILL.md`
- `dev/plugins/agent-kb/skills/kb-promote/SKILL.md`
- Matching files under `plugins/agent-kb/`

**Implementation**
- [x] Create valid plugin manifests with `name: agent-kb`.
- [x] Add README sections for Markdown canonical storage, storage adapters, editor profiles, and agent adapters.
- [x] Rename the core module to `workflow_agent_kb.py`.
- [x] Rename public functions to `scaffold_agent_kb`, `lint_agent_kb`, and `record_agent_kb_event`.
- [x] Make `.agent-kb.json` the canonical config written by scaffold.
- [x] Read compatibility configs `.codex/agent-kb.json` and `.codex/obsidian-kb.json`.
- [x] Write event metadata under `<vault>/.agent-kb/events/`.
- [x] Keep the CLI names `kb_scaffold.py`, `kb_lint.py`, and `kb_event_hook.py`.
- [x] Package the same behavior under `plugins/agent-kb/`.

**Tests**
- [x] Run focused `agent-kb` tests until green.

**Validation Commands**
```bash
python3 -m unittest dev/plugins/agent-kb/tests/test_agent_kb.py
python3 -m unittest plugins/agent-kb/tests/test_release_smoke.py
```

**Done When**
- [x] Independent `agent-kb` dev and release tests pass.

**Risks / Rollback**
- If release packaging drifts from dev, resync only the `agent-kb` plugin root before proceeding.

### Slice 3: DevFlow decoupling and final verification

**Status:** done

**Goal**
- Keep DevFlow healthy while removing KB ownership from DevFlow.

**Files / Modules**
- `dev/plugins/dev-flow/README.md`
- `dev/plugins/dev-flow/hooks.json`
- `dev/plugins/dev-flow/scripts/workflow_lib.py`
- `dev/plugins/dev-flow/tests/test_project_orchestrator.py`
- `plugins/dev-flow/README.md`
- `plugins/dev-flow/hooks.json`
- `plugins/dev-flow/scripts/workflow_lib.py`
- `plugins/dev-flow/tests/test_release_smoke.py`
- `.agents/plugins/marketplace.json`
- `.agents/plugins/marketplace.dev.json`
- `.planning/STATE.md`
- `.planning/verification/`
- `openspec/changes/extract-agent-kb-plugin/tasks.md`

**Implementation**
- [x] Remove KB skills from DevFlow skill inventory expectations.
- [x] Remove DevFlow release smoke imports of KB behavior.
- [x] Remove DevFlow hook calls to `kb_event_hook.py`.
- [x] Remove or replace DevFlow README KB command docs with a pointer to `agent-kb`.
- [x] Register `agent-kb` in release and dev marketplace files.
- [x] Record verification evidence.
- [x] Update workflow state and this ledger.

**Tests**
- [x] Run both plugin suites and OpenSpec validation.

**Validation Commands**
```bash
openspec validate extract-agent-kb-plugin --strict
python3 -m unittest discover -s dev/plugins/agent-kb/tests
python3 -m unittest discover -s plugins/agent-kb/tests
python3 -m unittest discover -s dev/plugins/dev-flow/tests
python3 -m unittest discover -s plugins/dev-flow/tests
```

**Done When**
- [x] `agent-kb` is independently packaged, DevFlow tests pass, and verification evidence exists.

**Risks / Rollback**
- Keep archive blocked until verification evidence is recorded.

### Slice 4: Plugin Eval hardening

**Status:** done

**Goal**
- Address the `plugin-eval` findings from the first `agent-kb` evaluation without changing the intended KB behavior.

**Files / Modules**
- `dev/plugins/agent-kb/skills/*/SKILL.md`
- `plugins/agent-kb/skills/*/SKILL.md`
- `dev/plugins/agent-kb/scripts/`
- `plugins/agent-kb/scripts/`
- `dev/plugins/agent-kb/tests/`
- `plugins/agent-kb/tests/`
- `.planning/verification/`
- `.planning/STATE.md`

**Implementation**
- [x] Rewrite all AgentKB skill descriptions to start with clear `Use when ...` trigger sentences.
- [x] Shorten skill descriptions enough to return trigger budget from heavy to moderate.
- [x] Split `workflow_agent_kb.py` into focused scaffold, lint, event, config, template, and markdown modules.
- [x] Add quality regression tests for skill trigger descriptions, Python line length, function complexity, and plugin-eval file complexity.
- [x] Keep dev and release plugin scripts synchronized.
- [x] Record the remaining static deferred-budget warning as a known residual risk.

**Tests**
- [x] Run focused AgentKB dev and release suites.
- [x] Run Plugin Eval on dev and release plugin roots.
- [x] Run plugin manifest validation on dev and release plugin roots.
- [x] Run OpenSpec strict validation and DevFlow suites.

**Validation Commands**
```bash
node /Users/cY/.codex/plugins/cache/openai-curated/plugin-eval/9b3c8689/scripts/plugin-eval.js analyze /Users/cY/dev/skills/cy-codex-skills/plugins/agent-kb --format markdown
node /Users/cY/.codex/plugins/cache/openai-curated/plugin-eval/9b3c8689/scripts/plugin-eval.js analyze /Users/cY/dev/skills/cy-codex-skills/dev/plugins/agent-kb --format markdown
python3 /Users/cY/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py /Users/cY/dev/skills/cy-codex-skills/plugins/agent-kb
python3 /Users/cY/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py /Users/cY/dev/skills/cy-codex-skills/dev/plugins/agent-kb
openspec validate extract-agent-kb-plugin --strict
python3 -m unittest discover -s dev/plugins/agent-kb/tests
python3 -m unittest discover -s plugins/agent-kb/tests
python3 -m unittest discover -s dev/plugins/dev-flow/tests
python3 -m unittest discover -s plugins/dev-flow/tests
```

**Done When**
- [x] `plugin-eval` reports grade A for both dev and release `agent-kb` plugin roots.
- [x] The original weak description, long-line, and Python complexity warnings are gone.

**Risks / Rollback**
- `plugin-eval` still reports a static deferred-token warning because this plugin intentionally bundles executable scripts and tests. Active budget remains moderate.

## Execution Ledger

| Slice | Status | Evidence |
|---|---|---|
| Requirements and validation surface | done | Red tests failed against missing standalone plugin and DevFlow-owned KB behavior; final validation passed. |
| AgentKB plugin implementation | done | `agent-kb` dev and release plugin tests passed. |
| DevFlow decoupling and final verification | done | OpenSpec strict validation and dev/release plugin suites passed. |
| Plugin Eval hardening | done | `plugin-eval` improved from 55/D/high risk to 95/A/medium risk for dev and release plugin roots. |

## Acceptance Criteria

- [x] `agent-kb` appears in `.agents/plugins/marketplace.json` and `.agents/plugins/marketplace.dev.json`.
- [x] `agent-kb` plugin manifests are valid and use `displayName: AgentKB`.
- [x] `agent-kb` generated vault instructions say Markdown is canonical and Obsidian is an editor profile.
- [x] `agent-kb` scaffold writes `.agent-kb.json`.
- [x] Event capture writes to `.agent-kb/events/` and redacts prompt/output/secrets.
- [x] Legacy `.codex/obsidian-kb.json` config is still readable.
- [x] DevFlow no longer lists KB skills as native DevFlow skills.
- [x] DevFlow release smoke no longer imports KB core behavior.
- [x] No Feishu sync or cloud-document storage behavior is implemented.

## Validation Commands

```bash
openspec validate extract-agent-kb-plugin --strict
python3 -m unittest dev/plugins/agent-kb/tests/test_agent_kb.py
python3 -m unittest plugins/agent-kb/tests/test_release_smoke.py
python3 -m unittest discover -s dev/plugins/dev-flow/tests
python3 -m unittest discover -s plugins/dev-flow/tests
```

## Final Verification

- [x] Focused `agent-kb` tests pass.
- [x] Broader DevFlow and AgentKB plugin suites pass.
- [x] OpenSpec strict validation passes.
- [x] Plugin Eval reports `95/100`, grade `A`, for both dev and release `agent-kb` roots.
- [x] Verification evidence is recorded.
