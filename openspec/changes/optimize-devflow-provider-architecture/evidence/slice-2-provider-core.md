# Slice 2 Provider Registry and Core Facade Evidence

## RED

- Initial provider suite: 11 tests, 11 expected failures because
  `workflow_provider_profiles` did not exist.
- Workflow config alias test initially failed because
  `read_workflow_mode_config()` exposed no provider fields.

## GREEN

Command:

```bash
python3.12 -m unittest \
  dev/plugins/dev-flow/tests/test_provider_profiles.py \
  dev/plugins/dev-flow/tests/test_runtime_gates.py -v
```

Result: `Ran 31 tests in 0.272s` and `OK`.

Implemented and verified:

- machine-readable 3-profile/2-roadmap registry;
- complete ten-capability and thirteen-side-effect/default-deny schemas;
- canonical and alias provider config parsing;
- `resolve_provider_selection`, `diagnose_provider_selection`, and dry-run
  `provider_activation_plan` facade;
- core/none independence;
- orthogonal strict/roadmap selection;
- manifest-declared hook behavior;
- single-root ambiguity detection;
- allowed/excluded Matt mapping;
- separate provider readiness and canonical evidence readiness;
- on-demand goal readiness.

No provider install, lock write, config persistence, or migration action ran.
