## Purpose

Defines a sealed standing-authority and recoverable execution protocol for exact milestone commit, fast-forward push, deterministic publication, readback, and named DevFlow refresh without repeated authorization prompts.

## ADDED Requirements

### Requirement: Only predeclared milestones can hold standing external-effect authority
DevFlow SHALL execute milestone external effects automatically only from a current contract approved in the Goal, active OpenSpec change, and Execution Ledger before candidate freeze.

#### Scenario: Standing contract is complete
- **WHEN** a milestone is declared eligible for automatic external effects
- **THEN** its contract binds the plugin id, version rule and resolved version, authoritative remote and ref, tag and channel, publication mechanism, exact release assets, write set, refresh targets, exclusions, failure policy, and reentry policy
- **AND** ordinary task completion cannot create or enlarge that authority

#### Scenario: Contract target is ambiguous
- **WHEN** version, channel, remote, ref, publication target, asset set, cache, or project target cannot be derived uniquely from the checked-in contract and current repository identity
- **THEN** DevFlow returns `AWAIT_HUMAN`
- **AND** names that single concrete missing release authority before any external mutation

#### Scenario: Existing projects receive no implicit authority
- **WHEN** a project has no Milestone External Effects Contract
- **THEN** commit, push, publication, cache refresh, and project refresh remain default-deny
- **AND** upgrading DevFlow does not synthesize standing authority from chat, historical receipts, or repository presence

### Requirement: Candidate freeze binds exact reviewed bytes and evidence
DevFlow SHALL freeze an exact release candidate before staging or committing and SHALL invalidate the milestone if any bound input drifts.

#### Scenario: Candidate is eligible
- **WHEN** the milestone Completion Contract is complete, focused and broad tests pass, DevFlow validators pass, source/release parity is current, release-target Plugin Eval passes the declared threshold, and an independent review reports P0=0 and P1=0
- **THEN** the candidate manifest binds every reviewed file, generated release asset, release notes, version, plugin identity, evidence receipt, review receipt, and SHA-256
- **AND** a secret scan and unresolved-blocker check pass

#### Scenario: Validation and review evidence is independently verifiable
- **WHEN** validation and independent review are offered as candidate-freeze evidence
- **THEN** strict versioned receipts bind their repository-relative paths and SHA-256 values into the candidate, bind the candidate projection back into each receipt, and enumerate the canonical validation checks, Plugin Eval result and dispositions, secret scan, unexpected-file scan, unresolved blockers, reviewer identity, review mode, and P0/P1 counts
- **AND** self-authored booleans, missing provenance, unknown fields, duplicate keys, non-canonical commands, or an unbound review MUST fail closed before index mutation

#### Scenario: Declared release assets remain exact
- **WHEN** generated publication assets live in the milestone receipt directory rather than the Git write set
- **THEN** plan, reentry, and terminal verification re-read the exact bound asset directory and require every declared member's type, name, size, and SHA-256 to match the candidate
- **AND** a missing, extra, symlinked, replaced, or byte-drifted asset returns `FAIL_CLOSED_REPAIR` before index or downstream mutation

#### Scenario: Candidate or review drifts
- **WHEN** a candidate file, untracked candidate, generated asset, review digest, evidence digest, or secret-scan result differs after freeze
- **THEN** DevFlow fails closed before index mutation
- **AND** it does not repair the mismatch by silently widening the manifest

#### Scenario: Candidate contains an exact tracked deletion
- **WHEN** an approved write set removes a tracked file before candidate freeze
- **THEN** the candidate manifest binds that safe repository-relative path as an exact deletion distinct from every present file record
- **AND** worktree, literal-path index, commit tree, commit changed-path set, and same-identity reentry all prove the path remains absent; undeclared deletion, file/deletion overlap, resurrection, or deletion drift returns `FAIL_CLOSED_REPAIR` before downstream mutation

#### Scenario: Malformed requested effects are technical evidence failures
- **WHEN** the standing contract's requested-effect collection is missing, malformed, duplicated, or contains non-string values
- **THEN** DevFlow returns `FAIL_CLOSED_REPAIR`
- **AND** it does not fabricate a target authority or write `awaiting_human`; only a well-formed concrete undeclared effect can produce `AWAIT_HUMAN`

#### Scenario: Standing and execution paths share strict contract validation
- **WHEN** a standing contract has a malformed ref, incomplete identity, unavailable declared project target, invalid nested field, or non-canonical requested-effect sequence
- **THEN** the standing resolver and milestone executor return the same technical validation failure before granting or mutating anything
- **AND** only a well-formed concrete effect, target, ownership, or material-risk value outside the validated standing grant may produce `AWAIT_HUMAN`

#### Scenario: Release promotion occurs before freeze
- **WHEN** development source has a generated release counterpart
- **THEN** source-to-release promotion and validation complete before candidate freeze
- **AND** post-push release synchronization is read-only and MUST fail if it would create a second tracked change

### Requirement: Exact commit and push are single-effect recoverable steps
DevFlow SHALL stage only the frozen candidate, create one semantic milestone commit, and push it only when the declared remote ref remains safe to fast-forward.

#### Scenario: Exact index is committed
- **WHEN** the candidate manifest still matches the worktree and the Git index contains only the declared milestone write set
- **THEN** DevFlow creates exactly one commit with the declared semantic message
- **AND** records the commit and tree identity in the milestone receipt

#### Scenario: Fast-forward preflight passes
- **WHEN** the authoritative remote ref is reachable, still equals the contract's expected base, and the candidate commit descends from that base
- **THEN** DevFlow may push the exact refspec without force
- **AND** remote readback must equal the candidate commit before publication continues

#### Scenario: Remote divergence blocks push
- **WHEN** the remote ref no longer equals the expected base or a fast-forward cannot be proven
- **THEN** DevFlow stops before push
- **AND** it does not rebase, merge, force-push, or choose another ref automatically

#### Scenario: Push succeeds but receipt write is interrupted
- **WHEN** remote readback already equals the candidate commit after a local interruption
- **THEN** idempotent reentry records the completed push without pushing again
- **AND** downstream execution resumes from the same identity

### Requirement: Publication uses a deterministic tag-bound mechanism
DevFlow SHALL publish a declared stable milestone through a verified immutable tag-bound repository mechanism and SHALL prefer GitHub Actions over an ad-hoc local publication path.

#### Scenario: Stable release identity is derived
- **WHEN** a non-breaking DevFlow capability release advances the checked-in `0.3.x` line
- **THEN** the deterministic policy resolves version `0.4.0`, stable channel, and tag `dev-flow-v0.4.0`
- **AND** both development and release plugin manifests use that version before freeze

#### Scenario: Tag and Release are created
- **WHEN** commit push/readback is complete, the tag does not conflict, and the reviewed workflow exists in the tagged commit with least-privilege permissions
- **THEN** DevFlow pushes the immutable declared tag and the canonical workflow creates the GitHub Release with only the declared notes and assets
- **AND** no local `gh` credential is required for the Actions path

#### Scenario: Rebuilt assets match the frozen cross-machine identity before publication
- **WHEN** the tag-bound workflow rebuilds the seven declared assets on its publication runner
- **THEN** compression-independent archive bytes and fixed metadata reproduce the checked-in non-cyclic expectation receipt's exact names, sizes, and SHA-256 values
- **AND** any mismatch fails before `gh release create`; the workflow does not publish first and defer identity discovery to later readback

#### Scenario: Existing same-identity publication is reused
- **WHEN** the declared tag, commit, Release, asset names, sizes, and SHA-256 values already match the contract
- **THEN** reentry treats publication as complete
- **AND** it does not recreate, overwrite, retag, or re-upload the Release

#### Scenario: Tag or Release collides
- **WHEN** an existing tag, Release, version, asset, or commit differs from the declared identity
- **THEN** DevFlow fails closed with the concrete identity conflict
- **AND** it never deletes, retargets, force-updates, or overwrites the conflicting publication

### Requirement: Publication readback precedes every refresh
DevFlow SHALL require current readback of the published tag, commit, visibility, channel, asset manifest, and asset SHA-256 before refreshing any local runtime.

#### Scenario: Publication readback matches
- **WHEN** the target channel exposes the declared version, tag, commit, publication state, asset list, sizes, and SHA-256 values
- **THEN** the state machine records a publication receipt
- **AND** named refresh becomes eligible

#### Scenario: Publication or asset readback is incomplete
- **WHEN** the Release succeeds but any declared identity or asset cannot be read back or mismatches
- **THEN** DevFlow preserves the pushed commit and tag evidence
- **AND** it does not refresh marketplace, cache, or project references

#### Scenario: Publication fails after tag push
- **WHEN** the canonical workflow fails after the immutable tag exists
- **THEN** DevFlow retains the tag and performs at most the configured one diagnosis and one applicable remediation for the same publication identity
- **AND** it does not switch to a higher-risk mechanism without new authority

### Requirement: Post-publication refresh is named, sealed, and five-layer verified
DevFlow SHALL refresh only the named DevFlow marketplace, plugin cache, and current DevFlow source project references after publication identity is proven.

#### Scenario: Named refresh completes
- **WHEN** the standing contract names `dev-flow`, the `cy-codex-skills` marketplace/cache, and the current DevFlow source project as the only refresh targets
- **THEN** DevFlow first uses a receipt-bound exact fast-forward plan/apply/verify for the named clean source checkout, then target-specific plan/apply/verify receipts for cache and project refresh
- **AND** verifies source, generated release, published artifact, installed cache, and current-project identities all match

#### Scenario: Named source checkout is dirty or drifted
- **WHEN** the named source checkout is not clean, is on another branch, has another remote identity, no longer descends from the expected base, or cannot read back the published commit
- **THEN** DevFlow stops the same-identity refresh path with `FAIL_CLOSED_REPAIR` and preserves publication evidence
- **AND** it does not stash, reset, rebase, merge, overwrite user work, refresh the cache, or write `awaiting_human`

#### Scenario: Unnamed consumer is refused
- **WHEN** refresh attempts to include another plugin or consumer project
- **THEN** DevFlow rejects the target before any consumer write
- **AND** reports the concrete missing target authority

#### Scenario: Cache or project identity drifts
- **WHEN** cache verification, project plan identity, project receipt, or five-layer parity does not match the published contract
- **THEN** DevFlow fails closed and preserves every receipt
- **AND** it does not claim refresh or milestone completion

### Requirement: External-effect execution is idempotent and gate-deduplicated
DevFlow SHALL record a receipt before and after every irreversible external boundary and SHALL recover through same-identity readback rather than repeating effects.

#### Scenario: Reentry follows the first incomplete effect
- **WHEN** execution restarts after commit, push, tag, publication, source fast-forward, cache refresh, or project refresh
- **THEN** it verifies completed effects from their authoritative readback
- **AND** resumes only the first incomplete same-identity step

#### Scenario: Cache intent persisted before the effect
- **WHEN** the exact cache-refresh intent is durable but process loss or a technical boundary failure occurs before the cache identity changes
- **THEN** reentry revalidates the same plan, contract, candidate, and pending intent and retries only that same cache effect
- **AND** once authoritative cache readback is current, every later reentry is verify-only and cannot apply the refresh again

#### Scenario: Release-build cleanup observes exact membership
- **WHEN** deterministic bundle generation cleans an invocation-owned staging directory
- **THEN** it revalidates the directory identity plus every registered member's exact name, type, inode, link count, change identity, and membership before removing only those members and the empty directory
- **AND** any injected, replaced, hard-linked, symlinked, or otherwise unregistered member preserves the staging directory and returns a technical failure instead of recursively deleting caller data

#### Scenario: Complete receipt is replayed
- **WHEN** a terminal milestone receipt is evaluated again
- **THEN** the operation is read-only and returns the same complete identity
- **AND** it produces no second commit, push, tag, Release, cache apply, project apply, or Human Gate

#### Scenario: Excluded effects remain impossible
- **WHEN** the milestone executor evaluates its effect set
- **THEN** PR creation, merge, force-push, OpenSpec archive, unrelated release, unnamed plugin refresh, and unnamed consumer refresh are absent
- **AND** any attempt to add them requires a new material-authority decision
