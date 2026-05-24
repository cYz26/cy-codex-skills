## 1. Baseline and Tests First

- [x] 1.1 Record the current Plugin Eval baseline for release and development plugin roots.
- [x] 1.2 Add or update tests that assert DevFlow manifests expose at most three default prompts.
- [x] 1.3 Add tests that assert context-tool facade imports and core audit/apply behavior continue to work after module splitting.
- [x] 1.4 Add release-package smoke tests for manifest and context-tool behavior.
- [x] 1.5 Run focused tests and confirm the new expectations fail before implementation where behavior is not yet present.

## 2. Full Implementation

- [x] 2.1 Trim release and development plugin default prompts to three high-value starters.
- [x] 2.2 Shorten high-cost skill descriptions while preserving routing intent.
- [x] 2.3 Split context-tool implementation into focused inventory, catalog, recommendation, and action modules.
- [x] 2.4 Keep `workflow_context_tools.py` as a compatibility facade for existing CLIs and exports.
- [x] 2.5 Remove Python long-line warnings in affected context-tool files.
- [x] 2.6 Mirror required release/development package changes consistently.

## 3. Verification and Evaluation

- [x] 3.1 Run focused context-tool and packaging tests.
- [x] 3.2 Run full development plugin unittest discovery.
- [x] 3.3 Run release-package smoke tests.
- [x] 3.4 Run DevFlow preflight for release and development plugin roots.
- [x] 3.5 Run `openspec validate optimize-devflow-plugin-eval-score --strict`.
- [x] 3.6 Run Plugin Eval for release and development plugin roots and compare against baseline.
- [x] 3.7 Record verification evidence and update `.planning/STATE.md`.
