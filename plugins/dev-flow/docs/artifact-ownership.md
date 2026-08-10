# Artifact Ownership

DevFlow has one active canonical control plane. Git tracking is reported
independently; ignored planning files must not be described as checked in.

## Canonical

- Behavior proposal, design, specs, and tasks:
  `openspec/changes/<change-id>/`
- Execution contract and status: `TASK_LEDGER.md`
- DevFlow state and checkpoints: `.planning/devflow/**`
- Verification evidence: `.planning/devflow/verification/**`
- Durable engineering policy: `AGENTS.md` and `ENGINEERING_POLICY.md`

Only approved main-agent or explicitly serialized writes may update canonical
artifacts. Matt skills can inform decisions, tests, diagnosis, review,
architecture, and domain modeling, but their scratch output is not canonical by
itself.

## Delegated Work

Worker output is admissible only when it follows a validated Agent Task
Contract, stays inside its disjoint write set, reports verification evidence,
and passes main-agent integration review. Workers do not own OpenSpec, root
control-plane files, `.planning/devflow/**`, release metadata, or generated
release assets.

## Generated Filesystem Artifacts

A Generated Artifact Contract is a standalone, registration-only ownership
record sealed before the owning command creates output. Store the contract,
observed manifest, fresh plan, and terminal cleanup receipt under
`.planning/devflow/generated-artifacts/`; these documents are main-agent-owned
evidence even when the output belongs to a worker.

A pre-existing or unregistered path never becomes task-owned because of its
name, extension, ignore status, apparent cache/build purpose, or a
post-creation contract. Automatic cleanup is limited to exact manifest entries
under a fresh `AUTO_CLEAN` plan. Tracked, protected, shared, escaped, occupied,
symlinked, hardlinked, or drifted targets are preserved and stop fail-closed;
they become a Human Gate only when resolving them needs a concrete new
authority or material risk acceptance.

## Historical and Legacy Evidence

- `docs/history/**` is source-only historical evidence. Release sync
  excludes it, active runtime modules do not import it, and no current gate
  reads it.
- Retired configuration and local filesystem markers are inspection inputs for
  `inspect_legacy_workflow_config.py` only.
- Personal memories and chat summaries are context, never repository truth.

Historical or method evidence must be promoted into a canonical target before
it can satisfy implementation, verification, archive, or release readiness.
Ambiguous user-authored or historical files are preserved until a separately
authorized migration names exact paths and rollback evidence.
