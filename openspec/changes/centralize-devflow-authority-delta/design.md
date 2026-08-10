## Context

See `proposal.md` for motivation and the delta specifications for normative behavior. This design is shaped by the following current-state evidence:

- The repository is a brownfield Full OpenSpec project. OpenSpec `1.7.0` and the vendored methodology sources validate, but the current worktree is missing its `.agents/skills` project links. That is a bounded project-local activation drift, not missing product authority.
- `workflow_side_effect_policy.py` is the narrowest existing policy seam, but it only checks whether an unscoped authorization string is present. `workflow_continuation.py` separately maps invalid canonical state and implementation-readiness repair to `AWAIT_HUMAN`.
- `workflow_generated_artifacts.py` already provides strong owner, identity, exact-path, receipt, and idempotency checks for `AUTO_CLEAN`. The orchestration and CLI still describe every apply as requiring explicit human authorization.
- `workflow_release_sync.py` and `workflow_project_refresh.py` provide mature sealed plan/apply/verify patterns. Git routing provides only read-only reachability; there is no fast-forward proof, exact candidate/index binding, commit/push/readback executor, publication executor, or five-layer parity receipt.
- The development and generated release plugin versions are on the `0.3.x` line. The repository has no `.github/workflows` publication mechanism and no immutable release tag policy.
- The packaged runtime was byte-reproducible for source files, but its schema-v2 manifest recorded an absolute Python executable in `buildCommand`, and its legacy `sourceCommit` could refer to the pre-build parent while the packaged bytes matched a newer worktree. A containing Git commit cannot be self-recorded inside a file in its own tree without a circular identity. The schema-v3 target therefore uses a deterministic source-tree digest as the authoritative provenance identity and retains schema-v1/v2 readers only for compatibility.
- The authoritative repository is `git@github.com:cYz26/cy-codex-skills.git`, the authorized branch is `main`, the local marketplace id is `cy-codex-skills`, and the plugin id is `dev-flow`. The initial reviewed base `f8f42cd208a6b15ab415025f6fd62f003178d77e` became historical after readback found `origin/main` at `9366e8ae63752a9ce86bd52a814233ca74edc16e`. Decision `HG-BASELINE-9366E8A-001` authorizes that exact replacement base plus bounded reconciliation of the ten overlapping paths, without merge, rebase, force-push, or any change to the named downstream effects. The replacement base is re-read and must still match immediately before mutation.
- The current source checkout `/Users/cy/Dev/agents-dev/cy-codex-skills` is at the same base and is the only project refresh target authorized by this milestone. It currently contains unrelated user work, so its exact fast-forward boundary must fail closed unless it is clean when the post-publication step executes; this evidence drift is a technical stop, not a new authority request. No consumer project is in scope.

### Skill Routing Ledger

| Field | Status | Evidence / reason |
| --- | --- | --- |
| `artifact-status` | `final` | All behavior-changing decisions are resolved below; there are no Open Questions. |
| `capability-research` | `required/used` | Local CLI, source/release trees, remote refs, marketplace/cache metadata, release generation, and migration plan were inspected. No web-only product decision is required. |
| `decision-resolution` | `required/used` | The user explicitly resolved the Human-Gate principle and successively granted one standing milestone authority for commit, push, publication, and named refresh. |
| `decision-grilling` | `required/skipped` | No unresolved product or ownership choice remains after the explicit amendments and repository-derived identities. |
| `implementation-planning` | `required/used` | This document, the delta specs, Completion Contract, and `tasks.md` are the canonical implementation plan. |
| `architecture-guidance` | `required/used` | `codebase-design` was used to select one deep policy module and narrow boundary adapters instead of duplicating checks. |
| `domain-language-modeling` | `required/used` | `domain-modeling` was used to define the vocabulary below inside canonical OpenSpec rather than create a competing root context file. |
| `openspec-routing` | `required/used` | The change uses proposal, design, delta specs, executable tasks, strict validation, apply, sync, and completion verification. Archive is excluded. |

### Capability Evidence Ledger

| Claim | Evidence class | Current evidence | Contract consequence |
| --- | --- | --- | --- |
| OpenSpec planning is available | authoritative current | `openspec status` reports `1.7.0` and the change artifacts | Full OpenSpec remains canonical. |
| Project skill activation drift is local and exact | local scan | dependency check reports trusted vendored/global bytes but missing `.agents/skills`; migration plan names 16 links | Run one exact project-local activation receipt before implementation and re-verify; do not refresh cache or other projects. |
| Existing cleanup is safe enough to automate | source + tests map | sealed task ownership, owner-exit, identity, quarantine, and receipt checks already exist | Reuse it; do not implement a second deletion engine. |
| Current publication path is descriptive only | local scan | no `.github/workflows`; Git path stops at `ls-remote`; release docs are guidance | Add an executable, fakeable milestone boundary and a tag-bound workflow. |
| Runtime build provenance is not portable | byte/hash comparison | packaged source hashes match while `sourceCommit` and absolute `buildCommand` do not describe the candidate portably | Normalize commands and bind exact source-tree/file digests; retain legacy fields compatibly. |
| Version/ref/channel are deterministic | repository identity + approved rule | non-breaking capability release from `0.3.x`, `origin/main`, stable DevFlow channel | Resolve `0.4.0` and `dev-flow-v0.4.0` without another question. |

### Domain vocabulary

- **Authority Envelope**: the Goal, active OpenSpec behavior, semantic plan, write set, risk class, targets, and exclusions already approved by the user.
- **Authority Delta**: a proposed action or changed identity that is not covered by the current Authority Envelope or materially changes the risk borne by the user.
- **Standing Milestone Authority**: a sealed, predeclared grant for a specific milestone effect sequence. It cannot be inferred from a phase name, old receipt, chat-only note, or generic release flag.
- **Standing Goal Execution Authority**: the stable task/provider/model/credential-policy/cost-policy/serial boundary approved for repeated execution within one Goal. It survives ordinary attempt completion or failure until one of those stable dimensions or the Goal contract changes.
- **Attempt Receipt**: one run's technical evidence and lifecycle identity. It may be one-use for replay safety, but consuming or invalidating it does not consume the standing human authority that allowed another same-boundary attempt.
- **Candidate Payload Manifest**: the exact reviewed tracked and declared generated payload, with path, mode, size, and SHA-256. The manifest file itself is sealed by an outer receipt to avoid self-hash cycles.
- **Gate Key**: a stable digest of concrete missing authority plus the bound action and identity. The same unresolved delta has one question and one receipt.
- **Technical Repair Stop**: a fail-closed stop caused by failing or incomplete technical evidence. It permits only approved diagnosis/repair and is not a Human Gate.
- **Effect Receipt**: a before/after, identity-bound record for one external boundary, recoverable through authoritative readback.
- **Publication Identity**: plugin id, version, commit, immutable tag, channel, release URL/state, declared asset names, sizes, and SHA-256 values.

An incidental-finding disposition describes critical-path handling. An authority decision describes whether the action is permitted. They are related but are not aliases.

## Goals / Non-Goals

**Goals:**

- Make one total, pure, testable authority resolver the source of policy truth for continuation, minimal repair, exact cleanup, technical stop, and Human Gate decisions.
- Keep predeclared model execution under one standing Goal authority across attempt failure, bounded repair, evidence refresh, refreeze, and retry; record actual monetary cost without manufacturing a per-attempt currency gate.
- Make `awaiting_human` impossible without a current resolution containing concrete missing authority, while atomically maintaining both state markers and deduplicating repeated gates.
- Provide a recoverable milestone state machine that validates, commits, pushes, publishes, reads back, and refreshes only a predeclared identity.
- Preserve default-deny behavior for existing projects and every undeclared external effect.
- Make release assets reproducible and bind review, candidate, Git, publication, cache, and project identities into one terminal receipt.

**Non-Goals:**

- No PR, merge, rebase, force-push, OpenSpec archive, unrelated plugin publication, consumer-project refresh, broad deletion, or historical cleanup.
- No production dependency, selectable policy variant, background service, mutating hook, workflow-configuration key, or project-schema advance.
- No automatic product/ownership decision, new provider/account/credential privilege, global/workstation configuration, or recovery by switching to a higher-risk execution/publication path. Model execution is automatic only when an explicit standing Goal execution envelope already grants its exact stable boundary.
- No promise that a technical failure is automatically repairable. Fail-closed repair may stop execution while still avoiding a false Human Gate.

## Decisions

### 1. A pure authority-delta kernel owns classification

Add `scripts/workflow_authority_delta.py` with a single public resolver:

```python
resolve_authority_delta(
    *,
    request: Mapping[str, object],
    authority_envelope: Mapping[str, object],
    evidence: Mapping[str, object],
    standing_contract: Mapping[str, object] | None = None,
) -> dict[str, object]
```

The result preserves a versioned JSON shape with exactly one of `CONTINUE`, `CONTINUE_WITH_MINIMAL_GUARD`, `DEFER_AND_CONTINUE`, `WAIT_OWNER`, `AUTO_CLEAN`, `FAIL_CLOSED_REPAIR`, or `AWAIT_HUMAN`; stable `reasonCodes`; `missingAuthority`; `invalidations`; `materialDelta`; contract/evidence digests; and `gateKey` only when appropriate.

Precedence is:

1. untrusted or ambiguous ownership/risk and authority-bearing target or identity drift;
2. material authority delta;
3. technical evidence failure requiring bounded repair;
4. active owner wait;
5. exact task-owned `AUTO_CLEAN`;
6. one required minimal guard;
7. approved deferral;
8. ordinary continuation.

Unknown inputs default to `FAIL_CLOSED_REPAIR` when more evidence can be produced within authority, and to `AWAIT_HUMAN` only when the missing fact is itself an ownership, target, permission, product, or material-risk decision. `AWAIT_HUMAN` is invalid unless `missingAuthority` is non-empty. Contextual envelopes name exact allowlists for ownership and risk as well as action, effect, target, and write set; a globally recognized token is not authority unless that envelope covers it. Missing or malformed identity dimensions and noncanonical collections fail closed before guard, deferral, owner-wait, or cleanup classification.

`workflow_side_effect_policy.side_effect_decision` remains as a schema-v1 compatibility adapter. Continuation, cleanup orchestration, release, Git, refresh, guidance, and validators consume the new result rather than reimplementing classification.

Alternative considered: expand each existing caller's conditionals. Rejected because it preserves contradictory precedence and makes regression coverage combinatorial.

### 2. Stable execution authority is separate from attempt receipts

For `model.*` effects, the request carries an `execution` mapping with stable
`taskId`, `provider`, `model`, `credentialPolicy`, `costPolicy`, and `serial`
fields plus an ephemeral `attemptId`. The Authority Envelope carries the same
stable fields under `standingExecution` and deliberately has no attempt id.
The supported cost policy is `record_actual_no_currency_gate`: actual spend is
retained as evidence, while no per-run currency threshold or confirmation is
invented.

Malformed execution identity is a technical repair stop. A different task,
provider, model, credential privilege, cost policy, or concurrency policy is a
concrete authority delta. A different attempt id is not. An incomplete,
consumed, stale, or failed attempt receipt is represented by technical evidence
and returns `FAIL_CLOSED_REPAIR`; after bounded repair/refreeze produces current
evidence, another attempt under the same standing envelope returns `CONTINUE`.
The resolver does not require the release-oriented Standing Milestone Contract
for such a covered `model.*` request merely because its risk is declared
external. Git, publication, installation, cache, project, and release effects
retain their existing standing-milestone rules.

Alternative considered: put the run id or exact receipt path in the human
authority identity. Rejected because replay safety and permission lifetime are
different concerns, and coupling them forces a false Human Gate after every
ordinary technical retry.

### 3. One controlled recorder owns Human-Gate state

Add `workflow_authority_gate.py` and a narrow CLI. The recorder accepts only a current resolver receipt, revalidates its bound state/evidence, and atomically writes:

```text
current_stage: awaiting_human
current_change.status: awaiting_human
authority_gate.key: <digest>
authority_gate.missing_authority: [...]
authority_gate.next_question: <one concrete question>
```

The same seam clears both markers after the authority envelope incorporates the answer. State validation rejects mismatched markers, missing gate evidence, or awaiting state written for a technical failure. Gate-key replay is read-only.

Gate recording uses a same-directory write-ahead intent that binds the exact
pre-gate STATE digest, Goal/change, resolver identity, gate key, and final
receipt bytes. If execution stops between receipt persistence and dual-marker
activation, retry may finish only that exact transition; any state or identity
drift remains a technical failure. The final v1 receipt shape stays compatible
and replaces the private intent only after STATE readback succeeds.

Stop, doctor, hooks, validators, and review remain read-only observers. `workflow_continuation` adds `FAIL_CLOSED_REPAIR` as a technical terminal/continuation result without removing the existing six compatibility actions; old callers receive additive fields until migrated.

Alternative considered: let Stop or doctor repair state. Rejected because diagnostic entry points must not synthesize authority or mutate workflow state.

### 4. Existing lifecycle engines remain authoritative boundary adapters

The resolver delegates facts, not mutations:

- Generated Artifact Lifecycle supplies registration, ownership, exact-path, owner-exit, retention, and identity facts. For `AUTO_CLEAN`, the orchestrator supplies the existing explicit apply flag automatically, then revalidates the cleanup receipt. The mutation flag remains an execution safeguard but is no longer interpreted as a Human Gate.
- Release Sync supplies sealed local source-to-release promotion.
- Project Refresh supplies sealed project plan/apply/verify/rollback.
- A new named-cache adapter wraps exactly one `codex plugin add dev-flow@cy-codex-skills --json` target and records before/after cache identities. It cannot enumerate or refresh additional plugins.

Stale but reproducibly regenerable plans return `FAIL_CLOSED_REPAIR` and may be replanned only for the same contract identity. Ownership ambiguity, protected/history content, or target expansion returns `AWAIT_HUMAN`.

Alternative considered: replace the mature cleanup and refresh engines. Rejected because their stronger existing safety proofs should be composed, not duplicated.

### 5. Milestone effects use a sealed, resumable state machine

Add `workflow_milestone_external_effects.py` plus `milestone_external_effects.py` with `plan`, `advance`, and `verify` operations. Pure orchestration is separated from true external adapters so tests can use a real temporary Git remote and fakes only for GitHub/Codex boundaries.

The state sequence is:

```text
CONTRACT_VALIDATED
→ LOCAL_RELEASE_PROMOTED
→ VALIDATION_CURRENT
→ REVIEW_CURRENT
→ CANDIDATE_FROZEN
→ INDEX_EXACT
→ COMMITTED
→ PUSH_PREFLIGHT_CURRENT
→ PUSHED_READBACK_CURRENT
→ TAGGED_READBACK_CURRENT
→ PUBLISHED_READBACK_CURRENT
→ SOURCE_FAST_FORWARDED
→ CACHE_REFRESHED
→ PROJECT_REFRESHED
→ FIVE_LAYER_VERIFIED
→ COMPLETE
```

Every step has a before-intent and after/readback receipt. Reentry examines authoritative state and resumes the first incomplete same-identity step. Source and project recovery verify a persisted pending intent before replanning, so a plan whose transition changes after apply cannot trigger the effect twice. Cache recovery distinguishes a pending intent whose authoritative identity is already current from one that failed before the effect: the former completes by readback without another apply, while the latter may retry only the same sealed cache plan. A failed technical boundary, reviewed-diff drift, or incomplete evidence is `BLOCKED_RETRYABLE` or `FAIL_CLOSED_REPAIR`; it never fabricates missing authority. A changed remote base, tag collision, or concrete unnamed target is a material target-authority delta and returns a concrete `AWAIT_HUMAN` resolution. A same-identity Release that is visible while its tag-bound Action is incomplete is `PUBLICATION_PENDING`, not a collision or Human Gate, and refresh remains blocked until complete readback.

Invocation-owned release staging records directory and member type/device/inode/size/mtime/ctime/link-count identities. Cleanup removes exact registered members one by one and the resulting empty directory only after revalidation; injected hard links or other membership drift preserve the staging tree and return technical failure.

Release promotion is before candidate freeze. After push, release sync is dry-run/readback only. Any tracked drift blocks tag creation rather than creating a second commit.

Before candidate freeze, an explicit same-change re-promotion may rebuild the
local generated release after a bounded repair only when source and generated
release name the same active change and refresh revision, project schema is
unchanged, and neither configuration-sensitive nor manifest identity drift is
present. The option is default-off for upgrade/history validation; it cannot
silently waive a missing refresh revision for an established project.

The reviewed commit freezes tracked workflow state with matching
`current_stage: external_effects` and `current_change.status: external_effects`
plus the current standing-contract and evidence digests. After that commit, the
durable terminal receipt is authoritative for milestone completion. The
executor must not rewrite tracked workflow state to `complete` after push,
because doing so would create an unreviewed second diff/commit. A later tracked
status roll-forward requires its own authorized candidate; it is not part of
this milestone.

The milestone CLI accepts only the canonical contract path for the active
change. Plan, apply/reentry, and verify share one authority guard bound to the
namespaced STATE, active Goal/change, full verification gates, canonical
contract path and bytes, project `.dev-flow.json` full-OpenSpec mode, OpenSpec
bytes, write set, and exact candidate/validation/review documents. After the
commit exists, the guard reads STATE, `.dev-flow.json`, the contract, and
OpenSpec from that same Git tree rather than trusting later worktree bytes.
Duplicate-key JSON and a commit whose file mode differs from the manifest fail
closed before further effects.

The candidate does not trust caller-authored `pass` flags. It binds strict,
versioned validation and independent-review evidence documents by
repository-relative path and SHA-256, and the runtime re-reads those exact
documents from the same trusted worktree or candidate commit used by the
authority guard. The validation and review receipts are deterministic acyclic
projections of those documents plus the candidate back-reference; a caller
cannot substitute a higher Plugin Eval score or lower P0/P1 count. Canonical
validation commands are fixed by a checked-in versioned policy and compared
exactly rather than accepted as arbitrary non-empty shell strings.
Validation enumerates the canonical focused/broad/release/OpenSpec/validator/
doctor/parity/runtime checks, release-target Plugin Eval score/findings and
dispositions, secret and unexpected-file scans, and blockers. Review names the
independent read-only reviewer, exact candidate, reviewed diff, and P0/P1
counts. Unknown fields, duplicate keys, missing provenance, forged
projections, non-canonical commands, or malformed requested-effect collections
are technical failures, not synthetic Human Gates. One shared strict milestone
contract validator is consumed by the standing resolver and external-effects
executor; only a well-formed concrete effect or target outside that validated
grant can reach `AWAIT_HUMAN`.

Release assets remain outside the Git write set but inside the canonical
receipt binding. Plan, every same-identity reentry, and terminal verification
re-read the exact asset directory and member name/type/size/SHA-256 inventory.
The deterministic bundle builder likewise removes only invocation-registered
members after revalidating directory and member identities; recursive cleanup
is forbidden when membership drifts.

Because tracked STATE is itself in the candidate, its three evidence fields
would otherwise create a cryptographic self-hash cycle. The v1 binding uses one
acyclic projection: only `candidate_digest`, `validation_digest`, and
`review_digest` are replaced by a fixed sentinel while hashing STATE; the
candidate uses that normalized STATE record, and validation/review projections
replace only their candidate back-reference with the candidate projection.
Every other byte and every raw manifest file SHA-256 remains exact. Any drift
outside those three declared cycle edges invalidates the standing milestone.

Alternative considered: one shell script. Rejected because crash recovery, identity readback, test seams, and effect-specific safety require explicit durable transitions.

### 6. Git mutation is exact and fast-forward-only

Extend `workflow_git.git_transport_preflight` with expected remote commit, candidate commit, and ancestry proof. The milestone adapter:

1. verifies the payload manifest and an uncontaminated index;
2. stages only manifest paths using literal pathspecs;
3. verifies index path/mode/blob identity;
4. creates one commit with `feat(dev-flow): centralize authority-delta execution`;
5. requires `refs/heads/main` still equals the frozen base and the candidate descends from it;
6. pushes exactly `HEAD:refs/heads/main` without force;
7. uses `git ls-remote` readback to require the remote ref equals the candidate commit.

Detached worktree state is allowed because the authoritative target ref is explicit and the source checkout is not used to construct the commit. No implicit upstream, alternate branch, merge, rebase, or force fallback exists.

Alternative considered: create and later merge a task branch. Rejected because PR/merge are excluded and the user explicitly authorized the current task to update the authoritative branch after all gates pass.

### 7. Publication is deterministic, immutable, and Actions-first

Add a checked-in stable release policy and a tag-bound `.github/workflows/publish-dev-flow.yml`. The policy derives the next non-breaking capability release from `0.3.x` as `0.4.0`, tag `dev-flow-v0.4.0`, channel `stable`, remote `origin`, ref `refs/heads/main`, and plugin id `dev-flow`.

The workflow is present in the reviewed commit, has least-privilege `contents: write`, checks out the exact tag with a commit-pinned checkout action, runs only checked-in Python/standard-library packagers and validators, and creates the GitHub Release through the runner-provided GitHub CLI. It never accepts a manually supplied tag, version, asset glob, or alternate repository.

Declared assets are:

- `dev-flow-0.4.0.zip` — deterministic plugin bundle from `plugins/dev-flow/`;
- `dev-flow-0.4.0.release-manifest.json` — plugin/version/tag/commit-independent tree and asset metadata;
- `dev-flow-0.4.0.sha256` — exact SHA-256 lines for all published binary/manifest assets;
- `devflow_runtime.pyz`, `devflow_runtime.MANIFEST.json`, and `devflow_runtime.sha256` — the verified runtime artifacts already shipped in the plugin;
- `dev-flow-v0.4.0.md` — reviewed release notes.

The deterministic bundle excludes its outer release manifest and checksum file, avoiding self-hash cycles. Runtime and plugin ZIP members use the stored representation with fixed order, timestamps, modes, and metadata, so zlib/toolchain compression differences cannot change reviewed bytes. The candidate payload manifest binds all tracked release inputs and locally reproduced assets; a checked-in expectation receipt outside the plugin ZIP binds the exact seven asset names, sizes, and SHA-256 values without a self-cycle, and the outer milestone receipt binds the candidate manifest's own SHA-256 and the independent review receipt.

The tag-bound workflow rebuilds into a task-owned directory, runs the checked-in expectation verifier, and only then invokes immutable Release creation. A name, size, member-set, or SHA mismatch fails the Action before publication; it cannot create an immutable but unrecoverably mismatched release and rely on later readback to discover the error.

`package_devflow_release_runtime.py` emits schema v3, normalizes the recorded build command to repository-relative logical arguments, and makes `sha256:<sourceTreeSha256>` plus its structured `sourceIdentity` the authoritative provenance. Verification accepts schema-v1/v2 manifests under their old contract and requires the stronger identity for schema v3. This is an additive asset-format evolution, not a project persistence migration.

The executor creates and pushes the immutable tag only after branch readback. Publication completion requires GitHub readback of release state, tag, commit, asset names, sizes, and downloaded SHA-256 values. Existing identical publication is idempotently reused. Any mismatch is a collision; nothing is deleted, retagged, overwritten, or force-updated.

Alternative considered: local `gh release create` from the workstation. Rejected as the primary path because tag-bound Actions is reproducible and does not couple native Git success to workstation GitHub control-plane authentication.

### 8. Named refresh proves five-layer identity

Post-publication refresh is exactly:

1. read-only source/release parity in the milestone commit;
2. publication asset/tag/commit readback;
3. receipt-bound fast-forward of only `/Users/cy/Dev/agents-dev/cy-codex-skills` after proving its clean worktree, exact branch/remote, expected base, remote published commit, and fast-forward ancestry;
4. targeted local marketplace refresh for `dev-flow@cy-codex-skills`;
5. cache verification for that exact plugin/version/tree;
6. `plugin_project_migration.py plan/apply/verify` for that same source checkout only, bound to the published plugin identity;
7. final source/release/published/cache/project receipt comparison.

The source checkout must be clean and fast-forwardable to the already-read-back commit. The refresh adapter may fast-forward only this declared checkout before planning its references. It may not touch `game-dev-plugins`, any other consumer, another marketplace, or another plugin.

The current worktree's missing project-skill links are a separate prerequisite receipt: the canonical activation writer may create only the exact `.agents/skills` links named by its dry-run and must verify them against trusted source bytes. This local reversible repair grants no cache/publication/project authority and is repeated as a final published-identity verification rather than treated as publication success.

Alternative considered: use the broad updater apply path. Rejected because it can enumerate multiple configured plugins and consumers and cannot prove the milestone's exact target set.

### 9. Project refresh impact is explicit and default-deny

Classify impact as `changed`. Advance the versioned refresh contract from revision 9 through revision 11, retain `fixtures/project-refresh/authority-milestone-cases-v10.json`, and add the source/release `standing-execution-cases-v11.json` pair with current tracked digests. Project schema remains 8 because no `.dev-flow.json` key or reader contract changes.

Generated `AGENTS.md` and `ENGINEERING_POLICY.md` guidance explain authority delta, technical repair, `AUTO_CLEAN`, and standing milestone contracts. Existing projects without a standing contract remain default-deny, retain historical/user files, and require no cleanup. Refreshing guidance remains an explicit receipt-bound project operation; merely upgrading the plugin does not grant external effects.

Alternative considered: advance project schema solely for prose/policy changes. Rejected because schema advancement is reserved for configuration-sensitive reader behavior and would manufacture a migration that is not required.

### 9. Test at public seams and real local boundaries

TDD targets only stable public behavior:

- resolver and gate recorder results/state invariants;
- continuation and Stop/doctor/hook consumption;
- generated-artifact orchestration using the existing lifecycle interface;
- milestone plan/advance/verify;
- Git preflight and a real temporary bare remote;
- publication, cache, and project adapters faked only at their true external process/API boundary;
- release packager determinism and source/release parity.

The long-run fixture contains at least 20 dependency-ordered transitions, including minimal guard, derived evidence refresh, owner wait, `AUTO_CLEAN`, validation, review, commit, push, publication, cache, and project refresh. Its successful run asserts zero `AWAIT_HUMAN`; injected ambiguity, drift, target expansion, and collisions stop before mutation. Crash injection after each external step proves idempotent same-identity recovery.

Internal helper calls and implementation order are not mocked. This keeps refactoring freedom behind the public resolver and milestone interfaces.

## Target State and Completion Contract

The target state is one authority vocabulary, one pure classification seam, one controlled gate writer, and one recoverable milestone executor used consistently by source, generated release, skills, templates, validation, and runtime guidance.

Completion requires all of the following:

1. Every resolver request returns one exclusive decision; `AWAIT_HUMAN` always has concrete `missingAuthority`, and no other decision may persist awaiting state.
2. `current_stage` and `current_change.status` cannot diverge at a Human Gate; identical `gateKey` replay produces no new question or state transition.
3. Approved local repair, derived evidence/provenance refresh, predeclared read-only review, and exact task-owned cleanup produce no extra Human Gate.
4. Regression cases cover ordinary continuation, minimal guard, `AUTO_CLEAN`, active owner, ambiguity, drift, true external delta, invalidation, gate deduplication, remote divergence, reviewed-diff drift, partial push/readback failure, tag collision, partial publication/readback failure, asset mismatch, unnamed refresh, cache/project drift, and idempotent reentry.
5. A dependency-ordered simulation performs more than ten steps with zero false `AWAIT_HUMAN`; all injected true authority, ambiguity, drift, and identity cases fail closed before mutation.
6. Focused and broad DevFlow tests, strict OpenSpec validation, workflow validators/doctor, pre-promotion tests, source/release parity, runtime verification, and release-target Plugin Eval pass.
7. No P0 or P1 finding remains in an independent read-only review. The reviewed diff and exact candidate payload remain identical through commit.
8. Project Refresh Impact revision 11 proves changed guidance/runtime/package bytes while preserving schema 8 and default-deny compatibility.
9. The milestone creates exactly one commit, fast-forward pushes `main`, verifies remote readback, creates or reuses exactly one matching immutable tag and GitHub Release, verifies every declared asset SHA-256, then refreshes only the named DevFlow marketplace/cache/source project and proves five-layer identity.
10. PR, merge, force-push, archive, unnamed release/refresh, broad deletion, and historical cleanup counts remain zero.

## Execution Contract

### Critical path and incidental budget

Critical path: characterize policy → resolver RED/GREEN → integrate consumers and state → automate exact cleanup → implement milestone/Git boundaries → make release deterministic and publishable → update guidance/refresh contract → integrated verification/review → execute the preauthorized milestone.

Incidental budget: one bounded RED/GREEN guard per newly exposed defect that is necessary for a listed Completion Contract item and fits the approved write set. After the guard, execution returns to the critical path. A finding may be deferred only if the Completion Contract remains fully true.

Escalation triggers are material authority deltas, not labels: undeclared dependency or version, public/persistence contract expansion beyond this additive release format, project-schema/configuration change, new repo/ref/channel/version ambiguity, credential/model-cost acquisition, new consumer, protected or unowned deletion, irreversible migration, force/merge/PR/archive, severe safety risk, or write-set expansion outside the planned roots.

### Implementation readiness

`implementation_readiness.required` remains `false`: the approved plan selects no external implementation provider. The project-local skill activation drift is repaired through the canonical exact activation writer and verified before TDD; it does not select or invoke a provider.

### Standing Milestone External Effects Contract

| Field | Bound value |
| --- | --- |
| Goal | Systemically reduce false Human Gates while preserving fail-closed safety and complete the verified DevFlow release chain. |
| Change | `centralize-devflow-authority-delta` |
| Milestone | `dev-flow-authority-delta-v0.4.0` |
| Plugin / marketplace | `dev-flow` / `cy-codex-skills` |
| Version rule / resolved version | first non-breaking capability release after checked-in `0.3.x` → `0.4.0` |
| Authoritative remote / ref | `origin` (`git@github.com:cYz26/cy-codex-skills.git`) / `refs/heads/main` |
| Expected base | `9366e8ae63752a9ce86bd52a814233ca74edc16e`, authorized by `HG-BASELINE-9366E8A-001` and revalidated before candidate mutation and push |
| Tag / channel | `dev-flow-v0.4.0` / `stable` |
| Publication mechanism | checked-in tag-bound GitHub Actions workflow in the reviewed candidate |
| Assets | the seven exact assets listed in Decision 6; no globs at execution time |
| Asset expectation | checked-in `evidence/dev-flow-0.4.0.release-assets.json`, outside the plugin ZIP and bound by the standing write set |
| Commit message | `feat(dev-flow): centralize authority-delta execution` |
| Refresh targets | named marketplace/cache `dev-flow@cy-codex-skills`; source checkout `/Users/cy/Dev/agents-dev/cy-codex-skills` |
| Failure strategy | preserve commit/tag; one same-identity diagnosis and at most one applicable repair; otherwise fail closed; never use force or a second publication mechanism |
| Reentry strategy | authoritative readback, reuse matching effects, resume first incomplete step, never duplicate an effect |
| Exclusions | PR, merge, rebase, force-push, archive, other release, other plugin, `game-dev-plugins`, and every unnamed consumer/project |

This table is the standing authority instance for this change. `tasks.md` is the active dependency-ordered Execution Ledger. No task or phase may enlarge the table.

### Planned write sets

| Slice | Owner | Write set | Required evidence |
| --- | --- | --- | --- |
| Project-local prerequisite | primary | exact ignored `.agents/skills` links named by canonical activation plan and its local receipt | dry-run, apply, dependency recheck; no cache/consumer writes |
| Authority policy | primary | `dev/plugins/dev-flow/scripts/workflow_authority_delta.py`, gate/state/continuation/side-effect callers, schemas, focused fixtures/tests | RED/GREEN plus state atomicity/dedup evidence |
| Lifecycle/guidance | primary | generated-artifact orchestration/CLI/docs; DevFlow skills; root and template `AGENTS.md`/`ENGINEERING_POLICY.md` guidance | focused lifecycle tests and generated guidance assertions |
| Milestone/Git | primary | milestone modules/CLI/schemas/docs, `workflow_git.py`, focused fixtures/tests | real temporary remote matrix and crash-reentry matrix |
| Release/publication | primary | version manifests, deterministic package scripts, release policy/notes, `.github/workflows/publish-dev-flow.yml`, release tests | reproducible asset hashes and tag/readback contract tests |
| Refresh compatibility | primary | refresh verifier, named-cache adapter, refresh contract revision 11, schema-8 fixtures/tests | plan/apply/verify fakes, legacy default-deny, five-layer parity |
| Generated release | primary | `plugins/dev-flow/**`, marketplace release metadata | release promotion receipt, source/release parity, release-target Plugin Eval |
| Canonical planning/evidence | primary | this OpenSpec change, `.planning/devflow/**`, and the active ledger/evidence surfaces | validators, exact candidate/review/verification receipts |

All discovery subagents are read-only under validated Agent Task Contracts. The final independent reviewer is also read-only and receives the frozen diff and validation receipts. The primary agent owns OpenSpec, root control-plane, release generation, integration, external effects, and completion claims.

### Validation commands

The task list records exact focused test commands as files are introduced. Final validation includes at least:

```bash
openspec validate centralize-devflow-authority-delta --strict
openspec validate --all --strict
PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest \
  dev.plugins.dev-flow.tests.test_authority_delta_policy \
  dev.plugins.dev-flow.tests.test_continuous_execution_contract \
  dev.plugins.dev-flow.tests.test_generated_artifact_lifecycle \
  dev.plugins.dev-flow.tests.test_git_transport_preflight \
  dev.plugins.dev-flow.tests.test_milestone_external_effects \
  dev.plugins.dev-flow.tests.test_runtime_gates \
  dev.plugins.dev-flow.tests.test_release_sync \
  dev.plugins.dev-flow.tests.test_project_refresh
PYTHONDONTWRITEBYTECODE=1 python3.12 dev/scripts/run_devflow_prepromotion_tests.py
PYTHONDONTWRITEBYTECODE=1 python3.12 dev/plugins/dev-flow/scripts/verify_release_runtime.py
PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_*.py'
PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest discover -s plugins/dev-flow/tests -p 'test_*.py'
python3 dev/plugins/dev-flow/scripts/sync_release_assets.py --repo . --check
plugin-eval start plugins/dev-flow --request "Evaluate this plugin." --format markdown
plugin-eval analyze plugins/dev-flow --format markdown
python3 dev/scripts/codex_auto_update_plugins_skills.py --json
git diff --check
```

Final external verification additionally runs the milestone CLI plan/advance/verify, native Git `ls-remote` readbacks, GitHub Actions/Release readback, asset downloads with SHA-256 verification, target-specific cache verification, and project migration plan/apply/verify for the one named source checkout.

## Migration Plan

1. Activate and verify only the current worktree's exact project skill links so project-local capability routing is trustworthy. Preserve the plan and receipt; do not refresh caches or consumers.
2. Implement resolver and gate state additively. Keep side-effect schema v1, existing continuation keys, generated-artifact schemas, project-refresh v1 receipts, and `git.push_pr` compatibility routing. Legacy candidate v1 documents with no deletion field retain their original `{files,assets}` digest semantics; a new optional `deletions` member becomes authoritative only when present and is then included in the payload digest.
3. Update callers, skills, templates, root guidance, and validators to consume the new model. Existing projects with no standing contract remain default-deny.
4. Add milestone/release contracts, deterministic packagers, publication workflow, and refresh impact revisions 10-11. Promote source to generated release before candidate freeze.
5. Freeze, validate, and independently review the exact candidate. Any drift invalidates the freeze and returns to validation/review without widening authority.
6. Execute commit → branch push/readback → tag/publication/readback → named source fast-forward/cache/project refresh → five-layer verify under the standing contract.

Rollback before commit is ordinary exact local edit reversal. After branch push, do not rewrite history: follow-up repair requires a new reviewed commit and authority evaluation. After tag push, preserve the immutable tag and publication evidence; never delete or retarget it automatically. Cache/project refresh uses its recorded rollback only if the same named target and pre-refresh identity remain provable. Existing historical files and receipts are never cleanup candidates.

## Risks / Trade-offs

- **[Risk] A pure resolver can become a policy dumping ground.** → Keep mutation and evidence gathering in narrow adapters; resolver inputs are typed facts and output is one small versioned result.
- **[Risk] Compatibility adapters may temporarily expose both old and new vocabulary.** → Add fields without removing old keys, test both views, and make new state invariants authoritative.
- **[Risk] Candidate, review, and receipt files can form self-hash cycles.** → Hash the payload in one manifest and seal that manifest/review in an outer execution receipt; never require a file to contain its own digest or containing commit. Represent approved tracked deletions as explicit sorted candidate paths, separate from present-file byte records, and prove their absence again in the index and committed tree.
- **[Risk] Tag publication succeeds after the local process loses its receipt.** → Read back tag, Release, and every asset before any retry; matching identity is success, mismatch is a collision.
- **[Risk] GitHub Actions or Release control plane is unavailable.** → Preserve the pushed commit/tag, allow one configured same-identity diagnosis/remediation, stop without switching to a local high-risk publication mechanism.
- **[Risk] Release zip or runtime assets differ across machines.** → Fixed ordering/timestamps/modes, repository-relative build metadata, standard-library packaging, local-vs-Action hash comparison, and publication download verification.
- **[Risk] A broad updater touches unrelated consumers.** → Use a target-specific adapter and reject any target not exactly named in the milestone contract before invoking a writer.
- **[Risk] New guidance silently widens old projects.** → No standing contract means default-deny; project schema remains 8; revision-10 fixtures prove legacy behavior and no historical cleanup.
- **[Risk] Current remote `main` moves during the long validation window.** → Bind the expected base at freeze, re-read before candidate mutation and push, require exact equality/fast-forward, and stop without rebase/merge/force on divergence. A moved base invalidates the candidate and requires one new exact-base standing grant plus full reconciliation, validation, independent review, and refreeze; it never inherits authority from historical digests.
- **[Risk] The current worktree is detached.** → Push only the explicitly bound candidate commit to the explicitly bound ref after ancestry proof; never infer a branch from local HEAD state.
