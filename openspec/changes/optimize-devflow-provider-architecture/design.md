# DevFlow Provider Architecture Design

## Skill Routing Ledger

- kind: `architecture / compatibility / workflow-repair`
- workflow mode: `Full OpenSpec`
- artifact-status: `final`
- capability-research: `used` — current upstream repositories, installed
  caches, manifests, dependency commands, local scripts, tests, state schemas,
  and release evaluation were inspected on 2026-07-10 and refreshed on
  2026-07-13 against Superpowers `v6.1.1`/main
  (`d884ae04edebef577e82ff7c4e143debd0bbec99`) and Matt `v1.1.0`
  (`d574778f94cf620fcc8ce741584093bc650a61d3`)/main
  (`391a2701dd948f94f56a39f7533f8eea9a859c87`).
- decision-resolution: `used` — retain-hard-dependencies, direct replacement,
  and provider/profile designs were compared; the approved result is core by
  default with optional lean and strict adapters.
- decision-grilling: `skipped` — the architecture defaults, compatibility
  boundary, provider roles, and evaluation gate are resolved below; no open
  decision remains.
- implementation-planning: `used` — implementation is decomposed into
  dependency-ordered, independently verifiable capability slices in
  `tasks.md`.
- architecture-guidance: `used` — the provider boundary, canonical ownership,
  project-local activation, and safe deactivation contracts are defined here.
- OpenSpec: `required and used` — dependency, routing, integration, migration,
  state, and compatibility behavior changes require proposal, design, specs,
  tasks, verification, sync, and archive gates.
- GSD: `skipped for planning execution` — this change is repairing GSD's
  optional-provider boundary and the current repository does not have a
  consistent GSD project/state model. GSD is inspected as an external roadmap
  capability, not used as the canonical planner for this change.
- Open Questions: `none`.

## Context

DevFlow currently has three responsibilities entangled in the same dependency
surface:

1. Core workflow governance: OpenSpec routing, task ledgers, evidence, review,
   archive, release, goal, checkpoint, and context-health contracts.
2. Methodology discipline supplied by Superpowers skills.
3. Long-horizon roadmap governance supplied by GSD.

The code reflects that coupling:

- `workflow_dependency_catalog.py` contains fixed Superpowers and GSD skill
  lists.
- `workflow_dependency_checks.py` always checks those lists and the GSD
  runtime/agents.
- `workflow_project_activation.py` always plans GSD installation and
  Superpowers/GSD project activation.
- `workflow_dependency_plugin_checks.py` selects Superpowers caches globally
  and infers SessionStart requirements from version.
- `workflow_state.py` and `workflow_verification.py` write GSD-owned root state
  and phase paths.
- routing skills and templates repeat provider-specific names and workflow
  rules.

The target architecture must be simpler for ordinary work without weakening
the core completion contract, while remaining compatible with repositories
that already have Superpowers links, GSD runtime files, or legacy DevFlow
planning artifacts.

## Target State

DevFlow exposes one stable core workflow and resolves optional external
providers through a small, machine-readable adapter seam.

```text
User request
    -> DevFlow workflow-mode routing (Full OpenSpec / Ledger / Prototype)
    -> provider selection
         methodology_profile: core | lean-matt | strict-superpowers
         roadmap_provider: none | gsd
    -> capability route + side-effect policy
    -> canonical OpenSpec / TASK_LEDGER / evidence / review / release gates
```

New repositories use `core + none`. Existing repositories without explicit
provider configuration stay unchanged through a read-only legacy inference and
migration recommendation. `lean-matt` is complete and usable as an opt-in
profile, but cannot become the default until the recorded outcome benchmark
passes. `strict-superpowers` remains available for teams that prefer mandatory
method gates. GSD participates only as the selected roadmap provider.

## Goals / Non-Goals

### Goals

- Make core readiness independent of Superpowers, Matt, and GSD.
- Preserve OpenSpec and DevFlow as canonical behavior/task/evidence owners.
- Preserve strict Superpowers capability without making it universal.
- Add a constrained Matt adapter without importing its tracker/spec/commit
  control plane.
- Make GSD additive and profile-scoped.
- Guarantee path-level single-writer ownership across DevFlow and GSD.
- Make selection, provenance, diagnosis, activation, updater, migration, and
  release evidence deterministic and auditable.
- Lower repeated DevFlow instruction cost and measure outcomes before changing
  defaults.

### Non-Goals

- Do not fork or rewrite Superpowers, Matt, GSD, or OpenSpec.
- Do not replace Superpowers with a Matt hard dependency.
- Do not reproduce GSD's roadmap parser or phase engine in DevFlow.
- Do not let provider skills become canonical artifact owners.
- Do not automatically install, update, trust, commit, push, publish tracker
  items, archive, release, or clean up files.
- Do not reuse `check_dependencies.py --strict` for methodology selection; it
  retains its current developer-helper meaning.
- Do not switch `lean-matt` to default as part of this change.
- Do not change the `dev-flow` plugin id or add production dependencies.

## Architecture Decisions

### 1. Use capability contracts, not external skill names, as the stable API

The stable capability IDs are:

- `decision-resolution`
- `implementation-planning`
- `test-first-execution`
- `root-cause-diagnosis`
- `change-review`
- `completion-proof`
- `execution-orchestration`
- `architecture-guidance`
- `goal-definition`
- `roadmap-lifecycle`

The complete capability contract is fixed here rather than delegated to
implementation:

| Capability | Trigger and requiredness | Core mapping | Lean mapping | Strict mapping | Canonical evidence | Side effects | Unavailable behavior |
|---|---|---|---|---|---|---|---|
| `decision-resolution` | required when goals, trade-offs, compatibility, or acceptance remain unresolved | `feature-intake` plus native one-question decision protocol | `grilling`; `grill-with-docs` only with approved doc write set | `brainstorming` | resolved proposal/design decisions; no Open Questions unless draft | `workspace.read`, conditional `draft.write` | block the unresolved decision; never fall back to another external provider |
| `implementation-planning` | required for non-trivial implementation, migration, refactor, or delegation | `change-plan` + `ai-native-tech-plan` | Core mapping | `writing-plans`, promoted into OpenSpec tasks | Target State, Completion Contract, Slices, Ledger, acceptance and commands | `draft.write`; promoter-only `canonical.write` | block planning for the selected profile; no silent provider fallback |
| `test-first-execution` | required for feature, bugfix, or risky behavior unless a reviewed exception exists | `execute-task` RED/GREEN evidence contract | `tdd` | `test-driven-development` | failing-before-passing evidence or approved exception | approved `code_test.modify` | block the triggered execution capability |
| `root-cause-diagnosis` | required for hard bug, regression, or unexpected behavior before repair | native reproduce/hypothesize/instrument/root-cause contract | `diagnosing-bugs` | `systematic-debugging` | reproduction, hypotheses, root cause, regression validator | `workspace.read`; approved `code_test.modify` | use core only when adapter declares core mapping; otherwise block |
| `change-review` | required for risky implementation, completion, release, or requested review | `REVIEW_CHECKLIST` + `verify-and-archive` | `code-review` | `requesting-code-review`; `receiving-code-review` when feedback exists | standards/spec findings and disposition | `workspace.read`, `draft.write` to review evidence | block the applicable review gate |
| `completion-proof` | required before complete/fixed/passing/archive/release claims | `verify-and-archive` + DevFlow evidence | Core mapping | `verification-before-completion` plus core evidence | fresh commands, exits, changed files, risks, reviewer notes | `workspace.read`; promoter `canonical.write` | always block completion; no provider-only fallback |
| `execution-orchestration` | required when an approved plan is delegated, parallelized, or isolated | `execute-task` + Agent Task Contract | Core mapping | `executing-plans` or `subagent-driven-development`; conditional worktree/finish skills | owner, write set, dependency edges, validation, review gate | `code_test.modify`; conditional `git.branch_worktree` | inline core fallback only when approved plan permits it; otherwise block |
| `architecture-guidance` | required when module/domain/external capability shape is material | `capability-research` + `ai-native-tech-plan` | `codebase-design`; conditional `domain-modeling` | Core mapping | design decisions and approved ADR/glossary promotion | `workspace.read`, conditional draft/canonical writes | use declared core mapping; no cross-provider fallback |
| `goal-definition` | required only for explicit goal requests or goal-suitable execution | standalone `define-goal` | same | same | objective with evidence, bounds, threshold, non-goals, stop conditions | `goal.state` after explicit request | block goal-backed execution, not ordinary core readiness |
| `roadmap-lifecycle` | required only for selected GSD or an active change-phase binding | not applicable for `none` | same overlay | same overlay | GSD PROJECT/ROADMAP/phase/verification and binding | `canonical.write`; conditional install/update | set `roadmapReady: false`; leave unbound OpenSpec available |

Skill availability proves only provider readiness; it never proves that the
capability's canonical evidence gate has been satisfied.

Alternative rejected: retain hard-coded skill lists. It preserves compatibility
but keeps provider drift spread across dependency, routing, activation, updater,
and documentation code.

### 2. Keep methodology and roadmap selection orthogonal

The canonical configuration is additive to the existing `.dev-flow.json`
workflow section:

```json
{
  "workflow": {
    "mode": "full-openspec",
    "methodology_profile": "core",
    "roadmap_provider": "none",
    "provider_selectors": {
      "superpowers": {
        "kind": "codex-plugin",
        "plugin_id": "superpowers",
        "source_channel": "openai-curated-remote",
        "version": "6.1.1"
      },
      "mattpocock-skills": {
        "kind": "git-skill-pack",
        "repository": "mattpocock/skills",
        "ref": "v1.1.0",
        "commit": "d574778f94cf620fcc8ce741584093bc650a61d3"
      },
      "gsd": {
        "kind": "project-runtime",
        "package": "@opengsd/gsd-core",
        "version": "1.6.1"
      }
    },
    "roadmap_bindings": {}
  }
}
```

The resolver accepts documented camelCase aliases for compatibility but writes
only the snake_case keys. `methodology_profile` maps to exactly one adapter:

| Profile | Adapter | Core additions |
|---|---|---|
| `core` | `devflow-native` | no external methodology dependency |
| `lean-matt` | `mattpocock-skills` | decision, TDD, diagnosis, review, architecture |
| `strict-superpowers` | `superpowers` | mandatory method gates and execution discipline |

`roadmap_provider` is `none` or `gsd` and may be combined with any methodology
profile. This avoids six duplicated composite profiles.

Selectors are portable and tracked; they never contain absolute cache paths.
The machine-local `.planning/devflow/providers.lock.json` records the resolved
root, manifest digest, version/ref, and skill hashes. Resolution precedence is
explicit selector, matching lock, then unique compatible discovery. A stale or
non-portable lock produces `stale_lock`; ambiguous discovery only reports
candidates and never binds automatically.

`check_dependencies.py` and `activate_project_dependencies.py` accept repeated
`--provider-source <provider-id>=<source-id>` dry-run overrides, where
`source-id` names a source record in `dependency-provenance.json`. Persisting an
override requires both `--apply` and `--persist-provider-selection`; otherwise
the invocation changes neither `.dev-flow.json` nor the provider lock.

### 3. Put provider behavior behind a small deep module

Add `workflow_provider_profiles.py` as the public facade with these operations:

```python
def resolve_provider_selection(repo: Path, codex_home: Path, config: dict[str, Any]) -> dict[str, Any]: ...
def diagnose_provider_selection(selection: dict[str, Any], repo: Path, codex_home: Path) -> dict[str, Any]: ...
def provider_activation_plan(selection: dict[str, Any], repo: Path, codex_home: Path) -> dict[str, Any]: ...
```

Supporting modules may handle registry validation, activation, and roadmap
state, but callers use the facade. The result includes:

- explicit/effective profile and roadmap provider;
- selection source and inference evidence;
- selected adapter root, version/ref, channel, manifest digest, and skill
  hashes;
- capability readiness and canonical evidence status as separate fields;
- `coreReady`, `methodologyReady`, and `roadmapReady`;
- conflicts, blocking reasons, dry-run commands, and migration actions.

The machine-readable source is `docs/provider_profiles.json`, with external
version/source facts remaining in `docs/dependency-provenance.json`. A separate
`docs/provider_side_effect_policy.json` keeps authorization rules auditable.

Alternative rejected: replace the string `superpowers` with `mattpocock` in
existing files. Their plan, completion, orchestration, packaging, and side
effects are not equivalent.

### 4. Keep critical quality gates native to DevFlow Core

Core continues to require:

- OpenSpec for behavior/integration/compatibility changes;
- Target State, Completion Contract, Capability Slices, and Validation Commands;
- RED/GREEN evidence or an explicit TDD-not-applicable reason;
- Task Ledger ownership/write-set/review gates for delegated work;
- fresh completion commands and evidence before archive/release;
- the existing canonical artifact promotion boundary.

External providers improve how the work is performed but do not own whether it
is complete. Therefore Matt's lack of a standalone
`verification-before-completion` equivalent does not weaken `lean-matt`.

### 5. Constrain the Matt adapter to composable primitives

The adapter pins the observed upstream release `v1.1.0`, commit
`d574778f94cf620fcc8ce741584093bc650a61d3`, and expected skill hashes in its
provider lock at `.planning/devflow/providers.lock.json`.

Allowed automatic capability mappings:

| Capability | Matt skill |
|---|---|
| `decision-resolution` | `grilling` |
| `test-first-execution` | `tdd` |
| `root-cause-diagnosis` | `diagnosing-bugs` |
| `change-review` | `code-review` |
| `architecture-guidance` | `codebase-design`, optionally `domain-modeling` |

`grill-with-docs` requires an approved ADR/glossary write set. `prototype` is
available only after DevFlow enters explicit Prototype Mode.

The adapter excludes `ask-matt`, `setup-matt-pocock-skills`, `to-spec`,
`to-tickets`, `implement`, `triage`, and `wayfinder` from implicit routing.
Explicit user invocation remains possible, but it cannot expand current task
authority and remains subject to tracker, git, dependency, and canonical-write
gates.

### 6. Resolve one Superpowers distribution, never a mixed cache

The strict adapter selects one explicit project binding or configured source.
All required skills and hooks must come from that root. Multiple plausible
roots without a binding produce `ambiguous_source`; choosing the highest
version silently is forbidden.

Hook requirements come from the selected distribution manifest/adapter. A
hookless curated `6.1.1` package is valid when its manifest declares no hook.
If the selected manifest declares an executable hook, missing trust blocks only
the strict capability that requires it.

`using-superpowers` is adapter bootstrap metadata, not a business capability.
Superpowers scratch artifacts remain drafts until promoted into OpenSpec,
DevFlow evidence, or an approved ledger.

The strict mappings are exactly those in the capability table:
`brainstorming`, `writing-plans`, `test-driven-development`,
`systematic-debugging`, `requesting-code-review`, conditional
`receiving-code-review`, `verification-before-completion`, conditional
`executing-plans` or `subagent-driven-development`, conditional
`using-git-worktrees`, and conditional `finishing-a-development-branch`.
Architecture and goal definition deliberately use their declared core/on-demand
mappings because Superpowers has no selected replacement for those capabilities.

### 7. Apply a default-deny side-effect contract to provider routing

The side-effect classes are:

- `workspace.read`
- `draft.write`
- `canonical.write`
- `code_test.modify`
- `git.branch_worktree`
- `git.commit`
- `git.push_pr`
- `tracker.read`
- `tracker.write`
- `dependency.install_update`
- `destructive.cleanup`
- `archive_release`
- `goal.state`

Authorization is complete and default-deny:

| Effect | Allowed only when | Denial behavior |
|---|---|---|
| `workspace.read` | path/system is within the user-placed task scope | omit the read and report missing scope |
| `tracker.read` | tracker is in scope and current credentials allow read-only access | do not query or broaden tracker scope |
| `draft.write` | current planning/review action declares an adapter-owned draft path and write set | keep output in chat or stop for write authority |
| `canonical.write` | DevFlow/OpenSpec promoter or approved canonical task owns the exact path | reject direct provider write and require promotion |
| `code_test.modify` | approved OpenSpec task declares the write set and validation | block edits outside the write set |
| `git.branch_worktree` | approved plan explicitly declares isolation/branch setup | continue inline only if allowed; otherwise stop |
| `git.commit` | user explicitly authorizes commit for this repository/task | leave changes uncommitted |
| `git.push_pr` | user explicitly authorizes push or PR creation | do not contact the remote |
| `tracker.write` | user explicitly authorizes issue/spec/ticket mutation | return a draft only |
| `dependency.install_update` | user explicitly authorizes the named dependency/source action | return dry-run commands only |
| `destructive.cleanup` | user approves enumerated owned files and rollback | preserve files and report cleanup candidates |
| `archive_release` | verification passes and user authorizes the named archive/release | keep ready-but-not-applied status |
| `goal.state` | user explicitly requests goal creation/control and the quality gate passes | provide a Goal Mode Prompt without changing goal state |

DevFlow can machine-enforce its own router, activation, updater, hook, and
promoter paths. It cannot guarantee interception of every explicitly invoked
third-party skill, so AGENTS, ENGINEERING_POLICY, OpenSpec tasks, and current
task authority remain the outer boundary. The product must not claim stronger
enforcement than this.

### 8. Namespace the entire DevFlow planning subtree

Target path ownership is:

| Path | Sole writer |
|---|---|
| `.planning/devflow/STATE.md` | DevFlow state facade |
| `.planning/devflow/verification/**` | DevFlow evidence recorder |
| `.planning/devflow/checkpoints/**` | DevFlow checkpoint workflow |
| `.planning/devflow/context-health/**` | DevFlow context-health workflow |
| `.planning/devflow/compact-results/**` | DevFlow compact recovery |
| `.planning/devflow/codebase/**` | DevFlow brownfield mapper |
| root `.planning/STATE.md`, `PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `config.json` | GSD, only when selected |
| `.planning/phases/**`, `milestones/**`, `todos/**`, root `.planning/codebase/**` | GSD, only when selected |

Namespacing the whole subtree prevents case-insensitive macOS collisions such
as DevFlow `ARCHITECTURE.md` versus GSD `architecture.md`, not only the known
STATE schema collision.

All DevFlow state consumers use one path/owner resolver. A root state with
`gsd_state_version` is never parsed or written by DevFlow. Core verification
writes only the DevFlow evidence subtree. GSD verification remains GSD-owned
and is additionally required only when an OpenSpec change has an active
machine-readable binding in `workflow.roadmap_bindings.<change-id>`:

```json
{
  "phase_id": "01-foundation",
  "milestone": "v1.0",
  "status": "active"
}
```

Creating or changing a binding is an approved canonical config write. The
resolver validates the OpenSpec change and GSD phase exist. A missing or renamed
phase produces `manual_review_required`. Switching roadmap provider to `none`
preserves bindings as `inactive`; it does not delete them or require GSD gates.
Archiving a bound change marks the binding `archived` after OpenSpec and GSD
verification pass. A GSD phase transition is blocked while any active binding
for that phase is unverified. Rebinding or removing an active binding requires
a durable checkpoint and explicit plan update.

Canonical ownership and Git tracking are separate. Doctor classifies required
provider paths as `tracked`, `partially_tracked`, or `local_only` and lists the
paths behind the result; it does not edit `.gitignore` automatically. Tracking
is advisory for core and for GSD with `commit_docs: false`. If selected GSD has
`commit_docs: true`, partial/local-only coverage makes `roadmapReady: false`
because its declared commit contract cannot be satisfied. Generated guidance
must not call ignored artifacts “checked in.”

### 9. Use content-driven, one-time legacy inference

Resolution order:

1. Explicit `.dev-flow.json` provider configuration.
2. Applied provider migration state/lock under
   `.planning/devflow/provider-migration/`.
3. For methodology, project-local Superpowers links with a single verifiable
   source resolve to `legacy_profile_inferred` with effective
   `strict-superpowers`; no such binding resolves to `core`. Matt is never
   inferred merely because matching standalone skills are installed.
4. Strong GSD content markers: `gsd_state_version`, GSD PROJECT/config,
   parser-valid ROADMAP, or canonical GSD phase filenames.
5. Legacy DevFlow `workflow_version` state and scaffold markers imply
   `roadmap_provider: none` unless strong GSD markers exist.
6. Conflicting markers produce `manual_review_required`.
7. No markers resolves to `core + none`.

Installed GSD runtime, skills, agents, or `.gsd-profile` alone never select GSD
because previous DevFlow activation installed those for every repository.

The compatibility resolver prefers new namespaced DevFlow state. Until the
declared sunset release `1.0.0`, it may read a legacy root `workflow_version` state only
when GSD is not selected. Any operation requiring a state write returns
`migration_required` until explicit migration creates
`.planning/devflow/STATE.md`; legacy root state is never rewritten. A root
`gsd_state_version` state is never DevFlow input. After the sunset release,
legacy root state is no longer read and diagnostics return a no-write migration
action. Compatibility uses numeric semantic-version tuple comparison against
the running DevFlow version; prerelease/build suffixes do not extend the
window. Applying migration persists explicit selection so the project is not
repeatedly re-inferred.

GSD content and lifecycle validity are obtained only through the selected
project-local runtime's read-only adapter commands: `state load`,
`roadmap validate`, `roadmap get-phase`, and `find-phase`, always with `--cwd`
and structured JSON errors. If the runtime lacks a required read-only command,
returns invalid JSON, or cannot resolve a bound phase, status is
`manual_review_required`; DevFlow does not copy the GSD parser or guess a phase.
Binding archival is an explicit DevFlow adapter action invoked only after the
OpenSpec archive and GSD verification gates report success, never inferred from
generic hook output.

### 10. Make migration dry-run-first, reversible, and non-destructive

Extend project migration with a provider/state report that records:

- explicit/inferred selection and confidence;
- evidence markers and conflicts;
- current and target owner per path;
- source hashes;
- `preserve`, `copy`, `rename`, `rewrite`, `activate`, `deactivate`,
  `manual_review`, and `cleanup_candidate` actions;
- snapshot and rollback manifest;
- separate authorization requirements for file migration and dependency
  activation.

Migration state, reports, snapshots, and rollback manifests live under
`.planning/devflow/provider-migration/**`; they never use a GSD root path.

Dry-run reports the snapshot it would create but creates no snapshot or file.
Apply requires explicit authorization, a durable checkpoint, hash-verified
snapshot, atomic writes, and no active conflicting phase/change. Failure before
commit restores original files/config without partial state. It stops on mixed
schemas or user-modified conflicts. A second apply is a no-op. It does not
remove GSD runtime/skills, Superpowers/Matt links, legacy skills,
AGENTS.md.generated, or historical planning evidence. Authorized rollback
restores config, lock, owned files, hashes, and readiness from the manifest;
post-migration hash mismatch caused by user edits produces
`manual_review_required` and never overwrites those edits.

New core setup does not create a fake ROADMAP, root STATE, or `01-foundation`
phase. GSD initialization occurs only after explicit selection and activation.

### 11. Treat `define-goal` as on-demand capability provenance

`goal-definition` maps to the standalone `define-goal` skill. It is diagnosed
only when the Goal Suitability Gate requires it or the user requests goal-backed
work. Missing goal definition does not make ordinary core readiness fail. Goal
tools remain user-controlled and DevFlow scripts stay advisory-only.

### 12. Separate architecture release from default-provider evidence

The change may ship the provider seam, GSD optionalization, and opt-in adapters
after structural tests pass. `lean-matt` becomes a default only in a later
approved change after the benchmark gate passes.

The benchmark uses these fixed task IDs: `ambiguous-decision`,
`compatibility-plan`, `known-failing-bug`, `risky-characterization-refactor`,
`external-capability-research`, `delegated-multifile-plan`,
`premature-completion-trap`, `seeded-code-review`, `checkpoint-recovery`, and
`authorization-boundary`. Compatibility, known-failing bug, risky refactor,
and premature completion are the high-risk gate. Strict and lean use separate
Plugin Eval configs and allowlisted provider fixtures whose base workspace
hashes must otherwise match. Runs use neutral prompts, fixed
model/runtime/config, randomized order, and at least three repetitions per
profile/class. They record provider/skill hashes, actual route evidence,
machine verifier results, canonical artifact compliance, critical defects,
unauthorized effects, human corrections, tokens, tool calls, elapsed time, and
blind-review scores.

Default-switch gate:

- zero unauthorized side effects or canonical artifact corruption;
- every high-risk TDD, compatibility, and premature-completion scenario passes
  three of three runs;
- at least 29 of 30 lean runs pass the machine verifier and are no more than one
  failure worse than strict;
- canonical artifact compliance is 100%;
- token telemetry coverage is at least 90%;
- paired median observed total tokens improve at least 20% versus strict, at
  least seven of ten task classes improve on paired median total tokens, and no
  class token median degrades more than 15%;
- aggregate median tool calls and elapsed time each degrade no more than 10%;
- blind-review quality is no more than 0.25/5 below strict and human correction
  count is no more than one higher.

Without those results, lean remains opt-in.

### 13. Keep provider identity outside stable core gates

Stable DevFlow contracts use capability identifiers, never provider skill
names. Decision gates expose `decision-resolution`; non-trivial planning uses
`implementation-planning`; architecture routing uses
`architecture-guidance`. The selected methodology adapter resolves those ids
to DevFlow-native, Matt, or Superpowers implementations. Templates, linters,
decision matrices, and diagnostics therefore remain valid when a provider is
unselected, disabled, upgraded, or replaced.

An unselected provider can be reported as `available_unselected`,
`absent_unselected`, or an advisory pollution risk. It contributes no install
command, next action, fallback, skill link, hook, or readiness failure.

Matt's six allowlisted primitives are installed and resolved under the current
repository's `.agents/skills/` tree. A global Matt pack is compatibility input
only and excluded global control-plane skills are advisory pollution; DevFlow
does not route them or silently use them to satisfy a project-local selection.

Provider switching may offer an explicit deactivation action. It is dry-run by
default and removes only symlinks whose skill name and provider identity are
verified against the selected provenance or an exact legacy provider target.
Directories, copied skills, unknown symlinks, user-modified content, global
plugin configuration, and provider caches are preserved and reported for
manual review. Apply requires the named cleanup authorization and records every
removed or preserved path.

Superpowers compatibility metadata targets curated `6.1.1`. Older source
records remain eligible only for deterministic legacy discovery and never
restore version-inferred hook requirements; the selected manifest remains the
hook authority.

## Data and Control Flow

1. Read workflow mode and explicit provider fields.
2. Resolve/infer provider selection without mutation.
3. Load and validate provider registry, side-effect policy, and dependency
   provenance.
4. Bind one provider source and compute capability requirements.
5. Diagnose core, methodology, roadmap, goal, and release readiness separately.
6. Route only to selected and permitted provider capabilities.
7. Require canonical evidence independently of skill availability/invocation.
8. Activation/updater/migration produce dry-run actions by default.
9. Explicit apply operates only on the selected scope and records evidence.
10. Release sync copies the dev source, packages the runtime facade/modules,
    runs packaged smoke tests, and evaluates the release target.

## Error and Status Contract

Provider status includes at least:

- `ready`
- `available_unselected`
- `missing`
- `disabled`
- `incompatible`
- `stale_link`
- `ambiguous_source`
- `unexpected_global_activation`
- `hook_missing_when_declared`
- `hook_untrusted_when_declared`
- `side_effect_contract_missing`
- `legacy_profile_inferred`
- `manual_review_required`
- `profile_unavailable`

Every blocking status identifies the affected readiness axis, capability,
selection source, evidence, and a non-mutating next action. No unselected
provider failure can reduce `coreReady`.

## Capability Evidence

- authoritative_current: Matt `v1.1.0` describes small, adaptable, composable
  skills and exposes a Claude skill-pack manifest without a Codex plugin/hook
  runtime.
- authoritative_current: Matt's main flow owns spec/ticket/implement actions,
  so only selected primitives are compatible with DevFlow's canonical control
  plane.
- authoritative_current: Superpowers distributions differ; the installed
  curated `6.1.1` manifest has an empty hook map, so version-only hook inference
  is invalid.
- authoritative_current: the Superpowers `6.1.1` Codex manifest removes the
  SessionStart hook, but its routing guidance still applies global mandatory
  skill-selection semantics; this is appropriate only for the opt-in strict
  adapter.
- authoritative_current: Matt `v1.1.0` remains substantially smaller for the
  six DevFlow-approved primitives, but its full pack also includes an alternate
  control plane; the complete pack is not a replacement for DevFlow Core. The
  2026-07-13 main snapshots contain 39 Matt skills versus 14 Superpowers
  skills. A static all-files word inventory of the six approved Matt
  primitives is 6,771 words versus 20,957 for the six closest Superpowers
  primitives. This supports a lower instruction footprint for the allowlist,
  not outcome equivalence and not global installation of the full Matt pack.
- local_scan: DevFlow hard-codes required Superpowers/GSD skills, unconditionally
  installs GSD, resolves skills across caches, and writes the same state/phase
  locations that GSD owns.
- local_scan: current GSD probes report `project_exists: false`, a spurious
  `none` phase, and missing phase verification for the DevFlow scaffold.
- local_scan: Plugin Eval of the release target reports `86/B`, zero failures,
  three static-budget warnings, and no observed usage.
- comparison: retaining hard dependencies preserves current behavior but keeps
  the coupling; direct Matt replacement loses or duplicates critical contracts;
  provider/profile isolation keeps capabilities selectable and testable.
- assumptions: external provider releases may drift after the observed refs;
  provenance checks and provider locks make drift visible rather than silently
  accepting it.

## SubAgent Strategy

Planning review uses three read-only workers under
`.planning/agent-tasks/20260710-devflow-optimization-plan-review.md`:

- provider capability/profile/side-effect review;
- GSD state ownership and migration review;
- test, benchmark, release, and rollback review.

Implementation may delegate only after an approved Agent Task Contract defines
Goal, Scope, Constraints, Verification, Evidence, Human Gate, owner, disjoint
write set, and review gate. Main-agent-owned artifacts are OpenSpec status,
provider registry schema, release sync, final evidence, and user authorization
decisions.

The 2026-07-13 hardening implementation uses
`.planning/agent-tasks/20260713-devflow-provider-hardening.md` and keeps the
provider-neutral gates, provider diagnostics/deactivation, and Matt/version
compatibility write sets disjoint.

## Migration Plan

1. Add characterization tests for current non-destructive behavior and explicit
   authorization boundaries.
2. Add provider registry, config parser, facade, and devflow-native adapter
   while legacy behavior remains inferable.
3. Add strict Superpowers and lean Matt adapters with deterministic source
   binding and side-effect exclusions.
4. Make dependency, activation, updater, routing, doctor, and templates consume
   the resolved selection.
5. Add namespaced DevFlow planning paths and read-only ownership guards.
6. Add migration dry-run, snapshots, explicit apply, idempotence, and rollback.
7. Stop default GSD installation/scaffolding and make roadmap readiness
   independent.
8. Reduce repeated skill instructions and add provider benchmark fixtures.
9. Synchronize the release package and verify runtime/source parity.
10. Run canary matrices for `core/none`, `lean-matt/none`, and legacy
    `strict-superpowers/gsd` before any real-project refresh.

## Risks / Trade-offs

- **Provider facade becomes a new abstraction layer** -> keep only three public
  operations and machine-readable adapters; do not create a generic plugin
  framework.
- **Legacy inference selects the wrong owner** -> require content markers,
  expose confidence/evidence, and stop on conflicts.
- **State migration loses user content** -> snapshot, hash, atomic write,
  explicit apply, idempotence, and rollback tests.
- **Explicit external skill invocation bypasses router policy** -> document the
  enforcement boundary and retain repo/user authorization as the outer gate.
- **Core becomes less disciplined after Superpowers is optional** -> keep
  planning, TDD evidence, completion proof, and review requirements native.
- **Benchmark compares installation rather than actual routing** -> require
  route evidence and isolated provider fixtures.
- **Static token reductions harm quality** -> quality non-inferiority gates
  precede efficiency thresholds.
- **Release/runtime metadata drifts during concurrent packaging** -> serialize
  release build/eval, verify source hashes/archive digest, and keep generated
  source-commit changes out of unrelated work.
- **Planning artifacts are local-only** -> doctor reports tracking policy and
  generated guidance describes the residual collaboration/recovery risk.

## Rollback

- Default-selection rollback keeps the provider seam and leaves `lean-matt`
  opt-in.
- GSD-optionalization rollback restores legacy roadmap inference without
  deleting new config or any GSD files.
- Full rollback switches to the compatibility resolver, restores prior code and
  release assets, reruns tests/runtime/Plugin Eval, and refreshes a previous
  DevFlow cache only after explicit user approval.
- Migration rollback restores the snapshot and verifies file hashes, explicit
  profile, and readiness axes match the pre-migration report.

## Goal Mode Prompt

```text
/goal Fully implement the approved optimize-devflow-provider-architecture Target State: make DevFlow Core plus OpenSpec independently ready; add deterministic core, lean-matt, and strict-superpowers methodology profiles plus optional GSD roadmap routing; namespace DevFlow planning artifacts; provide dry-run-first reversible migration; preserve canonical artifact and side-effect ownership; verify every capability slice with RED/GREEN evidence, provider/profile matrices, OpenSpec validation, release/runtime tests, release-target Plugin Eval, benchmark fixtures, and local-reference dry-run. Do not change the default to lean-matt without the recorded non-inferiority and efficiency thresholds. Do not install, update, clean, archive, release, commit, push, or refresh real projects without explicit approval. Stop for mixed ownership/schema, destructive migration, unresolved provider source, failed quality gates, or authority expansion.
```

## Continue Prompt

```text
Continue the approved change in @openspec/changes/optimize-devflow-provider-architecture/tasks.md. Read proposal.md, design.md, all three new capability specs, the devflow-plugin-quality delta, and the next todo Execution Ledger row first. Work on one Capability Slice at a time, record RED and GREEN commands, update checkboxes only after validation, preserve unrelated files and external installs, and stop at every explicit apply/release/local-refresh human gate.
```

## Open Questions

None. Provider defaults, selected capability mappings, state ownership,
migration behavior, authorization limits, evaluation thresholds, and rollback
conditions are fixed by this design. Any requested change to those decisions
requires updating the proposal, specs, and tasks before implementation.
