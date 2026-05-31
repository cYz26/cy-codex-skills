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

- `archive gate review: openspec status --change extract-agent-kb-plugin --json; openspec validate --all --strict; python3 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo . --json; python3 dev/plugins/dev-flow/scripts/doctor_workflow.py --repo . --write-report --json; python3 dev/plugins/dev-flow/scripts/check_dependencies.py --plugin-root dev/plugins/dev-flow --repo . --json`: pass (.planning/verification/20260529153107-archive-gate-review-openspec-status---change-extract-agent-kb-pl.md)

- `python3 -m unittest dev/plugins/dev-flow/tests/test_compact_recovery.py`: pass (.planning/verification/20260529153457-python3--m-unittest-dev-plugins-dev-flow-tests-test_compact_reco.md)

- `python3 -m unittest discover -s plugins/dev-flow/tests`: pass (.planning/verification/20260529153457-python3--m-unittest-discover--s-plugins-dev-flow-tests.md)

- `openspec validate --all --strict`: pass (.planning/verification/20260529153457-openspec-validate---all---strict.md)

- `python3 -m unittest discover -s dev/plugins/dev-flow/tests`: pass (.planning/verification/20260529153457-python3--m-unittest-discover--s-dev-plugins-dev-flow-tests.md)

- `python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root dev/plugins/dev-flow --repo . --marketplace .agents/plugins/marketplace.dev.json --json`: pass (.planning/verification/20260529153508-python3-dev-plugins-dev-flow-scripts-codex_plugin_preflight.py--.md)

- `python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root plugins/dev-flow --repo . --marketplace .agents/plugins/marketplace.json --json`: pass (.planning/verification/20260529153508-python3-dev-plugins-dev-flow-scripts-codex_plugin_preflight.py--.md)

- `python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root ./dev/plugins/dev-flow --repo . --marketplace .agents/plugins/marketplace.dev.json --json`: pass (.planning/verification/20260529153520-python3-dev-plugins-dev-flow-scripts-codex_plugin_preflight.py--.md)

- `shasum -a 256 dev/plugins/dev-flow/hooks.json plugins/dev-flow/hooks.json ~/.codex/plugins/cache/cy-codex-skills/dev-flow/0.3.0+codex.20260529145038/hooks.json dev/plugins/dev-flow/scripts/compact_recovery_hook.py plugins/dev-flow/scripts/compact_recovery_hook.py ~/.codex/plugins/cache/cy-codex-skills/dev-flow/0.3.0+codex.20260529145038/scripts/compact_recovery_hook.py dev/plugins/dev-flow/scripts/workflow_compact_recovery.py plugins/dev-flow/scripts/workflow_compact_recovery.py ~/.codex/plugins/cache/cy-codex-skills/dev-flow/0.3.0+codex.20260529145038/scripts/workflow_compact_recovery.py`: pass (.planning/verification/20260529153604-shasum--a-256-dev-plugins-dev-flow-hooks.json-plugins-dev-flow-h.md)

- `codex plugin add dev-flow@cy-codex-skills`: pass (.planning/verification/20260529153605-codex-plugin-add-dev-flow-cy-codex-skills.md)

- `openspec archive extract-agent-kb-plugin --yes; openspec validate --all --strict`: pass (archived to `openspec/changes/archive/2026-05-29-extract-agent-kb-plugin/` and synced `openspec/specs/extract-agent-kb-plugin/spec.md`)

- `openspec validate --all --strict`: pass (.planning/verification/20260529154708-openspec-validate---all---strict.md)

- `python3 -m unittest dev/plugins/dev-flow/tests/test_compact_recovery.py`: pass (.planning/verification/20260529154708-python3--m-unittest-dev-plugins-dev-flow-tests-test_compact_reco.md)

- `codex plugin add dev-flow@cy-codex-skills && shasum compact recovery hook cache sync`: pass (.planning/verification/20260529154721-codex-plugin-add-dev-flow-cy-codex-skills-shasum-compact-recover.md)

## add-capability-evidence-gate

- `python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py -k capability`: pass (.planning/verification/20260530014921-python3--m-unittest-dev-plugins-dev-flow-tests-test_project_orch.md)
- `python3 -m unittest discover -s dev/plugins/dev-flow/tests`: pass, 52 tests (.planning/verification/20260530014925-python3--m-unittest-discover--s-dev-plugins-dev-flow-tests.md)
- `python3 -m unittest discover -s plugins/dev-flow/tests`: pass, 7 tests (.planning/verification/20260530014929-python3--m-unittest-discover--s-plugins-dev-flow-tests.md)
- `openspec validate --all --strict`: pass, 8 items (.planning/verification/20260530014933-openspec-validate---all---strict.md)
- `python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root dev/plugins/dev-flow --marketplace .agents/plugins/marketplace.dev.json --repo . --json`: pass (.planning/verification/20260530014937-python3-dev-plugins-dev-flow-scripts-codex_plugin_preflight.py--.md)
- `python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root plugins/dev-flow --marketplace .agents/plugins/marketplace.json --repo . --json`: pass (.planning/verification/20260530014942-python3-dev-plugins-dev-flow-scripts-codex_plugin_preflight.py--.md)
- `codex plugin marketplace add /Users/cy/Dev/agents-dev/cy-codex-skills && codex plugin add dev-flow@cy-codex-skills`: pass (.planning/verification/20260530014951-codex-plugin-marketplace-add-users-cy-dev-agents-dev-cy-codex-sk.md)
- `codex plugin list; shasum cache verification for capability-research, OPENSPEC_DESIGN template, and workflow_dependency_catalog`: pass (.planning/verification/20260530014957-codex-plugin-list-shasum-cache-verification-for-capability-resea.md)
- `python3 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo . --json; python3 dev/plugins/dev-flow/scripts/doctor_workflow.py --repo . --json`: pass (.planning/verification/20260530015002-python3-dev-plugins-dev-flow-scripts-validate_workflow_state.py-.md)

- `python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py -k capability`: pass (.planning/verification/20260530014921-python3--m-unittest-dev-plugins-dev-flow-tests-test_project_orch.md)

- `python3 -m unittest discover -s dev/plugins/dev-flow/tests`: pass (.planning/verification/20260530014925-python3--m-unittest-discover--s-dev-plugins-dev-flow-tests.md)

- `python3 -m unittest discover -s plugins/dev-flow/tests`: pass (.planning/verification/20260530014929-python3--m-unittest-discover--s-plugins-dev-flow-tests.md)

- `openspec validate --all --strict`: pass (.planning/verification/20260530014933-openspec-validate---all---strict.md)

- `python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root dev/plugins/dev-flow --marketplace .agents/plugins/marketplace.dev.json --repo . --json`: pass (.planning/verification/20260530014937-python3-dev-plugins-dev-flow-scripts-codex_plugin_preflight.py--.md)

- `python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root plugins/dev-flow --marketplace .agents/plugins/marketplace.json --repo . --json`: pass (.planning/verification/20260530014942-python3-dev-plugins-dev-flow-scripts-codex_plugin_preflight.py--.md)

- `codex plugin marketplace add /Users/cy/Dev/agents-dev/cy-codex-skills && codex plugin add dev-flow@cy-codex-skills`: pass (.planning/verification/20260530014951-codex-plugin-marketplace-add-users-cy-dev-agents-dev-cy-codex-sk.md)

- `codex plugin list; shasum cache verification for capability-research, OPENSPEC_DESIGN template, and workflow_dependency_catalog`: pass (.planning/verification/20260530014957-codex-plugin-list-shasum-cache-verification-for-capability-resea.md)

- `python3 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo . --json; python3 dev/plugins/dev-flow/scripts/doctor_workflow.py --repo . --json`: pass (.planning/verification/20260530015002-python3-dev-plugins-dev-flow-scripts-validate_workflow_state.py-.md)

- `python3 -m unittest discover -s dev/plugins/dev-flow/tests`: pass (.planning/verification/20260530030118-python3--m-unittest-discover--s-dev-plugins-dev-flow-tests.md)

- `python3 -m unittest discover -s plugins/dev-flow/tests`: pass (.planning/verification/20260530030118-python3--m-unittest-discover--s-plugins-dev-flow-tests.md)

- `openspec validate --all --strict`: pass (.planning/verification/20260530030118-openspec-validate---all---strict.md)

- `python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root dev/plugins/dev-flow --marketplace .agents/plugins/marketplace.dev.json --repo . --json`: pass (.planning/verification/20260530030118-python3-dev-plugins-dev-flow-scripts-codex_plugin_preflight.py--.md)

- `python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root plugins/dev-flow --marketplace .agents/plugins/marketplace.json --repo . --json`: pass (.planning/verification/20260530030118-python3-dev-plugins-dev-flow-scripts-codex_plugin_preflight.py--.md)

- `codex plugin marketplace add /Users/cy/Dev/agents-dev/cy-codex-skills && codex plugin add dev-flow@cy-codex-skills`: pass (.planning/verification/20260530030118-codex-plugin-marketplace-add-users-cy-dev-agents-dev-cy-codex-sk.md)

- `shasum -a 256 dev/plugins/dev-flow plugins/dev-flow installed-cache key compact files`: pass (.planning/verification/20260530030118-shasum--a-256-dev-plugins-dev-flow-plugins-dev-flow-installed-ca.md)

- `python3 dev/plugins/dev-flow/scripts/compact_recommendation.py stopping/continuation probes`: pass (.planning/verification/20260530030118-python3-dev-plugins-dev-flow-scripts-compact_recommendation.py-s.md)

## refine-compact-followup-gate

- `python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py -k compact`: pass, 4 focused tests (.planning/verification/20260530030149-python3--m-unittest-dev-plugins-dev-flow-tests-test_project_orch.md)
- `python3 -m unittest discover -s dev/plugins/dev-flow/tests`: pass, 56 tests (.planning/verification/20260530030118-python3--m-unittest-discover--s-dev-plugins-dev-flow-tests.md)
- `python3 -m unittest discover -s plugins/dev-flow/tests`: pass, 8 tests (.planning/verification/20260530030118-python3--m-unittest-discover--s-plugins-dev-flow-tests.md)
- `openspec validate --all --strict`: pass, 10 items (.planning/verification/20260530030118-openspec-validate---all---strict.md)
- `development plugin preflight: python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root dev/plugins/dev-flow --marketplace .agents/plugins/marketplace.dev.json --repo . --json`: pass (.planning/verification/20260530030139-development-plugin-preflight-python3-dev-plugins-dev-flow-script.md)
- `python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root plugins/dev-flow --marketplace .agents/plugins/marketplace.json --repo . --json`: pass (.planning/verification/20260530030118-python3-dev-plugins-dev-flow-scripts-codex_plugin_preflight.py--.md)
- `codex plugin marketplace add /Users/cy/Dev/agents-dev/cy-codex-skills && codex plugin add dev-flow@cy-codex-skills`: pass (.planning/verification/20260530030118-codex-plugin-marketplace-add-users-cy-dev-agents-dev-cy-codex-sk.md)
- `shasum -a 256 dev/plugins/dev-flow plugins/dev-flow installed-cache key compact files`: pass (.planning/verification/20260530030118-shasum--a-256-dev-plugins-dev-flow-plugins-dev-flow-installed-ca.md)
- `python3 dev/plugins/dev-flow/scripts/compact_recommendation.py stopping/continuation probes`: pass (.planning/verification/20260530030118-python3-dev-plugins-dev-flow-scripts-compact_recommendation.py-s.md)
- `final state checks: python3 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo . --json; python3 dev/plugins/dev-flow/scripts/doctor_workflow.py --repo . --json; openspec validate --all --strict`: pass (.planning/verification/20260530030410-final-state-checks-python3-dev-plugins-dev-flow-scripts-validate.md)

- `python3 -m unittest discover -s dev/plugins/dev-flow/tests`: pass (.planning/verification/20260531053556-python3--m-unittest-discover--s-dev-plugins-dev-flow-tests.md)

- `python3 -m unittest discover -s plugins/dev-flow/tests`: pass (.planning/verification/20260531053603-python3--m-unittest-discover--s-plugins-dev-flow-tests.md)

- `python3 dev/plugins/dev-flow/scripts/claude_code_delegate.py --repo /Users/cy/Dev/agents-dev/cy-codex-skills --check --json`: pass (.planning/verification/20260531053608-python3-dev-plugins-dev-flow-scripts-claude_code_delegate.py---r.md)

- `openspec validate --all --strict`: pass (.planning/verification/20260531053613-openspec-validate---all---strict.md)

- `python3 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo /Users/cy/Dev/agents-dev/cy-codex-skills --json`: pass (.planning/verification/20260531053617-python3-dev-plugins-dev-flow-scripts-validate_workflow_state.py-.md)

- `node /Users/cy/.codex/plugins/cache/openai-curated/plugin-eval/fef63ecf/scripts/plugin-eval.js analyze plugins/dev-flow --format markdown`: pass (.planning/verification/20260531053742-plugin-eval-analyze-plugins-dev-flow.md)
