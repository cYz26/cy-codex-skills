## Context

DevFlow's current implementation models methodology and roadmap behavior as independently selectable providers. The default checkout selects `core` and `none`, but active dependency checks, project activation, updater logic, hooks, verification, archive policy, fixtures, and release packaging still load or describe Superpowers and GSD. This makes an unselected provider part of the common runtime surface and has produced roughly twelve thousand lines of provider-specific implementation and test code.

The approved target is not a profile rename. It removes the multi-methodology and multi-roadmap abstraction. DevFlow and OpenSpec remain the control plane and canonical artifact owners. A pinned, project-local MattPocock skill pack supplies six composable engineering primitives; it does not own planning artifacts, implementation orchestration, commits, releases, or roadmaps.

Current upstream research establishes these constraints:

- The stable source is `mattpocock/skills` tag `v1.1.0`, dereferenced to commit `d574778f94cf620fcc8ce741584093bc650a61d3`; current `main` is not the release pin.
- Upstream describes these skills as small, composable additions rather than a process framework. Codex delivery currently uses the skill installer rather than a native upstream Codex plugin.
- The six already-vendored fixtures and installed local copies match the pinned release hashes. Broader user-invoked skills such as `implement`, `to-spec`, and `to-tickets` would overlap DevFlow/OpenSpec authority and are intentionally excluded.

The repository is brownfield. Public provider-selection flags and config keys exist, so their active removal is a known breaking change. The user approved that break with one compatibility boundary: obsolete configuration remains inspectable through an isolated read-only migrator, while historical/user data is preserved by default.

## Skill Routing Ledger

- `kind`: architecture-and-implementation-plan
- `workflow-mode`: Full OpenSpec
- `artifact-status`: final
- `capability-research`: used — official upstream repository, stable tag, current release commit, local hashes, installed skill copies, and current runtime call chains were inspected
- `decision-resolution`: used — the user explicitly selected complete active removal, a single Matt-native path, and a read-only legacy migration boundary
- `decision-grilling`: skipped — the approved target leaves no unresolved product decision
- `implementation-planning`: used — `ai-native-tech-plan` and the OpenSpec change flow define the completion contract and capability slices
- `architecture-guidance`: used — `codebase-design` deep-module and write-ownership guidance shaped the module boundary
- `domain-language-modeling`: skipped — this change removes workflow-provider machinery and does not introduce a business-domain language or invariant model
- `openspec-routing`: `simplify-devflow-matt-native`
- `roadmap-routing`: skipped — sequencing is owned by this OpenSpec task ledger; no roadmap provider remains
- `setup-matt-pocock-skills`: skipped — its tracker/domain-document bootstrap is unrelated to DevFlow runtime integration

## Goals / Non-Goals

**Goals:**

- Provide exactly one active workflow: DevFlow/OpenSpec control plane plus a static Matt engineering capability pack.
- Remove all Superpowers/GSD selection, installation, activation, diagnosis, fallback, readiness, hook, verification, archive, benchmark, fixture, documentation, and release behavior from active code.
- Keep Matt capabilities source-pinned, hash-checked, project-local, and activated only when a task triggers them.
- Preserve DevFlow-native planning, execution, evidence, authorization, completion, and OpenSpec ownership.
- Make subagent use bounded, contract-first, and safe for parallel work.
- Recognize obsolete provider configuration deterministically without mutating the project or importing legacy runtime code.
- Keep development and release packages aligned and prove the simplified target through focused and full validation.

**Non-Goals:**

- Do not adopt the full Matt workflow, issue tracker model, `implement` auto-commit flow, or user-invoked planning/spec skills.
- Do not retain a hidden `core`, `lean-matt`, `strict-superpowers`, `none`, or `gsd` selection mode.
- Do not implement a roadmap subsystem or a replacement for GSD phases/milestones.
- Do not delete ignored project-local legacy installations, user-authored planning/history, or old OpenSpec/Git evidence.
- Do not apply migration findings, refresh installed caches, migrate other projects, archive this change, commit, or push as part of implementation.
- Do not add a production dependency.

## Target State

The active call graph becomes:

```text
.dev-flow.json (workflow mode and hook policy only)
        |
        v
DevFlow intake / OpenSpec planning / task ledger
        |
        +--> workflow_methodology.py
        |      static capability routes
        |      pinned Matt skill readiness
        |      project-local activation plan
        |
        +--> execute-task + Agent Task Contract
        |      primary-agent orchestration
        |      bounded independent subagents
        |
        +--> DevFlow evidence / verification / archive readiness

explicit operator command only
        |
        v
inspect_legacy_workflow_config.py --> legacy_workflow_config.py
                                      read-only findings; no active import edge
```

Normal readiness, activation, updater, hook, verification, archive, and release code has no import or data dependency on the legacy inspector. The names `superpowers` and `gsd` may occur only in the isolated legacy inspector and its tests, explicitly historical source-only evidence, and the current OpenSpec change.

## Completion Contract

- Active `.dev-flow.json` and generated scaffold config contain no methodology profile, roadmap provider, provider selector, roadmap binding, or provider lock selection.
- The static capability registry exposes only the supported DevFlow/OpenSpec routes and six Matt primitives.
- Dependency diagnosis for a triggered capability reports only OpenSpec, DevFlow, the required Matt skills, and developer tooling that is independently requested; it does not enumerate Superpowers/GSD candidates.
- Project activation can plan or apply the required project-local Matt skill links without provider-selection flags and remains authorization-gated for writes.
- Hooks, state, verification, and archive readiness use OpenSpec and DevFlow evidence only.
- The legacy inspector is deterministic, read-only, secret-safe, and is not imported by active runtime modules. It reports field presence and value type only; the canonical target is a fixed safe configuration rather than a copy of untrusted current values.
- Subagent contracts reject overlapping write ownership, missing evidence, and ambiguous authority; the primary agent owns shared artifacts and integration.
- Focused tests, full development tests, packaged tests, strict OpenSpec validation, release promotion/runtime verification, workflow validation, `git diff --check`, and release-target Plugin Eval complete with no failures.

## Decisions

### 1. Replace provider selection with one deep methodology module

Create `workflow_methodology.py` as the sole active methodology boundary. It owns stable capability identifiers, the static route map, the six skill names and hashes, and readiness/activation planning helpers. Callers request a capability; they do not select or inspect a provider.

The active routes are:

| Capability | Active implementation | Canonical evidence owner |
| --- | --- | --- |
| decision resolution | `grilling` | OpenSpec decision/design artifacts |
| implementation planning | `change-plan`, `ai-native-tech-plan` | OpenSpec proposal/design/specs/tasks |
| test-first execution | `tdd` | DevFlow evidence record |
| root-cause diagnosis | `diagnosing-bugs` | DevFlow evidence and regression test |
| change review | `code-review` | DevFlow reviewer findings/disposition |
| completion proof | `verify-and-archive` | DevFlow/OpenSpec verification evidence |
| execution orchestration | `execute-task` | DevFlow task and agent contract |
| architecture guidance | `codebase-design` | OpenSpec design/specs |
| domain-language modeling | `domain-modeling`, triggered only when domain concepts, vocabulary, invariants, or bounded contexts are in scope | OpenSpec design/specs |
| goal definition | `define-goal` on demand | Codex goal plus durable Goal Contract |

The Matt pack is fixed to `grilling`, `tdd`, `diagnosing-bugs`, `code-review`, `codebase-design`, and `domain-modeling`. `ask-matt`, `setup-matt-pocock-skills`, `grill-with-docs`, `to-spec`, `to-tickets`, `triage`, `wayfinder`, `implement`, `improve-codebase-architecture`, and other upstream skills are not routed or activated. Vendored upstream bytes remain exact and hash-verifiable; two deterministic project-copy adaptations replace upstream handoffs to excluded workflow-owning skills with DevFlow/OpenSpec-owned boundaries.

Alternative rejected: make `lean-matt` the default while retaining provider profiles. This would preserve most conditional branches, stale configuration, and readiness leakage.

Alternative rejected: adopt every Matt skill. Several user-invoked skills duplicate OpenSpec, tracker, orchestration, or commit authority and would create competing sources of truth.

### 2. Separate generic side-effect policy from methodology

Move `default_plugin_root`, effect identifiers, policy loading, and authorization decisions out of `workflow_provider_registry.py` into `workflow_side_effect_policy.py`. The checked-in `provider_side_effect_policy.json` becomes `side_effect_policy.json`. This keeps the existing default-deny authorization contract while removing the false implication that side effects belong to a methodology provider.

Alternative rejected: keep the old provider registry solely for side effects. That would preserve an active module and schema whose main abstraction no longer exists.

### 3. Keep configuration minimal and fail on obsolete active keys

New scaffolds write only active workflow and hook configuration. Active readers ignore neither provider keys nor ambiguous stale values: they report a migration-required diagnostic and direct the operator to the legacy inspector. They do not infer a provider, install anything, or fall back.

The repository's checked-in `.planning/devflow/providers.lock.json` is removed. Matt source identity and hashes live in dependency provenance/methodology data, not mutable project selection state.

Alternative rejected: silently strip obsolete keys in memory. Silent acceptance would hide migration debt and make the active behavior difficult to explain.

### 4. Isolate secret-safe legacy inspection behind an explicit read-only command

Create `legacy_workflow_config.py` and a thin `inspect_legacy_workflow_config.py` CLI. The inspector recognizes old methodology/roadmap fields, provider lock entries, generated provider skill links, GSD runtime markers, and Superpowers draft locations. Its report contains recognized inputs, conflicts, preserved paths, the canonical target config, and manual next actions.

The inspector performs no writes, installations, link changes, cleanup, network access, or provider imports. It has no `--apply`, rollback, or activation mode. Any future cleanup tool is a separate explicitly approved change.

Alternative rejected: retain the existing provider migration/apply engine. Its apply, rollback, activation, source-trust, and cleanup paths would keep legacy providers operational and violate zero runtime dependency.

### 5. Define bounded subagent orchestration as a DevFlow contract

DevFlow scripts and hooks never spawn agents. The primary coding agent may delegate only when at least two work items are independent or when a scoped parallel review/research pass materially improves evidence. Before spawn, it records and validates an Agent Task Contract containing objective, read/write scope, owner, shared-file exclusions, required evidence, authority, stop conditions, and human gates.

Rules:

- one writer owns each path; shared OpenSpec, ledger, generated release, and integration files stay with the primary agent;
- workers receive bounded deliverables and cannot expand scope or perform external side effects;
- read-only exploration and review may run in parallel;
- implementation agents require disjoint write sets and tests they can run independently;
- the primary agent reviews results, resolves conflicts, runs integrated verification, and alone claims completion;
- agent failure or partial evidence leaves the ledger item open.

Alternative rejected: treat subagents as the default executor for every task. Coordination cost and shared-state races exceed the benefit for sequential or tightly coupled work.

### 6. Delete comparison machinery instead of preserving dead fixtures

Remove Superpowers gates, GSD lifecycle/binding code, provider activation/deactivation/persistence, provider benchmark runners, strict/lean comparison fixtures, provider-specific tests, and packaged equivalents after active callers are switched. Rewrite remaining tests around one target contract rather than translating profile assertions.

Historical evidence remains in Git, prior OpenSpec changes, and existing `.planning` records. Source-only historical notes may remain only when clearly excluded from runtime/release reachability. Ignored local GSD/Superpowers installations and user data are reported but not deleted.

### 7. Promote release only after development tests pass

Implementation starts in `dev/plugins/dev-flow`. Release assets are regenerated through the repository promotion path, not hand-edited. The release archive, manifest, runtime pyz, wrappers, docs, templates, and tests must agree with the development source. A forbidden-reference allowlist permits legacy names only in the isolated inspector/tests and historical evidence excluded from runtime packaging.

Promotion has two non-circular verification layers. Before promotion, the checked-in
`dev/scripts/run_devflow_prepromotion_tests.py` runner executes every development
test module except exactly `test_packaged_runtime.py` and `test_release_smoke.py`,
which require the generated release tree. The runner rejects failures and skips.
Its exact command, strict repository-wide OpenSpec validation, and `git diff
--check` are recorded in a source-hash-bound receipt. Promotion readiness also
requires the active change to be verified and every implementation/state gate to
pass. Applying release sync additionally requires a separate durable
`release_allowed` authorization; `--apply` alone grants nothing.

After authorized promotion, the ordinary full development discovery runs all
test modules, including the two release-dependent modules, followed by the
packaged suite, runtime verification, workflow validation, diff checks, and
release-target Plugin Eval. The pre-promotion runner is therefore a complete
source-only gate, not a substitute for post-promotion full verification.

## Capability Slices

1. **Contract and red tests** — add OpenSpec artifacts and characterization/target tests for static routing, obsolete-key failure, read-only inspection, subagent contracts, and forbidden active references.
2. **Methodology and policy core** — introduce the static capability module and generic side-effect module; simplify dependency diagnosis and project activation around them.
3. **Control-plane simplification** — remove provider selection from config/scaffold/hooks/updater and remove GSD state, verification, and archive behavior.
4. **Legacy isolation** — implement the explicit inspector and delete active provider migration/deactivation engines.
5. **Guidance and dead-surface removal** — update active instructions/templates/docs and delete obsolete modules, fixtures, benchmarks, and tests while preserving historical evidence.
6. **Release and proof** — run the complete source-only pre-promotion gate and
   record its source-bound receipt; after separate authorization, promote release
   assets and run full/package/OpenSpec/workflow/runtime/eval checks, review the
   diff, and record evidence.

Each slice includes its own tests and cleanup. A later slice cannot mark an earlier failed contract complete.

## Risks / Trade-offs

- **Known public compatibility break for selected provider flags/config** → Fail with an explicit legacy-inspection next action; preserve a deterministic read-only report and document the target config.
- **Large deletion can remove generic behavior accidentally** → Extract side-effect policy first, add characterization tests, switch all imports, then delete and use forbidden-reference plus import-reachability checks.
- **Historical text can be mistaken for active integration** → Keep a narrow path allowlist and exclude historical notes from release packaging and active docs.
- **Installed caches/project links can remain stale after source completion** → Report them as residual migration work and remind the user; do not mutate them without separate approval.
- **Pinned upstream skill may drift on `main`** → Verify the annotated release tag commit and exact hashes; upgrades require an explicit provenance change.
- **Subagents can race on a shared worktree** → Validate disjoint write sets and keep all shared/generated integration paths with the primary agent.
- **Removing roadmap lifecycle reduces optional functionality** → This is an intentional approved target; sequencing remains in OpenSpec tasks and DevFlow state rather than a replacement roadmap system.

## Migration Plan

1. Capture red tests and current call-chain evidence.
2. Add the new active methodology/side-effect boundaries and switch callers while old modules still exist.
3. Add the read-only legacy inspector and prove active modules do not import it.
4. Remove provider/GSD/Superpowers branches, flags, state, fixtures, and release inputs.
5. Change the repository config to the minimal target and remove its provider lock/profile marker.
6. Regenerate release assets and run the completion contract.
7. Leave installed caches, ignored project-local legacy artifacts, other projects, archive, commit, and push untouched. Report the dry-run migration command and residual risk to the user.

Rollback before commit is Git-based: restore the implementation paths and regenerated release tree from the pre-change commit. The read-only inspector has no data rollback because it never writes.

## Open Questions

None. The active-removal boundary, six-skill Matt pack, read-only legacy behavior, subagent ownership model, and no-apply/no-push/no-archive constraints were explicitly resolved before implementation.
