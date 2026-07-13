# Slice 6 Provider-Neutral Routing and Context Evidence

## GREEN

Command:

```bash
python3.12 -m unittest \
  dev/plugins/dev-flow/tests/test_project_orchestrator.py \
  dev/plugins/dev-flow/tests/test_provider_guidance.py \
  dev/plugins/dev-flow/tests/test_runtime_gates.py
```

Result: `Ran 67 tests in 7.963s` and `OK`.

Verified behavior:

- normal guidance routes stable capability IDs and keeps OpenSpec/DevFlow
  canonical ownership independent of provider identity;
- new projects default to `core + none`;
- strict Superpowers and lean Matt details are deferred to their adapters;
- Matt implicit routing is limited to `grilling`, `tdd`,
  `diagnosing-bugs`, `code-review`, `codebase-design`, and
  `domain-modeling`;
- Matt control-plane/orchestrator skills do not become implicit DevFlow routes;
- GSD is described only as an optional roadmap provider; and
- syntax-valid but schema-invalid `.dev-flow.json` provider configuration now
  fails closed instead of silently selecting core defaults.

## Static Budget Disposition

The unsynchronized release package remains the primary Plugin Eval target and
scores `86/B`, risk `medium`, with the same three budget warnings as baseline.
The dev-path diagnostic scores `68/D`, risk `high`, because it scans source-only
tests and the large pinned benchmark provider fixtures; it reports one deferred
token failure plus complexity/readability warnings. Those fixtures are excluded
from release sync and are required for reproducible profile comparison.

This is a quality-backed blocker rather than a release-readiness pass: the final
release budget cannot be measured until an explicitly approved release sync
produces the candidate package. Residual risk is that the packaged candidate
may still need further instruction compaction after that evaluation.
