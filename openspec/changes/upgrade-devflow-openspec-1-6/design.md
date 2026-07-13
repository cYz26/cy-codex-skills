## Context

DevFlow currently declares OpenSpec CLI `1.5.0`, invokes
`openspec init --tools codex --profile core <repo> --force`, then expects five
generated sources under `<repo>/.codex/skills/` and promotes them into
`<repo>/.agents/skills/`. The command does not control OpenSpec's global
`delivery` setting. Official OpenSpec `v1.6.0` reads that setting from
`$XDG_CONFIG_HOME/openspec/config.json`; on this workstation it is `commands`,
so the command generated global `$CODEX_HOME/prompts/opsx-*.md` and no project
skills.

Official source and package evidence establishes these released contracts:

- npm `latest` is `1.6.0`, published 2026-07-10; tag `v1.6.0` resolves to
  commit `e1b51d111ab446b54dee2d6159ac245f0339ae52`.
- Node `>=20.19.0` is required.
- Core workflows are `propose`, `explore`, `apply`, `update`, `sync`, and
  `archive`.
- Codex skills are project-local `.codex/skills/openspec-*/SKILL.md`, while
  Codex commands are global `$CODEX_HOME/prompts/opsx-*.md`.
- Generated 1.6 skills carry `generatedBy: "1.6.0"` and
  `allowed-tools: Bash(openspec:*)`.
- `validate` resolves scaffolded changes and nested delta specs; blocked human
  archive paths now exit non-zero.
- Official `main` after `v1.6.0` contains release/website maintenance only, so
  no unreleased runtime behavior is selected.

## Skill Routing Ledger

- kind: external CLI integration and compatibility migration
- workflow mode: Full OpenSpec
- methodology profile: `core`
- roadmap provider: `none`
- capability-research: required and used; official repository, tag, npm
  package, CLI help, generated Codex artifacts, and local implementation were
  inspected
- decision-resolution: required and used; isolated generation was selected
  after reproducing global-delivery leakage
- architecture-guidance: required and used through DevFlow-native planning
- implementation-planning: required and used through `ai-native-tech-plan` and
  `change-plan`
- test-first-execution: required for implementation
- OpenSpec routing: canonical change
  `upgrade-devflow-openspec-1-6`
- roadmap routing: skipped because `roadmap_provider: none`; sequencing lives
  in this change's task ledger
- delegation: skipped because the active collaboration contract forbids
  subagent delegation for this request

## Goals / Non-Goals

**Goals:**

- Pin DevFlow to the released OpenSpec `1.6.0` contract.
- Install all six official core skills into `.agents/skills` deterministically.
- Make project activation independent of user-global OpenSpec profile,
  delivery, telemetry, and Codex home state.
- Preserve custom/non-OpenSpec project skills and fail closed on ambiguous or
  incompatible generated output.
- Keep release assets, installed cache, project configuration, diagnostics,
  and documentation consistent.

**Non-Goals:**

- Enabling OpenSpec stores or custom schemas as DevFlow defaults.
- Installing unreleased OpenSpec `main`.
- Reconfiguring the user's global OpenSpec profile/delivery or keeping global
  OPSX prompts.
- Archiving existing OpenSpec changes.
- Upgrading unrelated plugins, providers, or CLIs.

## Decisions

### 1. Pin the released package, not `latest` at execution time

Dependency provenance and apply-mode updater commands SHALL use
`@fission-ai/openspec@1.6.0`. npm registry lookup remains a diagnostic for
future drift, but activation and repair cannot silently jump to a later
release.

Rejected alternatives:

- `npm update -g @fission-ai/openspec`: non-deterministic after the next
  release.
- OpenSpec `main`: contains unreleased content and has no stable package
  contract.

### 2. Generate official skills in an isolated staging project

Activation SHALL create a temporary staging root and run the pinned installed
CLI with:

- `XDG_CONFIG_HOME` pointing inside staging, so the default `core + both`
  configuration is isolated from the user;
- `CODEX_HOME` pointing inside staging, so generated command files never touch
  the real global prompt directory;
- `OPENSPEC_TELEMETRY=0`;
- target path set to a staging project, not the real repository.

The real repository's `openspec/config.yaml` remains DevFlow/scaffold owned.
Only verified staged `.codex/skills/openspec-*` trees are copied into the real
`.agents/skills` directory. Temporary sources are always removed.

Rejected alternatives:

- Running `openspec init` in the real repository: creates legacy sources and
  inherits global delivery.
- Mutating the user's global delivery to `skills`: cross-project side effect.
- Vendoring upstream skill text into DevFlow: duplicates an external source
  and drifts on future upgrades.

### 3. Copy ephemeral generated skills and preserve custom targets

Staging sources cannot be symlink targets because staging is deleted. Official
generated skills are copied. Existing targets are refreshed only when their
frontmatter identifies them as OpenSpec-generated; custom wrappers remain in
place and produce a conflict/report instead of being overwritten.

### 4. Verify the complete 1.6 contract before writes

Generation succeeds only when all six expected skill directories exist and
each `SKILL.md` identifies OpenSpec and `generatedBy: "1.6.0"`. Missing,
additional, stale, or malformed core output blocks project skill mutation.
Dry-run reports the intended generation and target operations without invoking
OpenSpec or creating temporary/project/global files.

### 5. Add `update` without changing canonical ownership

`openspec-update-change` is added to the project skill catalog and guidance for
reconciling existing planning artifacts. DevFlow/OpenSpec repo artifacts remain
canonical, `execute-task` still owns implementation routing, and archive remains
behind DevFlow verification and explicit authorization gates.

### 6. Use OpenSpec 1.6 CLI state as the path contract

Guidance SHALL prefer `openspec status --change <id> --json` and
`openspec instructions <artifact> --change <id> --json`, including returned
`planningHome`, `changeRoot`, `artifactPaths`, and `actionContext`, instead of
assuming paths for arbitrary schemas or stores. DevFlow's own generated
`spec-driven` artifacts remain compatible.

## Completion Contract

- Dependency reports require and verify OpenSpec `1.6.0`.
- Apply-mode updating uses the pinned `1.6.0` install command.
- Project activation produces exactly six official OpenSpec 1.6 skill copies
  under `.agents/skills` and leaves real global OpenSpec/Codex config untouched.
- Dry-run performs zero writes and reports staged generation.
- Stale generated skills refresh; custom skills are preserved and reported.
- Failure, wrong version, incomplete output, and cleanup paths are covered by
  regression tests.
- Dev and packaged tests, strict OpenSpec validation, release synchronization,
  runtime verification, cache refresh, and current-project diagnostics pass.

## Capability Slices

1. **Contract and RED tests** — encode 1.6 provenance, six-workflow, updater,
   isolation, refresh, and failure expectations.
2. **Isolated project-skill generation** — implement staged invocation,
   verification, copy semantics, and cleanup.
3. **Routing and diagnostics alignment** — add update workflow and 1.6
   status/instructions guidance without global prompt dependency.
4. **Release and local rollout** — sync package, verify runtime, install CLI
   1.6.0, refresh plugin/project skills, and capture evidence.

## Migration Plan

1. Upgrade source contracts and tests on an isolated branch.
2. Run focused and full development verification.
3. Synchronize the packaged `plugins/dev-flow` release through the release
   promotion gate and rerun packaged/runtime checks.
4. Install the pinned OpenSpec CLI `1.6.0` in explicit apply mode.
5. Refresh the named DevFlow plugin cache and current project dependencies;
   the isolated generator adds/refreshed six `.agents/skills/openspec-*`
   targets.
6. Rerun dependency, migration, workflow, cache-drift, and Git checks.

Rollback:

- Reinstall `@fission-ai/openspec@1.5.0` only if the 1.6 runtime smoke fails.
- Restore generated project OpenSpec skill directories from the activation
  backup/transaction evidence; custom targets are never removed.
- Revert the DevFlow release commit if packaged verification fails. Do not
  change global OpenSpec profile/delivery during either direction.

## Risks / Trade-offs

- [Upstream adds a seventh core workflow without a version change] → exact-set
  validation fails closed and requires a reviewed DevFlow update.
- [Temporary generation succeeds but copy fails] → write generated targets
  transactionally and retain rollback evidence; cleanup runs in `finally`.
- [Node runtime is too old] → dependency diagnosis reports the `>=20.19.0`
  requirement before installation/activation.
- [Custom OpenSpec wrapper occupies a target] → preserve it and return a
  manual conflict rather than overwriting it.
- [Global prompt users expect `openspec init` side effects] → those prompts are
  optional UX outside DevFlow; users may install them separately with explicit
  global intent.

## Open Questions

None. The released source, local reproduction, and repository policy determine
the integration boundary.
