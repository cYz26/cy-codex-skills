# Provider Benchmark Results

Do not add a result directory until an externally funded benchmark run has been
separately authorized and completed.

Each tracked `results/<run-id>/manifest.json` must contain the aggregate metrics,
failure reasons, invalid runs, provider and skill hashes, blind-review decisions,
and SHA-256 references to immutable raw evidence under
`.planning/devflow/evals/<run-id>/raw`. Raw evidence must remain available until
the default-provider decision is archived.

The tracked run must also retain the execution manifest, public blind packet,
private blind-ID map, completed reviewer decision file, normalized evidence, and
their SHA-256 provenance references. Do not hand-edit normalized runs or expose
the private map to the reviewer before decisions are complete.

An aggregate manifest cannot replace missing raw evidence and cannot change the
default provider. A passing result only supports a later, separately approved
proposal.
