# Verification

## Commands

- `python3 -m unittest discover -s dev/plugins/dev-flow/tests`
- `python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root /Users/cy/Dev/agents-dev/cy-codex-skills/dev/plugins/dev-flow --marketplace /Users/cy/Dev/agents-dev/cy-codex-skills/.agents/plugins/marketplace.dev.json --codex-home /Users/cy/.codex --config /Users/cy/.codex/config.toml --json`

## Evidence

- Unit test and source marketplace preflight records are stored under `.planning/verification/`.

- `python3 -m unittest discover -s dev/plugins/codex-project-orchestrator/tests`: pass (.planning/verification/20260523134438-python3--m-unittest-discover--s-dev-plugins-codex-project-orches.md)

- `python3 dev/plugins/codex-project-orchestrator/scripts/codex_plugin_preflight.py --plugin-root /Users/cy/Dev/agents-dev/cy-codex-skills/dev/plugins/codex-project-orchestrator --marketplace /Users/cy/Dev/agents-dev/.agents/plugins/marketplace.json --repo /Users/cy/Dev/agents-dev/cy-codex-skills --codex-home /Users/cy/.codex --config /Users/cy/.codex/config.toml --json`: pass (.planning/verification/20260523134438-python3-dev-plugins-codex-project-orchestrator-scripts-codex_plu.md)

- `python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py`: pass (.planning/verification/20260524032233-python3--m-unittest-dev-plugins-dev-flow-tests-test_project_orch.md)

- `python3 -m unittest discover -s dev/plugins/dev-flow/tests`: pass (.planning/verification/20260524032237-python3--m-unittest-discover--s-dev-plugins-dev-flow-tests.md)

- `python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root /Users/cy/Dev/agents-dev/cy-codex-skills/plugins/dev-flow --marketplace /Users/cy/Dev/agents-dev/cy-codex-skills/.agents/plugins/marketplace.json --codex-home /Users/cy/.codex --config /Users/cy/.codex/config.toml --json`: pass (.planning/verification/20260524032243-python3-dev-plugins-dev-flow-scripts-codex_plugin_preflight.py--.md)

- `python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root /Users/cy/Dev/agents-dev/cy-codex-skills/dev/plugins/dev-flow --marketplace /Users/cy/Dev/agents-dev/cy-codex-skills/.agents/plugins/marketplace.dev.json --codex-home /Users/cy/.codex --config /Users/cy/.codex/config.toml --json`: pass (.planning/verification/20260524032251-python3-dev-plugins-dev-flow-scripts-codex_plugin_preflight.py--.md)

- `openspec validate rename-devflow --strict`: pass (.planning/verification/20260524032256-openspec-validate-rename-devflow---strict.md)

- `python3 -m unittest discover -s dev/plugins/dev-flow/tests`: pass (.planning/verification/20260524040145-python3--m-unittest-discover--s-dev-plugins-dev-flow-tests.md)

- `python3 -m unittest discover -s plugins/dev-flow/tests`: pass (.planning/verification/20260524040145-python3--m-unittest-discover--s-plugins-dev-flow-tests.md)

- `release preflight: python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root /Users/cy/Dev/agents-dev/cy-codex-skills/plugins/dev-flow --marketplace /Users/cy/Dev/agents-dev/cy-codex-skills/.agents/plugins/marketplace.json --codex-home /Users/cy/.codex --config /Users/cy/.codex/config.toml --json`: pass (.planning/verification/20260524040211-release-preflight-python3-dev-plugins-dev-flow-scripts-codex_plu.md)

- `development preflight: python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root /Users/cy/Dev/agents-dev/cy-codex-skills/dev/plugins/dev-flow --marketplace /Users/cy/Dev/agents-dev/cy-codex-skills/.agents/plugins/marketplace.dev.json --codex-home /Users/cy/.codex --config /Users/cy/.codex/config.toml --json`: pass (.planning/verification/20260524040212-development-preflight-python3-dev-plugins-dev-flow-scripts-codex.md)

- `openspec validate optimize-devflow-plugin-eval-score --strict`: pass (.planning/verification/20260524040226-openspec-validate-optimize-devflow-plugin-eval-score---strict.md)

- `plugin-eval release: node /Users/cy/.codex/plugins/cache/openai-curated/plugin-eval/6188456f/scripts/plugin-eval.js analyze plugins/dev-flow --format markdown`: pass (.planning/verification/20260524040227-plugin-eval-release-node-users-cy-.codex-plugins-cache-openai-cu.md)

- `plugin-eval development: node /Users/cy/.codex/plugins/cache/openai-curated/plugin-eval/6188456f/scripts/plugin-eval.js analyze dev/plugins/dev-flow --format markdown`: pass (.planning/verification/20260524040228-plugin-eval-development-node-users-cy-.codex-plugins-cache-opena.md)

- Final archive and commit-prep verification: pass (.planning/verification/20260524112808-final-devflow-archive-commit-prep.md)

- `python3 dev/plugins/dev-flow/scripts/check_dependencies.py --plugin-root /Users/cy/Dev/agents-dev/cy-codex-skills/dev/plugins/dev-flow --repo /Users/cy/Dev/agents-dev/cy-codex-skills --json`: pass (.planning/verification/20260524125709-python3-dev-plugins-dev-flow-scripts-check_dependencies.py---plu.md)

- `python3 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo /Users/cy/Dev/agents-dev/cy-codex-skills --json`: pass (.planning/verification/20260524125714-python3-dev-plugins-dev-flow-scripts-validate_workflow_state.py-.md)

- `python3 dev/plugins/dev-flow/scripts/doctor_workflow.py --repo /Users/cy/Dev/agents-dev/cy-codex-skills --write-report --json`: pass (.planning/verification/20260524125719-python3-dev-plugins-dev-flow-scripts-doctor_workflow.py---repo-u.md)

- `DevFlow dependency workflow verification suite`: pass (.planning/verification/20260524132559-devflow-dependency-workflow-verification-suite.md)

- `/opt/homebrew/bin/python3.11 -m unittest discover -s dev/plugins/dev-flow/tests`: pass (.planning/verification/20260525031341-opt-homebrew-bin-python3.11--m-unittest-discover--s-dev-plugins-.md)

- `context audit: codex-project-orchestrator disabled, dev-flow enabled, old plugin dirs absent`: pass (.planning/verification/20260525031341-context-audit-codex-project-orchestrator-disabled-dev-flow-enabl.md)

- `/opt/homebrew/bin/python3.11 -m unittest discover -s plugins/dev-flow/tests`: pass (.planning/verification/20260525031341-opt-homebrew-bin-python3.11--m-unittest-discover--s-plugins-dev-.md)

- `python3 -m unittest plugins/dev-flow/tests/test_release_smoke.py`: pass (.planning/verification/20260528130818-python3--m-unittest-plugins-dev-flow-tests-test_release_smoke.py.md)

- `python3 -m unittest dev/plugins/dev-flow/tests/test_dependencies.py`: pass (.planning/verification/20260528130818-python3--m-unittest-dev-plugins-dev-flow-tests-test_dependencies.md)

- `python3 -m unittest discover -s dev/plugins/dev-flow/tests`: pass (.planning/verification/20260528130818-python3--m-unittest-discover--s-dev-plugins-dev-flow-tests.md)

- `openspec validate repair-devflow-dependency-gates --strict`: pass (.planning/verification/20260528130818-openspec-validate-repair-devflow-dependency-gates---strict.md)

- `python3 -m unittest discover -s plugins/dev-flow/tests`: pass (.planning/verification/20260528130837-python3--m-unittest-discover--s-plugins-dev-flow-tests.md)

- `python3 dev/plugins/dev-flow/scripts/doctor_workflow.py --repo . --write-report --json`: pass (.planning/verification/20260528131235-python3-dev-plugins-dev-flow-scripts-doctor_workflow.py---repo-..md)

- `python3 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo . --json`: pass (.planning/verification/20260528131235-python3-dev-plugins-dev-flow-scripts-validate_workflow_state.py-.md)

- `python3 dev/plugins/dev-flow/scripts/check_dependencies.py --plugin-root dev/plugins/dev-flow --repo . --json`: pass (.planning/verification/20260528131235-python3-dev-plugins-dev-flow-scripts-check_dependencies.py---plu.md)

- `openspec validate add-obsidian-knowledge-base --strict`: pass (.planning/verification/20260528134254-openspec-validate-add-obsidian-knowledge-base---strict.md)

- `python3 -m unittest dev/plugins/dev-flow/tests/test_obsidian_kb.py`: pass (.planning/verification/20260528134255-python3--m-unittest-dev-plugins-dev-flow-tests-test_obsidian_kb..md)

- `python3 -m unittest discover -s dev/plugins/dev-flow/tests`: pass (.planning/verification/20260528134255-python3--m-unittest-discover--s-dev-plugins-dev-flow-tests.md)

- `python3 -m unittest plugins/dev-flow/tests/test_release_smoke.py`: pass (.planning/verification/20260528134255-python3--m-unittest-plugins-dev-flow-tests-test_release_smoke.py.md)

- `python3 -m unittest discover -s plugins/dev-flow/tests`: pass (.planning/verification/20260528134255-python3--m-unittest-discover--s-plugins-dev-flow-tests.md)

- `final rerun: openspec validate add-obsidian-knowledge-base --strict; python3 -m unittest discover -s dev/plugins/dev-flow/tests; python3 -m unittest discover -s plugins/dev-flow/tests; python3 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo . --json`: pass (.planning/verification/20260528134816-final-rerun-openspec-validate-add-obsidian-knowledge-base---stri.md)
