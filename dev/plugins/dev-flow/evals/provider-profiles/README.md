# DevFlow Methodology Provider Benchmark

This corpus compares `strict-superpowers` and `lean-matt` outcomes under the
same isolated task, model, sandbox, approval policy, verifier, resource limits,
and randomized schedule. It measures observed execution outcomes; static skill
size alone is not evidence of equivalence.

The ten task IDs and the four high-risk classes are fixed in both configuration
files. Prompts are provider-neutral. The fixtures have identical content hashes
after excluding only the selected profile, project skill links, provider runtime
snapshot, and production provider lock. Fixtures live under
`dev/plugins/dev-flow/fixtures/provider-profiles/`, outside the source paths
Plugin Eval statically analyzes and outside release-sync inputs. Each fixture
supplies a minimal `codex-home`, a production-schema provider lock, and exact
`SKILL.md` hashes. The project-local skills and runtime provider roots are pinned
snapshots of the real mapped skills, not benchmark-specific substitutes.

Every task has concrete seeded facts and a public output schema under
`benchmark-inputs/`. The bug task includes failing code and a regression test;
the review task includes a patch; stale-evidence and checkpoint tasks include
their conflicting source artifacts. The model sees required keys, types, and
canonical artifact paths but not expected values. Those values and diff
contracts remain in `evals/provider-profiles/task-oracles.json`, which is never
copied into the model workspace or passed through the Codex environment.

## Safe local validation

Configuration validation and planning do not run a model or create the output
directory:

```bash
python3.12 dev/plugins/dev-flow/scripts/run_provider_benchmark.py \
  --plugin-root plugins/dev-flow \
  --strict-config dev/plugins/dev-flow/evals/provider-profiles/benchmark.strict-superpowers.json \
  --lean-config dev/plugins/dev-flow/evals/provider-profiles/benchmark.lean-matt.json \
  --repetitions 3 \
  --output-root .planning/devflow/evals/dry-run \
  --dry-run
```

The dry-run prints both Plugin Eval commands, all sixty randomized
`profile + task_id + repetition` entries, fixture/prompt/provider/skill hashes,
the DevFlow commit, and the controlled resource settings. It also freezes the
plugin tree, both benchmark configs, both complete fixture trees, the private
task oracle, and the resolved Codex binary by path, version, and SHA-256.

## Authorized execution only

A live run spends model budget and therefore requires separate user approval.
After that approval, repeat the command without `--dry-run` and add
`--execute-authorized`. The runner copies the release plugin into a temporary
directory, copies the selected fixture into a separate per-scenario private
snapshot, points Plugin Eval at that snapshot's Codex config, and writes only
temporary data plus the explicit `--output-root`. It rechecks every frozen input
before each snapshot, before each model call, after each call, and before the
final manifest. Any drift invalidates and removes the whole run output so a
mixed-input result cannot enter aggregation.

Each scenario is isolated. A timeout is recorded as exit 124 with its partial
stdout/stderr, then the randomized schedule continues. Non-zero scenarios are
also retained rather than truncating the evidence set.

Live output is not a default-switch decision. Normalize the machine evidence,
add blind-review scores and human correction counts through the tracked import
workflow below, retain the immutable raw files, and run the aggregate gate. Even
a passing aggregate only makes lean eligible for a separate approved
default-change proposal.

## Reproducible blind review

After a complete live run, create a profile-free packet, a private identity map,
and an unfilled decision template. Keep the map away from the reviewer until all
decisions are final:

```bash
python3.12 dev/plugins/dev-flow/scripts/aggregate_provider_benchmark.py \
  --prepare-review-from <run-root>/execution-manifest.json \
  --evidence-root <run-root> \
  --review-packet <run-root>/review/blind-packet.json \
  --review-map <run-root>/review/private-map.json \
  --review-decisions <run-root>/review/decisions.json
```

The reviewer records their identity, a 0–5 score, correction count, and optional
notes for every blind ID. Import the completed file without editing normalized
runs by hand:

```bash
python3.12 dev/plugins/dev-flow/scripts/aggregate_provider_benchmark.py \
  --apply-review-from <run-root>/execution-manifest.json \
  --evidence-root <run-root> \
  --review-packet <run-root>/review/blind-packet.json \
  --review-map <run-root>/review/private-map.json \
  --review-decisions <run-root>/review/decisions.json \
  --output <run-root>/normalized-evidence.json
```

Finally run the decision gate:

```bash
python3.12 dev/plugins/dev-flow/scripts/aggregate_provider_benchmark.py \
  --input <run-root>/normalized-evidence.json \
  --evidence-root <run-root> \
  --output <run-root>/aggregate.json
```

The normalized file is accepted only when its runs exactly match the hashed
execution drafts and the packet, private map, and reviewer decisions. Each raw
manifest also binds the run identity and full repository, prompt, provider, and
skill hashes. Hand-edited scores or source hashes therefore fail provenance.

## Evidence boundary

Every valid run must record:

- repository, prompt, provider, and skill SHA-256 values;
- actual provider route evidence (installation alone is invalid);
- machine-verifier and canonical artifact results;
- unauthorized side effects;
- token, tool-call, and elapsed telemetry when emitted;
- a blind-review score and human correction count; and
- a hash-verified raw manifest covering telemetry, route, canonical, and
  side-effect evidence.

Plugin Eval's verifier validates public output structure and production provider
resolution. The runner independently derives task correctness from the private
oracle, canonical compliance and corruption from Plugin Eval's actual workspace
diff plus artifact contents, and unauthorized effects from unexpected paths and
forbidden raw commands. Agent-authored pass booleans are ignored.

Route evidence is also independent of the agent claim: the runner parses actual
`codex exec --json` `item.completed` / `command_execution` events and accepts
only successful reads of a pinned `SKILL.md` mapped to the scenario's expected
capability. Reading an unrelated provider skill does not satisfy routing. If the
trace, workspace diff, private task result, canonical artifact, or capability
route cannot be independently verified, the run fails and cannot support a
default switch. Raw evidence remains at its recorded immutable location until
the default-provider decision is archived.
