# Slice 7 Provider Benchmark Framework Evidence

## Contract Tests

Command:

```bash
python3.12 -m unittest dev/plugins/dev-flow/tests/test_provider_benchmark.py
```

Fresh focused release/benchmark result: `Ran 53 tests in 15.892s` and `OK`;
the benchmark contract contributes 27 tests. The complete development suite
also passed all 388 tests.

The tests cover the ten fixed tasks, four high-risk classes, fixture parity,
three repetitions, randomized order, route evidence, machine verification,
canonical artifacts, unauthorized effects, telemetry, blind review,
correction counts, every default-switch threshold, and raw-evidence
provenance. Missing, duplicate, escaping, or hash-drifted Plugin Eval result,
usage, verifier, or trace artifacts fail closed.

The live runner now freezes the release plugin, both configs, both complete
fixtures, the private task oracle, and the resolved Codex binary. Every
scenario runs from private plugin/fixture snapshots. Inputs are rehashed before
snapshotting, immediately before and after each model call, and before the final
manifest. A concurrent input edit raises `benchmark input drift` and removes
the entire run directory; the regression test proves no partial result remains
available for aggregation.

## Dry Run

The three-repetition dry-run returned:

- `validation.ok: true`;
- 60 randomized schedule entries, 30 per profile;
- identical base workspace and prompt-set hashes;
- `actualRouteEvidenceRequired: true`;
- frozen input groups for `plugin`, `configs`, `fixtures`, `taskOracle`, and
  `codexBinary`;
- `externalModelRunsPerformed: false`; and
- `writesPerformed: false`.

The planner resolved
`/Users/cY/.codex-switch/homes/internal/plugins/.plugin-appserver/codex`
(`codex-cli 0.142.5`) because the active official PATH target is unavailable.
That automatic fallback is acceptable for dry-run planning only. The live run
must first bind one approved Codex binary/model/runtime and then obtain separate
model-spend authorization.

No outcome-equivalence or default-switch claim is made. `lean-matt` remains
opt-in until 60 live runs, immutable raw evidence, blind review, and the
aggregate threshold all pass.
