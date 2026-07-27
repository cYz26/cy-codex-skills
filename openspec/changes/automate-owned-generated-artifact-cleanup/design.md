## Context

DevFlow already distinguishes read-only diagnosis from authorized mutation,
validates Agent Task Contracts, and preserves exact cleanup evidence for Human
Gates. It does not have a generic lifecycle for artifacts that the current
task creates and owns. As a result, routine generated residue is either left
behind or escalated through the same path as ambiguous destructive cleanup.

The implementation must preserve existing work in the DevFlow source tree,
keep hooks and validators read-only, avoid extension-based inference, package
the behavior into the release runtime, and remain compatible with projects
that do not opt into generated-artifact contracts.

## Goals / Non-Goals

**Goals:**

- Put registration, observation, classification, exact cleanup, and receipts
  behind one deep Generated Artifact Lifecycle module.
- Allow standing automatic cleanup authority only when a task registered
  ownership before creation and every live precondition remains true.
- Support regular files, directories, logs, caches, build outputs, locks, PID
  files, Unix sockets, spools, and other task-owned filesystem artifacts
  without relying on filename extensions.
- Give main-agent and worker execution the same contract and failure model.
- Keep unknown or drifted deletion behind a Human Gate.
- Prefer prevention and task-isolated output roots over cleanup after the fact.

**Non-Goals:**

- Retroactively claiming or deleting artifacts that lack a valid pre-creation
  contract.
- Deleting tracked source, canonical workflow state, sealed evidence, user
  input, shared caches, foreign task output, or externally located artifacts
  outside an explicitly isolated task root.
- Killing processes, releasing ports, changing configuration, cleaning legacy
  installations, or performing Git/release/publication actions.
- Adding a production dependency or a background cleanup daemon.

## Decisions

### DevFlow owns the generic lifecycle

The source DevFlow Plugin owns the generic contract, lifecycle module,
templates, schemas, and orchestration guidance. Domain Plugins such as
`ai-native-godot` may declare domain-specific isolated roots or adjacent
outputs, but they do not implement a second cleanup engine.

Alternative considered: implement cleanup only in `ai-native-godot`. Rejected
because ownership, Human Gate classification, task execution, and receipts are
cross-project workflow concerns.

### Use a pre-creation contract, observed manifest, and cleanup receipt

The lifecycle uses three immutable documents:

1. `generated-artifact-contract/v1` is sealed before the owning command runs.
   It binds task ID, run ID, owner, command digest, repository identity,
   isolated roots, explicitly declared adjacent output scopes, retention, and
   before-state. The caller persists its canonical bytes below
   `.planning/devflow/generated-artifacts/contracts/` before starting the
   command. The observed manifest records that file's exact identity and
   filesystem ctime; any candidate older than the persisted seal is
   post-created registration and cannot reach `AUTO_CLEAN`.
2. `generated-artifact-manifest/v1` is captured after the command and records
   every exact observed entry, identity field, type, content digest when
   applicable, directory membership, and owning-process completion.
3. `generated-artifact-cleanup-receipt/v1` binds the first two documents,
   decision, exact mutations, failures, postconditions, and zero unlisted
   mutation.

Alternative considered: infer ownership from `.gitignore`, extensions, or
known cache directory names. Rejected because these signals do not prove who
created a path or whether it is safe to delete.

### Prefer isolated roots and constrain adjacent outputs

An isolated root is absent before execution or is created empty and reserved
for one task/run. Its complete observed inventory may qualify for automatic
cleanup.

An adjacent output is permitted only when a tool cannot redirect output into
an isolated root. Its contract must predeclare the parent-scoped output
pattern, capture the complete before-state, and later prove that each cleanup
candidate was absent before execution, created during the owning command,
untracked, outside protected roots, and unchanged since observation.

Patterns may discover candidates, but deletion never uses a pattern or
recursive command. The manifest expands every candidate into an exact entry.

Alternative considered: allow only isolated roots. Rejected because some
compilers and interpreters create adjacent caches, but isolated roots remain
the default and recommended path.

### Keep planning read-only and execution explicit

`workflow_generated_artifacts.py` provides the lifecycle implementation.
`generated_artifact_lifecycle.py` provides a compact CLI with read-only
`prepare`, `observe`, and `plan` operations plus an explicit `cleanup --apply`
operation. `prepare` emits canonical JSON only; the caller must persist it at
the canonical contract path before running the bound command. `observe`
captures the persisted contract file identity, and `plan` verifies that anchor
without writing. The orchestrator may execute `cleanup --apply` without a
per-run Human Gate only when `plan` returns `AUTO_CLEAN`.

Hooks, stop policies, workflow validation, and project doctors may inspect and
report lifecycle state but MUST NOT invoke apply mode.

### Use four deterministic decisions

- `AUTO_CLEAN`: all registration, ownership, scope, identity, process-exit,
  protection, and retention checks pass.
- `WAIT_OWNER`: an owning process or lease is still live; retry is allowed but
  no deletion or Human Gate is created.
- `RETAIN`: the contract marks the artifact for promotion or evidence
  retention; cleanup is not attempted.
- `HUMAN_GATE`: ownership is missing or ambiguous, a baseline target existed,
  identity or membership drifted, a path is tracked/protected/shared, scope
  escaped, or cleanup would require another external effect.

Only `AUTO_CLEAN` grants standing cleanup authority. A contract cannot
authorize itself after the artifact exists.

### Apply cleanup as one fail-closed exact transaction

Immediately before the first mutation, apply mode revalidates the contract,
manifest, repository identity, process/lease state, every entry identity,
directory membership, protection rules, and tracked state. Any mismatch causes
zero mutation.

Each exact leaf is first atomically renamed to a collision-resistant quarantine
name in the same parent. The moved inode, type, content, and membership are
then verified against the manifest before final unlink/rmdir. A mismatched
replacement is restored and never deleted. Files and non-directory entries are
removed without following links. Directories are processed deepest-first only
after they are empty. No wildcard or recursive deletion is permitted. A
partial operating-system failure stops further mutation, records exact
completed and remaining entries, and requires explicit recovery from the
receipt; it never reports success.

### Integrate by reference instead of widening every task interface

The Generated Artifact Contract remains a standalone document referenced by
main-task execution records and optionally by Agent Task Contracts. Existing
tasks with no reference preserve current behavior. Worker post-validation
requires the referenced cleanup receipt before `cleanup_complete=true`.

This keeps the module interface small and avoids embedding a large artifact
inventory into TaskContract or worker-result documents.

## Completion Contract

The change is complete only when:

- all three document schemas and the lifecycle module reject unknown,
  pre-existing, tracked, protected, shared, occupied, drifted, and escaped
  targets;
- a canonical persisted contract-file identity proves pre-creation sealing,
  and any post-creation rewrite or reseal becomes `HUMAN_GATE`;
- valid isolated and adjacent task-owned artifacts produce `AUTO_CLEAN`,
  exact cleanup, idempotent post-state, and a bound receipt;
- concurrent leaf replacement cannot cause an unverified inode to be deleted;
- main-task and Agent Task Contract integration use the same lifecycle;
- hooks and validators remain read-only;
- source and release trees are byte-equivalent for managed runtime files and
  the complete lifecycle test module;
- full DevFlow tests, strict OpenSpec validation, release verification, and
  release-target Plugin Eval pass;
- the installed DevFlow cache and `game-dev` integration are refreshed only
  through the separately authorized named refresh, with no legacy cleanup;
- the pre-existing unregistered `game-dev` artifacts remain outside automatic
  authority.

## Risks / Trade-offs

- **A task registers an overbroad root** -> Require task/run isolation,
  baseline absence or exact before-state, protected-root rejection, tracked
  checks, and exact manifest expansion.
- **Concurrent creation is misattributed** -> Bind one owner/lease and return
  `WAIT_OWNER` while another owner or process is live.
- **A tool mutates a pre-existing output** -> Adjacent outputs that existed in
  the baseline are never auto-cleaned.
- **Cleanup hides useful diagnostics** -> `RETAIN` and promotion policy take
  precedence over `AUTO_CLEAN`; receipts preserve metadata and failures.
- **Partial cleanup creates uncertainty** -> Stop immediately, emit a failed
  receipt with exact completed/remaining entries, and require recovery rather
  than retrying blindly.
- **Runtime packaging overlaps another change** -> Keep source implementation
  isolated until integration, then regenerate the release runtime from the
  combined source state and preserve unrelated hook work.

## Migration Plan

1. Add RED tests and schemas without changing current cleanup behavior.
2. Implement the lifecycle module and CLI behind explicit contract references.
3. Add main-task, Agent Task Contract, policy-template, and doctor integration.
4. Regenerate the DevFlow release runtime from the combined current source
   tree and verify source/release parity.
5. Refresh only `dev-flow@cy-codex-skills`, then run `game-dev` diagnostics and
   add a project-specific contract adapter without deleting existing residue.
6. Roll back by removing contract references and restoring the prior Plugin
   cache; unreferenced projects retain their existing Human Gate behavior.

## Open Questions

None. The user selected registration-only ownership, generic artifact types,
DevFlow ownership, and no retroactive authorization.
