# DevFlow

DevFlow is a Codex-first workflow router built around one active control plane:
DevFlow plus OpenSpec. It owns intake, planning gates, project-local skill
activation, execution ledgers, evidence, review, archive readiness, and release
verification.

MattPocock skills supply small engineering primitives inside that control plane;
they do not create an alternate workflow.

## Active Architecture

- OpenSpec owns behavior-level proposal, design, specs, tasks, sync, and
  archive.
- DevFlow owns routing, execution orchestration, namespaced state, evidence,
  validation, and release gates.
- `TASK_LEDGER.md` and `.planning/devflow/**` are the durable execution
  control plane.
- `.dev-flow.json` selects only workflow mode and optional low-risk/hook/
  archive settings. It has no methodology or roadmap selector.

Minimal configuration:

```json
{
  "workflow": {
    "mode": "full-openspec"
  }
}
```

Workflow mode routing selects Full OpenSpec, Lightweight Ledger, or Prototype
Mode. Full OpenSpec is mandatory for behavior, API, data, persistence,
integration, migration, permission, error handling, and compatibility changes.

## Matt Engineering Primitives

DevFlow pins `mattpocock/skills` release `v1.1.0` at commit
`d574778f94cf620fcc8ce741584093bc650a61d3`. The vendored source, license, and
every resource hash are recorded in `docs/dependency-provenance.json`.

Only six skills are allowed:

| Capability | Matt skill |
|---|---|
| decision resolution | `grilling` |
| test-first execution | `tdd` |
| root-cause diagnosis | `diagnosing-bugs` |
| change review | `code-review` |
| architecture alternatives | `codebase-design` |
| domain concepts and invariants | `domain-modeling` |

DevFlow/OpenSpec retain implementation planning, orchestration, completion
proof, and canonical writes. Skills that create a separate workflow, setup,
spec system, ticket system, or implementation queue are intentionally excluded.

Static mappings live in `scripts/workflow_methodology.py`. Only triggered
Matt skills are copied to a project's `.agents/skills/`; a global installation
does not satisfy readiness.

Inspect current requirements:

```bash
python3 scripts/check_dependencies.py --repo . \
  --capability test-first-execution --json
```

Preview project-local activation:

```bash
python3 scripts/activate_project_dependencies.py --repo . \
  --capability test-first-execution --dry-run --json
```

Repeat `--capability` for every capability required by the current task.
Unknown capabilities fail closed.

## OpenSpec 1.7 Boundary

DevFlow pins OpenSpec 1.7.0 and Node `>=20.19.0`. It generates exactly six
official Codex skills in an isolated temporary project:

- `openspec-propose`
- `openspec-explore`
- `openspec-apply-change`
- `openspec-update-change`
- `openspec-sync-specs`
- `openspec-archive-change`

The generated tree is validated before a transactional copy to
`.agents/skills/`. Activation does not modify user-global OpenSpec
configuration or global prompts.

For arbitrary OpenSpec schemas, resolve artifact paths from
`openspec status --change <id> --json` and
`openspec instructions <artifact> --change <id> --json`.

## Contract-First Control Plane

DevFlow setup and migration validate:

- `AGENTS.md`
- `ENGINEERING_POLICY.md`
- `TASK_LEDGER.md`
- `EVIDENCE_TEMPLATE.md`
- `REVIEW_CHECKLIST.md`
- `.planning/devflow/STATE.md`

A non-trivial change records Target State, Completion Contract, Capability
Slices, Execution Ledger, Acceptance Criteria, Validation Commands, risks, and
Final Verification before implementation.

## Project-Directed Implementation Readiness

When an approved project plan explicitly selects an external implementation
provider, DevFlow can promote an `ImplementationReadinessRequirement v1` and
evaluate exact provider Evidence v1 for the current consumer revision, active
semantic plan, target profile, capability set, limitations, and provider
artifact. The deterministic result is Required, NotReady, or Ready; only Ready
may produce a content-bound Receipt v1.

Approval first records `implementation_readiness.required: true` in
`.planning/devflow/STATE.md`; plans selecting no external provider keep it
`false`. This durable marker makes a missing Requirement fail closed instead of
being mistaken for a non-applicable project. Promotion also verifies
`spec_approved`, `plan_written`, the active change, and the repository-derived
semantic-plan digest.

Inspect or compose the gate with caller-confirmed ordinary authority:

```bash
python3 scripts/implementation_readiness.py inspect --repo . \
  --change-id <change> --json
python3 scripts/implementation_readiness.py check-mutation --repo . \
  --change-id <change> --ordinary-authority --json
```

Promotion, receipt writing, and named-human override recording are dry-run by
default and require explicit `--apply`. Ready proves only current evidence; it
does not grant task, dependency, credential, cost, release, cache, migration,
Git, archive, or publication authority. The gate never discovers, selects,
installs, activates, invokes, or silently substitutes a provider. Projects that
do not select an external provider receive no injected provider configuration.

## Generated Artifact Lifecycle

DevFlow supports automatic task-owned reclamation only through a Generated
Artifact Contract sealed before the bound command creates output. The
registration records repository, task, run, owner, command, retention, scope,
and before-state. Names, extensions, ignore rules, and apparent cache/build
purpose never establish ownership.

The compact runtime CLI exposes read-only `prepare`, `observe`, and `plan`
operations plus explicit `cleanup --apply`. Its deterministic routes are:

- `AUTO_CLEAN`: the owner exited and every invariant passes; exact cleanup may
  move owned paths into recoverable DevFlow quarantine under the standing
  contract, and the terminal receipt is retained evidence. Physical purge is
  a separate destructive Human Gate.
- `WAIT_OWNER`: the process or lease is active; retry later without deletion
  or a Human Gate.
- `RETAIN`: the owning workflow preserves promoted or diagnostic output.
- `HUMAN_GATE`: ownership, baseline, scope, Git state, identity, membership, or
  another safety invariant is unsafe or ambiguous.

The last route is a genuine destructive Human Gate. It is distinct from
ordinary automatic task-owned reclamation and from retained evidence.
Validators, doctors, review, and hooks only report the decision and exact next
action; they never invoke apply mode. See
`docs/generated-artifact-lifecycle.md`.

## Incidental Finding Lifecycle

DevFlow protects the current Critical Path with three dispositions:

- `CONTINUE_WITH_MINIMAL_GUARD` permits one bounded in-scope RED/GREEN guard
  needed for safe completion.
- `DEFER_AND_CONTINUE` records optional non-blocking work in the tracked
  `TASK_LEDGER.md` Incidental Finding Register and returns to the active task.
- `BLOCKED_AWAITING_HUMAN` stops mutation when harm, scope, authority,
  ownership, or a product decision requires human judgment.

Required Completion Contract behavior cannot be deferred. The register carries
evidence, mitigation, impact, and a recommended follow-up, but it does not authorize
implementation or create another execution queue. At current-task
completion, DevFlow discloses residual findings and asks the human to accept,
reject, or defer follow-up. It never starts that follow-up automatically; a
severe blocked finding must be resolved durably before work resumes.

## SubAgent Strategy

DevFlow is the policy/router layer for delegation; scripts and hooks do not
spawn subagents. An approved ledger item plus a validated Agent Task Contract
defines Goal, Scope, Constraints, Verification, Evidence, and Human Gate.

- Every worker has a unique ID and explicit write set.
- Active contracts may not contain exact or parent/child path overlap.
- Root control-plane files, OpenSpec, `.planning/devflow/**`, release metadata,
  generated `plugins/**`, integration, and final proof remain main-owned.
- Workers stop rather than expanding scope, mutating shared files, adding
  dependencies, deleting ambiguous data, or performing external effects.
- The main agent reviews worker diffs and reruns integrated validation.
- Each worker returns `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or
  `BLOCKED`, together with files, commands, tests, risks, and review needs.

Validate one or more contracts:

```bash
python3 scripts/validate_agent_task_contract.py \
  --contract .planning/agent-tasks/task-a.md \
  --contract .planning/agent-tasks/task-b.md --json
```

## Legacy Configuration Inspector

Current readers reject retired workflow-selection keys. They do not infer,
activate, install, migrate, or clean up old integrations.

Use the isolated read-only inspector:

```bash
python3 scripts/inspect_legacy_workflow_config.py --repo . --json
```

The inspector classifies old configuration and filesystem artifacts,
distinguishes generated candidates from preserved user/history paths, and
recommends the minimal target configuration. It has no mutation or network
path. See `docs/legacy-workflow-config.md`.

## Hooks and Side Effects

Hooks use `$PLUGIN_ROOT` / `%PLUGIN_ROOT%`, support `off`, `warn`, and
`block`, and preserve Codex hook schemas. Stop uses one read-only
`devflow_stop_hook.py` entrypoint.

Side-effect policy is machine-readable in `docs/side_effect_policy.json` and
default-deny. Install/update, project migration, destructive cleanup, release
promotion, archive, goal state, Git commit, and remote publication each require
their own authorization.

## Continuous Execution

Approved multi-item work defaults to `auto-until-terminal`. `execute-task`
completes one item with evidence, then `project-orchestrator` derives the next
continuation outcome and consumes another approved item, checkpoints and
continues, verifies the active change, waits at a genuine Human Gate, reports a
separately authorized external effect, or proves overall completion. Review,
verification, and checkpoint labels do not themselves require user
confirmation.

The read-only Stop hook prefers the active Full OpenSpec task list over the
fallback `TASK_LEDGER.md` and blocks premature completion while executable work
remains. This enforcement is one-shot and conversation-scoped: an already-
continued Stop turn and an explicitly ephemeral conversation with no persistent
transcript stay silent, while a first Stop in a durable conversation retains
the existing guard. The hook does not parse transcripts, execute work, or
bypass the default-deny side-effect policy.

## Goal Workflow

Use `define-goal` for user-requested goals and for long-running,
migration/release, broad-refactor, cross-context, or delegation-backed work.
A valid goal names outcome, verification evidence, scope, non-goals, success
threshold, and stop conditions. Hooks may recommend a goal but never call goal
tools.

## Plugin Project Migration

`plugin-project-migration` is the single deterministic writer for one adopted
project. Its compatibility invocation and `plan` subcommand are read-only. The
versioned interface seals exact actions and authorizations, then verifies or
rolls back the selected transaction:

```bash
python3 scripts/plugin_project_migration.py plan --repo <repo> --json
python3 scripts/plugin_project_migration.py apply --repo <repo> \
  --expect-plan <sha256:...> --allow project-refresh-apply \
  --allow workflow-config-migration --json
python3 scripts/plugin_project_migration.py verify --repo <repo> \
  --receipt <apply-receipt> --json
python3 scripts/plugin_project_migration.py rollback --repo <repo> \
  --receipt <apply-receipt> --apply --json
```

The ordinary legacy `--apply` route uses the same engine for safe declared
Skill links and missing control-plane files but never grants workflow-
configuration authority. Active `AGENTS.md`, divergent generated candidates,
custom Skill copies, legacy `.codex/skills`, historical content, unsafe config,
and post-apply edits remain protected.

## Project Refresh Impact

Every DevFlow change records `changed`, `verified-unchanged`, or
`not-applicable` Project Refresh Impact in the versioned migration contract.
The record binds inspected surfaces, project-schema decision,
refresh-contract revision, tracked-input digest, migration paths, and fixture
coverage. The pre-promotion suite rejects stale evidence, mutation of an
immutable config target, a configuration-sensitive change without a schema
advance, or tracked drift without a revision advance.

Release packaging carries the manifest, schemas, immutable config targets,
runtime/CLI, refresh Skill/reference, and supported fixture matrix as one unit.
Runtime verification proves source/release identity; the read-only updater
reports named-cache identity. Registration success alone is never cache
freshness proof.

## Archive Policy

Archive policy defaults to `confirm-on-risk`. Inspect readiness without
mutation:

```bash
python3 scripts/archive_status.py --repo . --change <change> --json
```

Archive requires complete tasks, synchronized specs, recorded verification,
explicit archive intent, and authorization. Read-only status and validation
commands are never archive mutations.

## Release Promotion

Develop managed plugin assets under `dev/plugins/dev-flow/`. Release promotion
copies allowlisted assets, builds the deterministic runtime archive, and removes
stale generated files. Direct release apply is denied; use the promotion gate
only after verification is recorded.

```bash
python3 dev/plugins/dev-flow/scripts/release_promotion_gate.py \
  --repo . --apply --json
python3 plugins/dev-flow/scripts/verify_release_runtime.py \
  --plugin-root plugins/dev-flow --json
```

Run packaged tests and Plugin Eval against `plugins/dev-flow` before claiming
release readiness. The same gate also runs project-refresh parity and fixture
checks. Installed cache refresh and consumer-project migration remain separate,
explicit actions.

## Repair Discipline

For bugs and workflow failures, identify the root cause and affected contracts,
then cover durable prevention, regression tests, docs, compatibility, and
verification. Choose systemic, minimal, staged, or deferred execution based on
risk and the approved scope, never by hiding a failing check.
