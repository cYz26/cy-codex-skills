# DevFlow

DevFlow is the Codex workflow router for setup, planning, OpenSpec changes,
context health, verification, and plugin maintenance. Runtime code is packaged
under `scripts/`; detailed procedure stays in individual skills.

## Core Capabilities

- `project-setup`, `feature-intake`, `change-plan`, and
  `project-orchestrator` route common project work.
- `ai-native-tech-plan`, `context-health-check`, `checkpoint-compact`,
  `plugin-project-migration`, and `codex-updater` cover explicit specialist
  workflows.
- Workflow mode routing selects Full OpenSpec, Lightweight Ledger, or Prototype
  Mode before execution. Full OpenSpec remains mandatory for behavior, API,
  data, migration, integration, permission, error-handling, and compatibility
  changes; `.dev-flow.json` can enable Lightweight Ledger only for low-risk
  work.
- Hooks use `$PLUGIN_ROOT` / `%PLUGIN_ROOT%` instead of versioned installed
  cache paths and support `off`, `warn`, and `block` modes. Diagnostics
  preserve the Codex hook event schema while reporting the current stage,
  failed gates, next action, and recommended skill or command. Stop uses a
  single read-only `devflow_stop_hook.py` entrypoint.
- Agent Reach is deprecated and not recommended for DevFlow automation.

## Provider Profiles

DevFlow defaults to `core + none`: native methodology and no roadmap provider.
Optional `lean-matt`, `strict-superpowers`, and `gsd` selections implement
stable capability IDs from `docs/provider_profiles.json`; they do not replace
OpenSpec, DevFlow evidence, review, or release gates. Configure
`workflow.methodology_profile` and `workflow.roadmap_provider` in
`.dev-flow.json`.

Resolution uses explicit selector, matching lock, then unique discovery. One
source root is bound per provider. Diagnosis is read-only; activation,
migration, provider lock persistence, and dependency changes require explicit
apply. See `docs/provider-profile-migration.md` for mappings, planning ownership,
tracking states, migration, and rollback.

Pass current route requirements explicitly to diagnostics and activation:

```bash
python3 scripts/check_dependencies.py --repo . \
  --capability test-first-execution --json
python3 scripts/activate_project_dependencies.py --repo . \
  --capability test-first-execution --dry-run --json
```

Repeat `--capability` for delegated execution, review, completion proof, goal
definition, or selected roadmap lifecycle. Activation installs or links only
the selected profile and triggered conditional skills. Missing external
providers use the pinned source record; GSD's first content lock is created
only after a successful authorized pinned installer run and post-install
diagnosis. Matt's setup skill configures its alternate project workflow and is
not used as a DevFlow installer or canonical control plane.

For comparison or migration previews, both commands accept
`--methodology-profile` and `--roadmap-provider`; repeat `--provider-source
<provider-id>=<source-id>` for portable source selection. These overrides are
read-only unless activation receives both `--apply` and
`--persist-provider-selection`.

## Contract-First Control Plane

DevFlow setup and migration validate these root files:

- `AGENTS.md` routes Codex to the workflow and required skills.
- `ENGINEERING_POLICY.md` records durable engineering, dependency, testing,
  evidence, review, and release policy.
- `TASK_LEDGER.md` records the Goal Contract, task decomposition, owner,
  write set, evidence requirements, review gate, status, and execution log.
- `EVIDENCE_TEMPLATE.md` defines evidence records for TDD, verification,
  changed files, risks, and reviewer notes.
- `REVIEW_CHECKLIST.md` defines correctness, verification, scope, release, and
  archive readiness checks.

Non-trivial execution needs a Goal Contract and task ledger entry before worker
or subagent execution. Verification and archive readiness need evidence and
review results plus a knowledge-update decision: `none`, `AGENTS.md`,
`ENGINEERING_POLICY.md`, or a checked-in docs path.

## Workflow Modes

Configure lightweight routing in `.dev-flow.json`:

```json
{
  "workflow": {
    "lightweight_ledger": {
      "enabled": true
    }
  }
}
```

Lightweight ledgers must include Target State, Scope / Non-Goals, Validation
Commands, Execution Log, and Completion Claim. Prototype Mode is only for an
explicit spike, prototype, proof of concept, or demo request, and the output
must be marked non-production with cleanup or promotion criteria.

Hook modes live under `hook.mode` in `.dev-flow.json` and accept `off`, `warn`,
or `block`. Warn mode exits successfully while still emitting diagnostics; block
mode exits non-zero for blocking diagnostics; off mode emits no model-visible
diagnostic.

## Skill Routing Ledger

Design, research, architecture, product-shape, and technical-plan requests must
record a Skill Routing Ledger before the final artifact. The ledger records the
request kind, workflow mode, capability evidence, stable required capability
IDs, OpenSpec/roadmap route, and the reason for every skipped gate. If unresolved
Open Questions remain, decision resolution cannot be skipped; keep the artifact
as draft until the questions are resolved.

Decision grilling is the narrow ambiguity-resolution protocol inside decision
resolution. Use `scripts/workflow_decision_grilling.py --json` to classify
the gate when needed. The protocol is: inspect local evidence first, ask one
question at a time, provide a recommended answer, walk dependent decision
branches, and record resolved decisions in OpenSpec, the selected roadmap, or DevFlow ledger
artifacts.

## Safe Provider Cleanup

Provider deactivation removes only verified project-local skill links. Preview
the exact removal plan first and save its JSON, including `planDigest` and the
per-link rollback commands:

```bash
python3 scripts/activate_project_dependencies.py --repo <project> \
  --skip-official-installs \
  --deactivate-provider <provider-id> --dry-run --json \
  > provider-cleanup-dry-run.json
```

Apply only that reviewed plan by naming the provider, authorizing cleanup, and
passing the matching digest from the dry-run output:

```bash
python3 scripts/activate_project_dependencies.py --repo <project> \
  --skip-official-installs \
  --deactivate-provider <provider-id> \
  --authorize-provider-cleanup <provider-id> \
  --provider-cleanup-plan <planDigest> --apply --json \
  > provider-cleanup-apply.json
```

Keep both JSON reports as verification and rollback evidence. Cleanup preserves
unverified paths and never deletes global provider configuration, installed
plugin caches, or provider source caches. Disable a global plugin separately
when that independently authorized configuration change is required.

## Goal Workflow

DevFlow routes goal-backed work to `define-goal`. Apply the Goal Suitability
Gate during intake or planning, before context-health drift appears. Route to
`define-goal` when the user asks to create, set, refine, or use a goal, or when
the development task is long-running, multi-slice, migration or release
oriented, broad-refactor oriented, cross-context, subagent/delegation backed, or
otherwise likely to lose its definition of done. `define-goal` owns the active
goal check, objective quality bar, verification evidence, scope boundaries, and
stop conditions before goal creation.

Use implementation complexity and recovery cost as Goal Suitability inputs.
Score +2 for multiple OpenSpec changes, +2 for multiple capability slices, +2
for language such as "continue", "依次", "持续", "until human", or
"直到需要人工介入", +1 for data model, persistence, integration, migration,
AI/API, or platform collection surfaces, +1 for archive/release gates, and +1
for expected interruption or context compaction. Score 3 or higher requires a
Goal Mode Prompt and a pause for `/goal <objective>` or an explicit skip reason;
score 1-2 recommends a goal; score 0 does not require one.

Before a goal is created, apply the Goal Quality Gate: the candidate objective
must name the outcome, verification evidence, scope boundaries, non-goals,
success threshold, and stop conditions. Use
`scripts/validate_goal_quality.py --objective "<objective>" --json` when a
machine-readable check is useful.

After `define-goal` shapes the objective, set it in a Codex app, IDE, or CLI
composer with `/goal <objective>`. Use `/goal` to view the current goal and
`/goal pause`, `/goal resume`, or `/goal clear` to control it. If `/goal` is
not available, enable `features.goals` in Codex config or run
`codex features enable goals`.

Ordinary narrow implementation work does not require a Codex goal just because
it has multiple steps. Context-health goal statuses are a repair path after
drift is discovered, not the primary trigger for goal-backed execution. DevFlow
owns OpenSpec changes, ledgers, checkpoints, context-health reports, and
verification evidence. DevFlow does not call goal tools from hooks or scripts,
and it does not rely on a top-level CLI `goal` subcommand.

## Archive Automation

Archive policy lives under `archive.policy` in `.dev-flow.json` and defaults to
`confirm-on-risk`:

```json
{
  "archive": {
    "policy": "confirm-on-risk"
  }
}
```

Supported policies are:

- `confirm-on-risk`: archive can proceed after explicit archive intent when the
  change is ready and no risk is present; risk requires confirmation.
- `manual`: archive always requires an explicit approval gate.
- `auto-after-explicit-request`: if the user already asked to archive after
  verification, clean archive can proceed once readiness is true.

Inspect readiness without mutating files:

```bash
python3 dev/plugins/dev-flow/scripts/archive_status.py --repo . --change <change> --json
```

The pre-archive hook guards mutating archive operations such as `openspec
archive`, `openspec-archive-change`, `mv`/`git mv` into
`openspec/changes/archive`, and `rm`/`git rm` of active changes. Read-only
status, validation, grep, and file inspection commands are not archive-gated.
Under `confirm-on-risk`, risky archive mutations are blocked even when general
hook mode is `warn`; set `hook.mode` to `off` only when intentionally opting out
of DevFlow archive protection.

## Dependency Provenance

External workflow dependency records are maintained in
`dev/plugins/dev-flow/docs/dependency-provenance.json`. Dependency reports read
that catalog and include each dependency's expected version, installed version,
binary path, install command, smoke command/result, source, last verified date,
and status (`verified`, `dependency_drift`, `missing`, or `smoke_failed`).
Read-only checks report drift without running installers; mutating install and
update commands remain behind explicit apply mode.

The provenance schema records every supported provider source, selector, ref,
and verification command. Readiness checks only the selected methodology and
roadmap providers. Hook requirements come from the selected source manifest,
not a version heuristic; DevFlow never trusts provider hooks automatically.

## Routing and Capability Gates

Workflow routing is machine-readable in `docs/routing.matrix.json`.
Capability implementations are machine-readable in
`docs/provider_profiles.json`. The legacy `docs/superpowers_gate_matrix.json`
remains a compatibility shim. OpenSpec, `TASK_LEDGER.md`, and
`.planning/devflow/**` remain canonical DevFlow state and evidence; a selected
roadmap provider owns only its declared roadmap paths.

## Provider Artifact Promotion

Provider outputs, including compatibility paths under `docs/superpowers/`, are
drafts or method evidence. Promote approved content into OpenSpec, the selected
roadmap plan, `TASK_LEDGER.md`, or `.planning/devflow/verification/` before it
can satisfy archive or release readiness.

## Plugin Project Migration

`plugin-project-migration` detects drift after plugin or skill runtime updates.
The automatic path is sync-only: hooks and updater checks can remind, but they
do not edit `AGENTS.md`, `.agents/skills`, legacy `.codex/skills`, OpenSpec,
planning files, or scripts.
Reviewed apply mode refreshes declared project-local skill symlinks only when
targets are missing or already symlinks.

## Release Promotion

Develop plugins and standalone skills under `dev/`. At verified workflow
boundaries, run explicit release promotion to copy allowlisted runtime assets to
their release counterparts and then perform release validation. Stop hooks only
run read-only release-promotion checks. After fresh verification has been
recorded, use
`release_promotion_gate.py --repo . --apply --json` for the authorized DevFlow
sync. Direct `sync_release_assets.py --apply` calls are intentionally denied.
Use
`sync_release_assets.py --eval-target <path> --json` to resolve the
release-first Plugin Eval target.

The packaged runtime archive is audited by
`scripts/devflow_runtime.MANIFEST.json`, `scripts/devflow_runtime.sha256`, and
`scripts/devflow_runtime.SOURCE_COMMIT`. Verify the release runtime with:

```bash
python3 plugins/dev-flow/scripts/verify_release_runtime.py --plugin-root plugins/dev-flow --json
```

## Repair Solution Discipline

For bugs, workflow repair, and mechanism failures, start from systemic repair:
root cause, affected contracts, durable prevention, tests, docs, compatibility,
and verification. Execution may still choose systemic, minimal, staged, or
deferred repair based on current risk and validation cost.

## SubAgent Strategy

DevFlow is the policy/router layer for SubAgents. It recommends delegation for
independent domains, disjoint write sets, repeated investigation pressure,
repeated command failures, or bounded review needs. DevFlow does not spawn subagents from scripts or hooks, and Codex should not spawn them without
explicit user authorization or an approved delegated workflow.

Before delegated agent, subagent, worker, or parallel execution starts, create
and validate an Agent Task Contract. The contract records Goal, Scope,
Constraints, Verification, Evidence, and Human Gate sections so the main agent
can review the handoff before dispatch. Use
`scripts/validate_agent_task_contract.py --contract <path> --json` to check the
contract. Ordinary narrow main-agent work does not need this gate solely
because it has multiple steps.

When authorized, resolve the `execution-orchestration` capability from the
selected profile. The main agent owns OpenSpec artifacts,
`.planning/devflow/`, shared docs,
and final integration unless shared files are explicitly serialized. Each
SubAgent result reports status (`DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`), files changed or inspected, commands or tests run, residual
risks, and review needs.

## Verification

Run:

```bash
python3 -m unittest discover -s dev/plugins/dev-flow/tests
python3 -m unittest discover -s plugins/dev-flow/tests
node /Users/cY/.codex/plugins/cache/openai-curated/plugin-eval/45fe2bdd/scripts/plugin-eval.js analyze plugins/dev-flow --format markdown
```
