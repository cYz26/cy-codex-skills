# Optimize DevFlow Provider Architecture

## Why

DevFlow currently hard-wires Superpowers and GSD into dependency checks,
project activation, routing guidance, state files, and tests even though
OpenSpec and DevFlow already own the canonical behavior, task, evidence, and
archive contracts. This creates false readiness failures, duplicate workflow
owners, incompatible `.planning/STATE.md` schemas, unnecessary context cost,
and no safe way to compare a lighter methodology such as
`mattpocock/skills` without replacing one hard dependency with another.

The current local evidence makes the architectural issue concrete:

- OpenAI-curated Superpowers `6.1.1` has no Codex SessionStart hook, while
  DevFlow treats every Superpowers version at or above `6.0.0` without that
  hook as broken.
- GSD `1.6.0` drift from the recorded `1.6.1` blocks the complete dependency
  report even though DevFlow scripts do not invoke GSD plan, execute, or
  verify commands for ordinary work.
- GSD and DevFlow both write `.planning/STATE.md` using incompatible schemas
  and disagree about current phase and verification state.
- The release plugin's static Plugin Eval result is `86/B` with a heavy
  `14,534` active-token estimate and no observed-usage benchmark.

The 2026-07-13 upstream and local-runtime re-audit found four residual gaps in
the otherwise complete provider architecture:

- stable core gates and generated routing ledgers still expose
  `superpowers:brainstorming`, `brainstorming`, and `writing-plans` identities;
- an installed but unselected Superpowers distribution is summarized as
  `superpowers_missing` with an install action instead of remaining advisory;
- Matt activation records a global install command even though methodology
  providers are required to be project-local;
- the compatibility baseline still targets Superpowers `6.0.3`, while the
  current curated release is `6.1.1` and the installed DevFlow cache still
  exposes legacy provider links.

## What Changes

- Replace hard-coded methodology skill names with a machine-readable provider
  capability registry and a small `resolve -> diagnose -> activate` facade.
- Make DevFlow Core plus OpenSpec independently usable without Superpowers,
  Matt skills, or GSD; retain native plan, TDD-evidence, review, completion
  proof, archive, and release gates in the core contract.
- Add orthogonal provider selection in `.dev-flow.json`:
  - methodology profile: `core`, `lean-matt`, or `strict-superpowers`;
  - roadmap provider: `none` or `gsd`.
- Keep Superpowers as an optional strict adapter rather than a core dependency.
  Select one plugin root/version/channel and derive hook requirements from the
  selected manifest instead of from semantic version alone.
- Add Matt as an optional lean adapter for `grilling`, `tdd`,
  `diagnosing-bugs`, `code-review`, `domain-modeling`, and `codebase-design`.
  Keep `ask-matt`, `to-spec`, `to-tickets`, `implement`, and `wayfinder` out of
  DevFlow's canonical control plane and automatic side-effect surface.
- Make GSD an optional roadmap provider used only for explicit roadmap,
  milestone, phase, wave-execution, persistent-UAT, or multi-session lifecycle
  needs.
- Establish path-level single-writer ownership: all DevFlow planning artifacts
  move under `.planning/devflow/**`; GSD exclusively owns root GSD roadmap
  state, codebase, and phase artifacts when selected. This also prevents
  case-insensitive path collisions. DevFlow verification no longer appends its
  own file into a GSD-owned phase directory.
- Add non-destructive legacy inference and dry-run migration. Existing skill
  links, GSD runtime files, generated artifacts, and user-modified content are
  never removed automatically.
- Make dependency checks, activation, updater output, doctor diagnostics, hook
  recommendations, and local-reference refresh provider-aware and
  capability-scoped.
- Treat `define-goal` as an on-demand goal-definition capability with explicit
  provenance and diagnostics instead of an undeclared global assumption.
- Add a repeatable provider outcome corpus and a default-switch gate. Static
  size alone cannot justify changing the default methodology profile.
- Reduce DevFlow's own repeated skill guidance and implicit invocation surface,
  then reassess the release package with Plugin Eval and observed usage.
- Make core routing ledgers and decision gates provider-neutral by using stable
  capability identifiers such as `decision-resolution` and
  `implementation-planning`.
- Keep unselected provider diagnostics advisory and action-free; never convert
  `available_unselected` into a missing-provider remediation.
- Install and resolve Matt's allowlisted primitives project-locally, and add an
  explicit dry-run-first cleanup path for verified legacy provider symlinks.
- Align strict compatibility metadata with the current Superpowers `6.1.1`
  release while retaining older source records only for verifiable legacy
  compatibility.

## Capabilities

### New Capabilities

- `devflow-provider-profiles`: Provider-neutral methodology capability
  resolution, profile-scoped diagnosis, activation, provenance, and side-effect
  policy.
- `devflow-roadmap-provider`: Optional GSD lifecycle routing, single-writer
  planning-state ownership, and non-destructive migration from legacy layouts.
- `devflow-provider-evaluation`: Reproducible quality/cost evaluation and the
  evidence gate for changing default providers.

### Modified Capabilities

- `devflow-plugin-quality`: Make the release target the primary Plugin Eval
  signal, record observed usage or a blocker, and couple static-budget cleanup
  with outcome and release evidence.

## Target State

DevFlow has one stable core control plane and optional adapters. Selecting or
omitting a methodology or roadmap provider changes only the capabilities and
dependencies associated with that selection; it does not change OpenSpec,
Task Ledger, evidence, review, archive, release, or user-authorization
ownership. New repositories default to `core + none`. Legacy repositories are
diagnosed and inferred without mutation until a user explicitly applies a
migration.

## Completion Contract

- [x] Core readiness passes with OpenSpec available and with Superpowers,
      Matt, and GSD absent.
- [x] Each selected provider fails only for capabilities that its selected
      profile requires, with a concrete remediation path.
- [x] Superpowers resolution cannot mix skills from different cache roots or
      require a hook absent from the selected manifest.
- [x] Matt control-plane and mutating orchestration skills cannot be invoked
      automatically by the lean adapter.
- [x] GSD is not installed, updated, checked, or treated as a blocker unless
      `roadmap.provider` resolves to `gsd`.
- [x] DevFlow and GSD never write the same planning, codebase, state, or
      phase-verification path.
- [x] Legacy migration is dry-run by default, idempotent, preserves user files,
      and has a documented rollback.
- [x] Characterization, provider-matrix, migration, state-ownership, release,
      and packaged-smoke tests pass.
- [x] A provider benchmark corpus and rubric exist; no default switch to
      `lean-matt` occurs without non-inferiority and efficiency evidence.
- [x] Release-target Plugin Eval, release runtime verification, OpenSpec
      validation, and local-reference dry-run evidence are recorded.
- [x] Core decision gates, generated AGENTS guidance, and task-ledger templates
      expose stable capability ids rather than provider skill names.
- [x] Unselected Superpowers and Matt content contributes no install action,
      fallback, blocking status, or misleading compatibility summary.
- [x] Lean Matt activation installs and resolves only the six allowlisted skills
      from a project-local source.
- [x] Explicit provider deactivation removes only verified managed symlinks,
      is dry-run-first, and preserves copies, directories, and unknown content.
- [x] Superpowers `6.1.1`, release assets, installed DevFlow cache, and current
      project selection are freshly verified after the hardening changes.

## Impact

- Primary source: `dev/plugins/dev-flow`.
- Release package: `plugins/dev-flow` through the existing release sync and
  runtime packaging flow.
- Configuration: additive provider fields in `.dev-flow.json`; current workflow
  mode, hook mode, and archive settings remain compatible.
- Dependencies: OpenSpec remains core; Superpowers, Matt skills, GSD, and
  `define-goal` become profile- or capability-scoped.
- State: DevFlow state path changes through a compatibility facade and explicit
  migration; GSD state semantics are not reimplemented.
- Documentation and generated guidance: provider-neutral wording replaces
  direct hard-coded dependency instructions.

No production dependency, public plugin id, automatic installer authorization,
or automatic/unauthorized destructive cleanup is introduced by this change.
The explicit provider-deactivation path remains digest-bound, symlink-only,
transactional within the process, and separately authorized.
