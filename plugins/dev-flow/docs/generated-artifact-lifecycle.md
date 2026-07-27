# Generated Artifact Lifecycle

The Generated Artifact Lifecycle gives a task standing authority to reclaim
only the filesystem output it registered before creation. It does not infer
ownership from a filename, extension, ignore rule, cache directory, or build
tool.

## Documents

Keep four canonical JSON documents below
`.planning/devflow/generated-artifacts/`:

1. `generated-artifact-contract/v1`, sealed before the command runs.
2. `generated-artifact-manifest/v1`, observed after the command completes.
3. `generated-artifact-cleanup-plan/v1`, the fresh read-only decision.
4. `generated-artifact-cleanup-receipt/v1`, the exact terminal mutation
   evidence.

The contract binds repository, task, run, owner, command digest, retention, and
before-state. The owner PID is paired with its process-start token when
available, so later PID reuse cannot invalidate a successful receipt. A lease
is active only while its recorded exact identity remains present. Prefer an
absent or empty task/run-specific isolated root. Adjacent output is allowed
only with a complete parent inventory and a predeclared discovery pattern;
cleanup still uses exact manifest paths.

## Runtime CLI

The CLI writes canonical JSON to stdout. The caller persists each document
before continuing:

```bash
python3 scripts/generated_artifact_lifecycle.py prepare \
  --repo . --task-id <task> --run-id <run> \
  --owner-id <owner> --owner-pid <pid> \
  --command-json '["tool","--output","<isolated-root>"]' \
  --isolated-root <isolated-root>

python3 scripts/generated_artifact_lifecycle.py observe \
  --repo . --contract <contract.json> --exit-code 0

python3 scripts/generated_artifact_lifecycle.py plan \
  --repo . --contract <contract.json> --manifest <manifest.json>

python3 scripts/generated_artifact_lifecycle.py cleanup \
  --repo . --contract <contract.json> --manifest <manifest.json> \
  --plan <plan.json> --apply
```

`prepare`, `observe`, and `plan` are read-only. `cleanup --apply` first
recomputes the plan and revalidates repository identity, owner exit, tracked
and protected state, every exact entry, hashes, and directory membership. It
uses no wildcard, recursive deletion, or symlink following.

## Decisions

- `AUTO_CLEAN`: every invariant passes after owner exit. The orchestrator may
  invoke explicit `cleanup --apply` and must retain the terminal receipt.
- `WAIT_OWNER`: the process or lease is active. Wait, then observe and plan
  again; do not delete and do not open a routine Human Gate.
- `RETAIN`: evidence or promoted output remains under the owning workflow.
- `HUMAN_GATE`: registration, baseline, ownership, scope, tracked/protected
  state, identity, membership, or another invariant is missing or unsafe.

A failed operating-system removal stops immediately and records exact removed
and remaining entries. It never reports completion or retries unrecorded work.

## Task and Worker Evidence

Main-task evidence records the contract, manifest, plan, and cleanup receipt
through `record_task_evidence.py`. An Agent Task Contract may optionally
reference the standalone contract. Its canonical worker result then references
all four lifecycle documents and sets `cleanup_complete=true`.

G41 post-validation passes only for a bound terminal receipt with every exact
target absent and no process, configuration, Git, or network effect. Tasks
without a contract keep existing behavior and gain no automatic cleanup
authority.

## Read-Only Surfaces

Workflow validation, Doctor, review, hooks, and stop policies inspect the
registered documents and report the decision plus exact next action. They never
invoke `cleanup --apply`. A post-creation or self-authored document cannot
convert pre-existing residue into owned output.
