## Context

See `proposal.md` for motivation. The current system already has the correct
human workflow shape but not a complete deterministic project-refresh seam:

- `dev-flow-refresh` owns global-before-project ordering, diagnostics, AGENTS
  review, legacy cleanup boundaries, and final evidence;
- `plugin_project_migration.py` detects plugin-version, skill-link,
  control-plane, and skill-layout drift, but `managedFiles` is empty and plugin
  release version is its only migration version;
- `inspect_legacy_workflow_config.py` safely identifies and redacts retired
  config, but intentionally exposes no apply path;
- `scaffold_workflow.py` skips an existing `.dev-flow.json` and can report an
  `AGENTS.md.generated` write even when active guidance is already current;
- ordinary migration apply mutates links before all conflicts are known, so a
  subsequent `blocked` result does not currently prove zero partial writes;
- OpenSpec project-skill refresh and release promotion already provide useful
  staging, fingerprint, verification, and rollback patterns.

Current local capability evidence on 2026-08-06:

- OpenSpec CLI `1.7.0`, Codex CLI `0.147.0-alpha.1.2`, and Python `3.12.13`;
- `codex plugin add` is a supported installation command and has structured
  `--json` output, but it is an external global action rather than a project
  migration primitive;
- workflow validation is clean, Doctor is healthy with no cache drift, project
  migration is current, and the named installed cache matches the generated
  release;
- focused baselines pass: legacy inspector 9/9, project migration 14/14,
  orchestrator 48/48, release smoke 30/30, and refresh Skill validation.

### Capability Evidence Ledger

- `authoritative_current`: local OpenSpec/Codex/Python versions and current CLI
  `--help` output; the repository's checked-in manifests, package builder, and
  release verifier are authoritative for DevFlow behavior.
- `local_scan`: refresh/migration/setup/doctor Skills; workflow config reader,
  legacy inspector, migration/activation/scaffold/validation/release modules;
  source, release, installed cache, tests, OpenSpec changes, and current state.
- `comparison`: Skill-only orchestration lacks deterministic writes; one
  global-and-project CLI combines incompatible authority; a second project CLI
  duplicates migration ownership; a thin Skill over the existing migration CLI
  gives the smallest durable interface and greatest locality.
- `assumptions`: no top-level `devflow` command registration is required. The
  already packaged Python CLI remains the compatibility surface. Real consumer
  migration and installed-cache mutation are not assumed authorized.
- `contract`: the two delta specs in this change plus the exact focused,
  pre-promotion, release-runtime, migration-matrix, and Plugin Eval commands in
  this design.

### Skill Routing Ledger

- `artifact-status: final` — no unresolved design question remains.
- `capability-research: required/used` — current CLI, source/release/cache, and
  local implementation evidence changes the safe seam.
- `decision-resolution: required/used` — three Design It Twice alternatives
  were compared through validated read-only Agent Task Contracts.
- `decision-grilling: skipped` — local evidence resolves the Skill/CLI choice;
  no product trade-off remains for the user.
- `implementation-planning: required/used` — DevFlow `ai-native-tech-plan` and
  `change-plan` shape this complete execution contract.
- `architecture-guidance: required/used` — `codebase-design` selects one deep
  migration module behind a small interface.
- `domain-language-modeling: skipped` — Refresh Plan, Receipt, and schema
  revision are implementation-contract types, not project ubiquitous language;
  creating `CONTEXT.md` would duplicate OpenSpec behavior ownership.
- `openspec-routing: required/used` — migration, compatibility, and release
  behavior use Full OpenSpec.

### Goal Contract

- **Outcome:** every supported older DevFlow project configuration can be
  planned and, with explicit authority, migrated transactionally to the current
  project contract through the existing migration CLI and refresh Skill.
- **Verification evidence:** RED/GREEN migration matrix, deterministic no-write
  snapshots, failure/rollback injection, compatibility tests, full DevFlow
  source suite, strict OpenSpec, generated release/runtime parity, and release-
  target Plugin Eval.
- **Scope:** DevFlow development source, the generated release counterpart,
  project-refresh metadata/guidance/tests, temporary fixture repositories,
  direct submission of the exact reviewed change to `origin/main`, and targeted
  refresh/readback of only `dev-flow@cy-codex-skills`.
- **Non-goals:** applying migration to a real consumer, broad plugin or Skill
  update, legacy cleanup, active AGENTS merge, dependency addition, release
  publication, PR, or archive.
- **Success threshold:** every supported baseline has one verified route to the
  current schema; default and blocked paths make zero writes; apply is atomic or
  fully rolled back; source/release contracts match; all named validators pass.
- **Stop conditions:** material public-interface expansion beyond this plan, a
  new dependency, an unrecoverable target type, destructive cleanup, consumer-
  project apply, broad installation/update, or a failure that cannot be
  contained by one in-scope RED/GREEN guard.

The Goal Suitability Gate is required by migration, multiple slices, release
risk, and cross-context delivery. On 2026-08-07 the user authorized the systemic
repair and the agent created active Goal thread
`019fda1b-d564-7c40-9d8a-e1fc47c2fe93`, binding the four review corrections,
fresh verification, exact direct-main submission, and named cache refresh while
retaining every non-goal above.

## Target State

### Goals

- Make the Skill the human interface and the existing migration CLI the one
  deterministic project interface.
- Separate project schema and refresh identity from plugin release version.
- Support known legacy config without discarding unrelated current settings.
- Centralize exact planning, authorization, transaction, verification, and
  rollback semantics.
- Turn future project-facing DevFlow changes into an executable refresh-impact
  and release gate.
- Preserve existing read-only hook/updater behavior and current projects.

### Scope / Non-Goals

- A self-updating CLI, global plugin installer, multi-project batch writer, or
  automatic project-adoption hook.
- A generic arbitrary-code migration framework for every plugin.
- Automatic overwrite/merge of active `AGENTS.md`, deletion of legacy skills or
  history, or repair of ambiguous user-authored files.
- Supporting config migration without a trusted recoverable preimage; those
  projects receive read-only evidence and a manual Human Gate.
- A second canonical task queue, delivery timeline, or planning system.

## Decisions

### Keep the Skill and deepen the existing migration CLI

The external workflow has two seams:

1. `dev-flow-refresh` — natural-language intent, global freshness, project
   discovery, authorization, AGENTS review, cross-project reporting.
2. `plugin_project_migration.py` — one project, deterministic plan/apply/verify/
   rollback, stable machine result.

The CLI exposes four operations while retaining compatibility invocations:

```bash
python3 scripts/plugin_project_migration.py plan \
  --repo <project> --plugin-root <root> --codex-home <home> --json

python3 scripts/plugin_project_migration.py apply \
  --repo <project> --expect-plan sha256:<digest> \
  --allow workflow-config-migration --json

python3 scripts/plugin_project_migration.py verify \
  --repo <project> --receipt <apply-receipt> --json

python3 scripts/plugin_project_migration.py rollback \
  --repo <project> --receipt <apply-receipt> --apply --json
```

No-subcommand `--json` remains the existing read-only summary. Existing
`--apply` routes through an in-process plan and the same transaction engine but
does not gain workflow-config authority. Hooks and updater integration continue
to call only the read-only compatibility adapter.

Alternatives considered:

- **Skill-only:** smallest code change, but ordering, status interpretation,
  stale-plan detection, and rollback stay in prompts. Rejected.
- **New `refresh_devflow_project.py`:** clean name and common-caller shape, but it
  creates a second migration CLI/state owner and leaves old apply semantics live.
  Rejected in favor of deepening the established seam.
- **One global-and-project CLI:** looks convenient but would let an old process
  update its own package, mix network/cache effects with project writes, and
  blur separate authorization. Rejected.
- **Versioned transactional engine behind the existing CLI:** selected because
  deletion of the engine would otherwise redistribute migration complexity
  across Skills, hooks, activation, and tests; it therefore earns module depth.

### Extend the existing migration manifest into the refresh contract

`.codex-plugin/project-migration.json` remains the one plugin adapter. Its next
schema separates:

```json
{
  "schemaVersion": "2.0",
  "plugin": "dev-flow",
  "projectSchema": {
    "head": 1,
    "minimumSupported": 0
  },
  "configTargets": {
    "1": "assets/project-refresh/config-v1.json"
  },
  "migrationSteps": [
    {
      "id": "legacy-selection-v0-to-v1",
      "from": 0,
      "to": 1
    }
  ],
  "refreshContract": {
    "revision": 1,
    "trackedInputs": []
  }
}
```

The manifest names stable step IDs but never imports arbitrary code. A checked-
in registry maps known IDs to pure plan/verify implementations. Every
`from` version has at most one successor, the chain to `head` is continuous,
and old versioned config targets become immutable release evidence.

The runtime computes `refreshContractDigest` from canonical manifest data and
the bytes of declared refresh-sensitive inputs. Project migration state stores:

- plugin release version;
- migration-engine schema version;
- project schema version;
- refresh-contract revision and digest;
- applied migration IDs and the last verified receipt reference.

This makes a template or skill-layout change visible even when project config
schema does not change, while config behavior changes require a new immutable
target, schema head, and migration step.

### Model migration steps as pure planners and verifiers

A migration step receives an immutable snapshot and returns typed operations;
it cannot write. The transaction module is the only implementation allowed to
promote or roll back operations.

Planned operation kinds are deliberately finite:

- create a regular file if absent;
- replace a trusted tracked JSON file with an exact preimage;
- create a symlink to a verified source;
- replace an expected symlink;
- install a verified staged tree;
- create a non-conflicting merge candidate;
- preserve/report a path;
- require named authorization or manual review.

Each operation declares exact repository-relative paths, before/after
fingerprints, dependencies, ownership, rollback source, and verification. The
engine rejects path escape, parent/child overlap, symlink parents, duplicate
ownership, unknown operation kinds, and incomplete rollback before staging.

This concentrates filesystem and TOCTOU complexity in one deep module. The
interface is also the test surface; tests assert plans, receipts, and filesystem
outcomes rather than private step functions.

### Seal plans against managed state, not unrelated WIP

A `RefreshPlan` contains:

- repository identity and adoption evidence;
- source/release/cache and refresh-contract identity;
- detected baseline and confidence evidence;
- target schema and ordered migration IDs;
- normalized actions, dependencies, exact read/write sets, and fingerprints;
- required authorizations, manual actions, preserved paths, and final
  verification contract;
- deterministic `planSha256`.

Timestamps and raw legacy values are absent from the canonical digest. Apply
recomputes the plan immediately and accepts it only if the digest, runtime
identity, exact managed paths, and authorizations match. Dirty paths outside
the managed read/write set are reported but preserved and do not stale the
plan.

Stable result statuses include `current`, `migration_pending`,
`authorization_required`, `manual_review_required`, `baseline_ambiguous`,
`plan_stale`, `blocked`, `applied_and_verified`,
`verification_failed_rolled_back`, and `rollback_failed`. Each result also
reports retryability, changed/preserved paths, rollback status, and one exact
next action. Attention and failure statuses use non-success exit classes even
if a composed legacy validator returned process exit zero.

### Restrict automatic legacy config migration to recoverable inputs

The initial schema step handles the recognized retired selection aliases already
owned by the read-only inspector:

- remove only those retired keys from root and `workflow`;
- retain all other root/workflow fields and semantic JSON values;
- set `workflow.mode` to `full-openspec`;
- never emit raw old or unrelated values.

Automatic rewrite requires a repository-local regular `.dev-flow.json`, no
conflicting aliases, and a clean Git-tracked preimage bound to the plan's commit
and blob identity. Unrelated worktree changes are allowed. A non-Git, untracked,
dirty, symlinked, unreadable, or ambiguous config remains `manual_only` rather
than copying possible secrets into an untracked backup.

An adopted project with no config may plan create-if-absent. Its rollback is an
exact conditional delete. Historical provider files, `.codex/skills`, old
planning data, hook files, and ambiguous authored content stay inspection-only;
the config writer does not import cleanup authority from the inspector.

### Apply one preflighted transaction and advance state last

Apply accepts a dependency-closed selected action set. `manual_only` actions do
not gain authority; safe independent actions may run, but the project stays
incomplete until manual gates are resolved and replanned.

The transaction sequence is:

1. resolve and validate the current plan and authorizations;
2. validate the complete selected write set and rollback source before writing;
3. stage new content below a plan-isolated same-filesystem root;
4. bind the staged manifest and fingerprints;
5. promote in deterministic order;
6. run step verification plus migration sync, workflow validation, Doctor/cache
   drift, config schema, AGENTS disposition, and managed-path readback;
7. update migration state last and emit apply/verification receipts;
8. on any failure, restore already-promoted operations in reverse order;
9. retain recovery evidence if rollback is incomplete.

Explicit rollback is receipt-bound. It refuses any path whose current identity
or bytes differ from the receipt's after state, so it cannot overwrite user work
performed after migration.

### Preserve AGENTS as a human merge seam

The planner compares active guidance with the current required durable markers
and candidate content in memory; it does not equate scaffold's hypothetical
write list with real drift.

- current active guidance: `unchanged`, no candidate;
- missing active file: create may be planned after project adoption is proved;
- stale active guidance: create-only `AGENTS.md.generated`, then
  `agents_merge_required`;
- conflicting candidate: block candidate generation and preserve both files.

The engine never writes active `AGENTS.md`. The refresh Skill explains the
candidate, the human-approved merge is promoted through the active OpenSpec or
ledger, and fresh planning/verification determines completion.

### Make refresh impact an executable release property

The refresh contract tracks the live owners of:

- immutable versioned project config targets and the active config reader;
- project migration registry/planner/verifier;
- AGENTS template and durable-marker validator;
- control-plane inventory and templates;
- project-local DevFlow skill inventory;
- OpenSpec version/layout/provenance and project-skill installer;
- refresh Skill commands and project verification contract.

Pre-promotion compares development source with the existing generated release
before promotion:

- changing an immutable released config target is rejected;
- config-sensitive behavior requires `projectSchema.head` to advance and a
  unique step/fixture from the prior head;
- any tracked-surface byte change requires `refreshContract.revision` to
  advance;
- a source change records Project Refresh Impact as `changed`,
  `verified-unchanged`, or `not-applicable` with evidence;
- missing or contradictory impact evidence fails closed.

Release packaging includes the manifest, config targets, engine, wrapper, Skill
reference, and migration fixtures. Release runtime verification compares the
computed contract digest to source; an authorized installed-cache refresh then
performs the same readback. Plugin Eval runs only against the generated release
counterpart for the formal gate.

Planning/review templates gain a concise Project Refresh Impact field. The
complete procedure remains in the Skill and release checker, not in AGENTS.

### Pre-submit systemic repair decisions

The 2026-08-07 pre-submit Standards and Spec reviews reopened this change after
finding four Completion Contract gaps. The approved repair keeps the same
public seams and makes their existing versioned behavior complete:

1. Configuration inspection never assigns schema `1` from syntax alone. It
   derives the current target schema and bytes from `projectSchema.head`,
   `configTargets`, and the ordered migration contract, including create-if-
   absent and staged-source verification for a future head greater than 1.
2. Trusted configuration and trusted stored state are independent baseline
   evidence. If they identify different schema versions, planning returns
   `baseline_ambiguous` with zero configuration or state-sync actions.
3. Project Refresh Impact compares a canonical manifest identity in addition
   to tracked-input bytes. Manifest-only changes to managed files, project-local
   Skills, migration steps, configuration targets, or AGENTS ownership require
   the same revision/evidence advance as any other refresh-sensitive change.
4. The verification receipt is independently auditable: it binds project
   schema, migration path, selected actions with before/after fingerprints,
   authorizations, changed and preserved paths, state fingerprints, action-set
   identity, verification result, and rollback status. The public receipt JSON
   schema requires those fields for verification receipts.

The first GREEN pass was rejected by the independent 2026-08-07 review because
it covered an already-current future target but did not execute supported
older-schema paths, allowed a generic `managed-refresh` label to bypass the
configuration-sensitive schema gate, and schema-validated receipt fields
without runtime tamper validation. The corrected contract therefore advances
the real project schema to head `2`, adds immutable target v2 plus one registered
v1-to-v2 pure merge step and fixture coverage, executes the complete ordered
path atomically, removes the schema-gate bypass, and runtime-validates an
independent evidence digest and both state fingerprints for apply and
verification receipts.

The confirmed TDD seams are the existing migration CLI `plan/apply/verify` JSON
and filesystem result, the Project Refresh Impact/release-gate result, and the
published receipt JSON schema. Tests use future-head and conflicting-evidence
fixtures through those seams; they do not assert private helper structure.

## Completion Contract

- The existing refresh Skill remains the natural-language entry and names the
  enhanced CLI operations without duplicating their procedure.
- Default plan, compatibility sync, hooks, and updater checks are proven
  read-only across full-tree snapshots.
- Every supported schema fixture reaches current through one unique chain;
  invalid chains and ambiguous baselines fail closed.
- Known clean tracked legacy config migrates without losing unrelated fields or
  leaking values; unsafe inputs remain untouched and manual-only.
- Selected writes are fully preflighted, transactionally verified, or restored;
  injected rollback failure is explicit and preserves recovery evidence.
- Current and legacy CLI JSON consumers remain compatible.
- AGENTS and legacy cleanup boundaries remain intact.
- Future refresh-sensitive source drift fails pre-promotion without the matching
  contract revision, schema path when needed, fixtures, and impact evidence.
- Development, generated release, runtime audit, strict OpenSpec, and release-
  target Plugin Eval pass with recorded results.

## Acceptance Criteria

- A read-only plan for one adopted project is deterministic, redacted, exact,
  and makes no filesystem or state write.
- Every supported older schema resolves through one tested migration chain;
  ambiguous, incomplete, or conflicting chains fail before apply is available.
- An authorized clean legacy configuration reaches the current schema without
  losing unrelated settings, while unsafe inputs remain byte-identical and are
  reported as manual-only.
- Complete preflight precedes every selected write; success is freshly verified,
  and any promotion or verification failure restores all promoted paths or
  returns explicit retained recovery evidence.
- Current read-only hook/updater/no-subcommand consumers retain compatible JSON,
  and all existing project writes route through the one transaction engine.
- Active `AGENTS.md`, legacy skills, custom content, and unrelated WIP are never
  overwritten or deleted by refresh.
- A project-facing DevFlow change cannot pass pre-promotion or release checks
  with stale impact evidence, contract identity, migration fixtures, or packaged
  runtime; the authorized generated release passes formal Plugin Eval.

## Critical Path and Incidental Finding Budget

Critical Path:

1. lock the versioned contract and RED characterization;
2. implement pure plan/registry/config transforms;
3. implement centralized transaction/rollback and compatibility adapters;
4. integrate Skill/guidance and refresh-impact release gate;
5. complete source verification;
6. after explicit release-sync authority, generate and verify the release and
   run Plugin Eval.

One bounded RED/GREEN guard is permitted for an incidental defect only when it
blocks these contracts and fits the approved files. Anything else is classified
through the Incidental Finding Lifecycle and recorded in `TASK_LEDGER.md`.

Escalation triggers requiring replanning or a Human Gate:

- new dependency, top-level Codex command, generic plugin migration API, or
  change to a public config contract beyond the versioned path here;
- real consumer write, installed-cache mutation, release sync, publication,
  cleanup, or other external/destructive effect;
- inability to establish exact rollback or transaction isolation;
- active AGENTS merge, ambiguous user ownership, secret-bearing output, or a
  severe source/release/cache identity conflict;
- write-set expansion outside this change.

## Capability Slices

1. **Refresh contract and RED matrix:** manifest v2, immutable config target,
   supported baselines, contract digest, and failing behavioral tests.
2. **Deterministic planner:** registry validation, baseline resolution, redacted
   config transform, exact action composition, stable status/digest.
3. **Transactional executor:** full preflight, staging, promotion, verification,
   rollback, receipts, state-v2 migration, and old CLI adapters.
4. **Skill and managed-surface integration:** global-first Skill route, AGENTS
   semantic comparison, safe links/control-plane/dependency actions, docs and
   project guidance.
5. **Future-change release gate:** impact disposition, pre-promotion checks,
   immutable-history protection, packaged/runtime/cache parity.
6. **Integrated proof:** broad source, release generation, runtime verification,
   migration fixtures, strict OpenSpec, Plugin Eval, diff review, and state.

Each slice is production-complete at its interface and includes tests and
cleanup; no required behavior is deferred to another capability slice.

## Execution Ledger

All implementation and integration remain main-agent owned unless a newly
validated Agent Task Contract assigns a disjoint non-primary path.

| Slice | Owner | Write set | Evidence | Human Gate |
|---|---|---|---|---|
| Contract/RED | main | development manifest/assets and focused tests | failing then passing contract/matrix tests | approved plan |
| Planner | main | development migration/config modules and tests | deterministic snapshots and migration matrix | stop on schema expansion |
| Transaction | main | migration CLI/engine/state and tests | fault injection, rollback, compatibility | stop on destructive or unrecoverable behavior |
| Skill/guidance | main | development Skill/reference/docs/templates and root guidance | Skill validation and semantic drift tests | active AGENTS never auto-merged |
| Release gate | main | development release tooling/tests and release metadata | impact and source/release checks | authorized only after fresh source proof |
| Integration | main | OpenSpec/state/evidence, generated release, exact Git submission, named cache | broad suites, runtime audit, Plugin Eval, remote/cache readback | archive/PR/publication/consumer apply excluded |

## Continuation Policy and Human Gates

After implementation approval, execution is `auto-until-terminal`: complete the
next dependency-ready task, record evidence, and continue through ordinary
slice, review, checkpoint, and active-change verification boundaries.

The current repair Human Gate was resolved on 2026-08-07: the user approved the
systemic repair, exact direct-main submission, and targeted
`dev-flow@cy-codex-skills` refresh, and an active Goal is bound above.

Remaining independent gates:

- applying migration to any real consumer project;
- active AGENTS merge or legacy cleanup;
- dependency addition, broad plugin/Skill update, publication, archive, or PR.

If a genuine gate is reached, state records both `current_stage:
awaiting_human` and `current_change.status: awaiting_human`, plus the exact next
question. A phase label alone is not a stop.

## Generated Artifact Strategy

Read-only plans are emitted to stdout and do not create artifacts. Apply and
rollback use a plan-isolated transaction root below the existing DevFlow
migration namespace. Before staging, the task registers the root with the
Generated Artifact Lifecycle; staging is `AUTO_CLEAN` only after owner exit and
a successful terminal receipt. Apply, verification, and rollback receipts are
durable evidence and are never auto-cleaned. Recovery material is retained on
rollback failure. No raw legacy config preimage is copied into the transaction
root; tracked Git identity supplies config rollback evidence.

## Validation Commands

Focused development checks:

```bash
PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -B -m unittest \
  dev/plugins/dev-flow/tests/test_project_refresh.py \
  dev/plugins/dev-flow/tests/test_plugin_project_migration.py \
  dev/plugins/dev-flow/tests/test_legacy_workflow_config.py \
  dev/plugins/dev-flow/tests/test_project_orchestrator.py -v

PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -B -m unittest \
  dev/plugins/dev-flow/tests/test_release_sync.py \
  dev/plugins/dev-flow/tests/test_packaged_runtime.py \
  dev/plugins/dev-flow/tests/test_release_smoke.py -v

/opt/homebrew/bin/python3.12 \
  /Users/cY/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  dev/plugins/dev-flow/skills/dev-flow-refresh
```

Broad source and specification checks:

```bash
PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -B -m unittest \
  discover -s dev/plugins/dev-flow/tests -p 'test_*.py'

PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -B \
  dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo . --json

openspec validate add-versioned-devflow-project-refresh --strict
openspec validate --all --strict --no-interactive
git diff --check
```

Pre-promotion and release checks after the separate release-sync gate:

```bash
PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -B \
  dev/scripts/run_devflow_prepromotion_tests.py

PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -B \
  dev/plugins/dev-flow/scripts/sync_release_assets.py \
  --repo . --eval-target dev/plugins/dev-flow --json

PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -B \
  plugins/dev-flow/scripts/verify_release_runtime.py \
  --plugin-root plugins/dev-flow --repo-root . --json

node /Users/cY/.codex/plugins/cache/openai-curated-remote/plugin-eval/0.1.2/scripts/plugin-eval.js \
  analyze plugins/dev-flow --format markdown
```

Read-only local-reference evidence after major plugin changes:

```bash
PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -B \
  dev/scripts/codex_auto_update_plugins_skills.py --json
```

The 2026-08-07 user authorization permits release sync only after fresh source
proof, direct `origin/main` submission only after integrated review, and cache
refresh only for `dev-flow@cy-codex-skills`. No consumer-project migration,
broad updater action, archive, PR, publication, cleanup, or AGENTS merge is
authorized.

## Risks / Trade-offs

- **More engine complexity than the current link refresher** → keep the public
  interface small, steps pure, operation kinds finite, and test only through
  plans/receipts/filesystem outcomes.
- **Strict plans require replanning after legitimate managed edits** → stale
  refusal is intentional; unrelated WIP is excluded from the digest.
- **Git rollback requirement leaves some projects manual-only** → this avoids
  persisting secret-bearing preimages and still provides complete read-only
  diagnosis and exact next action.
- **Safe subsets can leave a project partly refreshed** → result remains
  incomplete, selected actions are dependency-closed, and fresh planning is
  required before completion.
- **Refresh-sensitive input lists can themselves drift** → release tests compare
  live known owners, manifest declarations, source/release bytes, revision, and
  impact evidence.
- **Compatibility adapter can prolong the old interface** → every write routes
  through one engine; the adapter is translation, not a second implementation.
- **Rollback can fail under hostile concurrent edits** → exact identity checks
  prevent overwriting new user work, retain recovery evidence, and stop further
  migration.

## Migration Plan

1. Add failing contract, registry, config, transaction, compatibility, and
   release-impact tests without changing current behavior.
2. Add manifest v2 and immutable current config target; read legacy migration
   state as v1-compatible input.
3. Implement pure planner/registry/config steps and compatibility summary.
4. Implement the centralized transaction, receipts, state-v2 update, verify,
   rollback, and failure injection.
5. Route safe project surfaces and AGENTS candidate logic through the planner;
   update the refresh Skill and maintained guidance.
6. Add pre-promotion/release/runtime impact enforcement and run broad source
   verification.
7. Stop for release-sync authorization; then generate the release, verify
   source/release parity, and run formal Plugin Eval.
8. Run the local-reference updater in read-only mode and report cache/project
   drift. At the original boundary, cache refresh and real project migration
   remained separate explicit gates; the 2026-08-07 authorization opens only
   the named DevFlow cache and leaves every consumer project closed.
9. Reopen the verified change for the four pre-submit review corrections, run
   public-seam RED/GREEN cycles, regenerate the authorized DevFlow release,
   repeat integrated review, submit the exact intended paths, and refresh only
   the named DevFlow cache with byte-level readback.

Rollback of repository implementation restores the prior manifest schema,
compatibility CLI, Skill/reference, tests, and generated release as one reviewed
change. A project migration rollback always uses its own receipt and never
depends on repository rollback.

## SubAgent Strategy

Design comparison used three validated read-only workers with zero write sets;
the main agent reviewed and promoted their conclusions here. Implementation
defaults to one main agent because migration engine, shared tests, release
metadata, and generated output overlap. A worker is allowed only for an
independently verifiable, disjoint non-primary test or documentation path under
a newly validated Agent Task Contract. The main agent always owns OpenSpec,
root control-plane files, `.planning/devflow/**`, release metadata, generated
`plugins/**`, integration, and the final claim.

## Recovery Prompts

Suggested Goal Mode objective if the user explicitly requests goal-backed
execution:

> Implement `add-versioned-devflow-project-refresh` through the verified
> generated release so every supported legacy fixture migrates transactionally,
> default and blocked paths make zero writes, all focused/broad/OpenSpec/runtime
> checks pass, and release-target Plugin Eval has no unapproved failure; stop for
> release sync, cache/project apply, destructive work, or public-scope expansion.

Continue prompt after context recovery:

> Read AGENTS.md, `.planning/devflow/STATE.md`, this change's proposal/design/
> specs/tasks, the latest checkpoint, and Git status. Preserve unrelated WIP,
> resume the first unchecked dependency-ready task, and continue automatically
> until a recorded Human Gate or verified repository completion.

## Review Checklist and Final Verification

- Verify specs, planner, CLI help/JSON, Skill examples, templates, and release
  contract use the same statuses, authorization IDs, and schema head.
- Inspect every planned write and rollback source; confirm no active AGENTS,
  legacy cleanup, arbitrary script, external install, or unlisted path can enter
  automatic apply.
- Review compatibility fields and hook/updater zero-write snapshots.
- Review fault-injection receipts and post-apply edit refusal.
- Compare source/release/runtime contract digests and immutable config targets.
- Record Plugin Eval score/findings and every incidental disposition.
- Inspect final diff and Git status; preserve the unrelated Git-transport
  evidence edit.

## Open Questions (RESOLVED)

None.
