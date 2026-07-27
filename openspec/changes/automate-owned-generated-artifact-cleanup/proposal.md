## Why

DevFlow currently treats deletion of every temporary or intermediate artifact
as destructive cleanup, even when the current task created and fully owns the
artifact. This collapses routine lifecycle reclamation and ambiguous data
deletion into the same Human Gate, causing avoidable stops while still lacking
a reusable ownership contract for generated files, directories, logs, caches,
locks, sockets, spools, and build outputs.

## What Changes

- Add a versioned Generated Artifact Contract that predeclares task/run
  ownership, command identity, allowed roots, before-state, retention, and
  cleanup policy before an artifact may qualify for automatic reclamation;
  the persisted canonical contract file identity/ctime plus each candidate's
  immutable filesystem birth time prove that registration was not
  reconstructed after creation. Filesystems without creation-time evidence
  fail closed to a Human Gate.
- Add immutable observed manifests and cleanup receipts that bind every exact
  artifact identity, descriptor-bound content digest, recoverable quarantine
  mapping, and zero unlisted mutation.
- Add one fail-closed lifecycle module with separate read-only
  classify/verify behavior and an explicit apply operation whose quarantine
  handoff uses exclusive rename and verifies the moved inode. Automatic
  cleanup removes exact paths from their declared scope but never performs a
  pathname-based final unlink/rmdir; physical quarantine purge remains a
  separate destructive Human Gate.
- Integrate the contract with DevFlow task execution and Agent Task Contracts
  so main-agent and worker artifacts follow the same rules.
- Keep validators and hooks read-only. The orchestrator may invoke automatic
  cleanup only for a contract-authorized plan after the owning process has
  exited.
- Preserve Human Gates for unregistered, pre-existing, tracked, protected,
  evidence-bearing, shared, externally located, occupied, or identity-drifted
  artifacts.
- Do not infer ownership from a filename, extension, ignore rule, or directory
  name. Existing unregistered artifacts are not retroactively authorized.
- Add source/release parity, runtime packaging, policy-template, and
  integration verification without adding a production dependency.

## Capabilities

### New Capabilities

- `generated-artifact-lifecycle`: Contract, manifest, classification,
  automatic cleanup, receipt, recovery, and validation requirements for
  task-owned temporary and intermediate artifacts.

### Modified Capabilities

- `incidental-finding-lifecycle`: Distinguish contract-authorized reclamation
  of task-owned generated artifacts from ambiguous or unowned destructive
  cleanup that remains `BLOCKED_AWAITING_HUMAN`.

## Impact

- DevFlow source scripts, runtime package manifest, release counterpart, and
  tests.
- Agent Task Contract template and validation.
- Generated project guidance in `AGENTS.md` and `ENGINEERING_POLICY.md`
  templates.
- The `game-dev` repository will be the first consumer integration, but its
  currently unregistered cleanup targets remain outside automatic authority.
- No new dependency, public network behavior, global configuration mutation,
  legacy cleanup, automatic quarantine purge, push, archive, or publication
  is introduced.

## Skill Routing Ledger

- `artifact-status`: final
- `capability-research`: skipped; the solution depends only on checked-in
  DevFlow contracts and local runtime behavior, not current external
  capability evidence.
- `decision-resolution`: used; the user selected registration-only automatic
  cleanup and rejected extension-based inference.
- `decision-grilling`: used; the ownership boundary was resolved before this
  proposal.
- `implementation-planning`: required; the change alters workflow behavior,
  schemas, runtime packaging, and project integration.
- `architecture-guidance`: used; the design places lifecycle complexity
  behind one deep module and keeps validators read-only.
- `domain-language-modeling`: skipped; the required ownership and lifecycle
  terms are explicit in the selected design and do not require a separate
  domain-modeling pass.
- `openspec-routing`: used; Full OpenSpec owns this behavior and compatibility
  change.
