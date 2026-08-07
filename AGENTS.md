# AGENTS.md

## Purpose

This repository uses a Codex-first, plan-first workflow. Durable repository
artifacts, not chat memory or external skill scratch files, are the source of
truth. Do not implement a non-trivial change from chat memory alone.

## Workflow Ownership

- OpenSpec owns behavior proposal, design, specs, tasks, verification, sync,
  and archive.
- DevFlow owns intake, routing, readiness, execution ledgers, evidence, review,
  release gates, and state below `.planning/devflow/`.
- Matt skills provide bounded engineering primitives only. They never own the
  workflow, canonical plans, task state, release, or archive.
- `TASK_LEDGER.md` owns sequencing when an OpenSpec task list is not the active
  execution ledger.

The active configuration is minimal:

```json
{"workflow":{"mode":"full-openspec"}}
```

OpenSpec 1.7 contributes exactly six project-local skills:
`openspec-propose`, `openspec-explore`, `openspec-apply-change`,
`openspec-update-change`, `openspec-sync-specs`, and
`openspec-archive-change`. DevFlow generates and verifies them in isolation
before copying them to `.agents/skills/`.

## Project Control Plane

- `AGENTS.md`: durable workflow and routing rules.
- `ENGINEERING_POLICY.md`: dependency, testing, evidence, review, and release
  policy.
- `TASK_LEDGER.md`: Goal Contract, task owner, write set, evidence, review
  gate, status, execution log, and the cross-change Incidental Finding Register.
- `EVIDENCE_TEMPLATE.md`: TDD and verification evidence format.
- `REVIEW_CHECKLIST.md`: correctness, scope, release, and archive checks.
- `.planning/devflow/STATE.md`: namespaced workflow state.

Canonical behavior and plans live in OpenSpec. Canonical execution and proof
live in the ledger, state, and verification records. External notes do not
satisfy a gate until approved content is promoted into those artifacts.

## Capability Routing

### Matt Methodology Contract

DevFlow pins `mattpocock/skills` `v1.1.0` and may copy only these six
project-local primitives when their capability is triggered:

- `grilling`: decision resolution.
- `tdd`: test-first execution.
- `diagnosing-bugs`: root-cause diagnosis.
- `code-review`: change review.
- `codebase-design`: architecture alternatives and boundaries.
- `domain-modeling`: domain concepts and invariants, only through the explicit
  `domain-language-modeling` capability.

DevFlow retains implementation planning, orchestration, completion proof, and
all canonical writes. Do not invoke Matt skills that create their own end-to-end
workflow, implementation queue, spec system, ticket system, or project setup.
Project-local copies may apply only the checked-in deterministic adaptations
that replace excluded upstream workflow handoffs with DevFlow/OpenSpec routes;
vendored upstream bytes remain immutable provenance evidence.
Missing or drifted required Matt resources fail closed; unrelated Matt skills
never affect readiness.

Stable capability mappings live in
`dev/plugins/dev-flow/scripts/workflow_methodology.py`, and workflow-mode
routing lives in `docs/routing.matrix.json`. Do not add project-selectable
methodology variants.

## Intake and Planning

- Use `feature-intake` for feature, bug, refactor, migration, tooling, or
  workflow-repair intake.
- Use `capability-research` when the solution depends on current external,
  platform, plugin, API, hook, CLI, installed-cache, or local-versus-platform
  evidence; the detailed evidence workflow lives in that skill.
- Use `grilling` when unresolved decisions remain after local evidence
  gathering. Ask one question at a time, include a recommended answer, and
  record resolved decisions in the canonical artifact.
- Use `ai-native-tech-plan` for the technical execution contract.
- Use `change-plan` and `openspec-propose` for proposal, design, specs, and
  tasks. Use `openspec-update-change` for planning-only revisions.
- Use `openspec-apply-change` only after the change is approved.

For research, design, architecture, product shape, or a non-trivial plan,
record a Skill Routing Ledger with required capabilities and these fields:

- `artifact-status: draft/final`
- `capability-research: required/used/skipped`
- `decision-resolution: required/used/skipped`
- `decision-grilling: required/used/skipped`
- `implementation-planning: required/used/skipped`
- `architecture-guidance: required/used/skipped`
- `domain-language-modeling: required/used/skipped`
- `openspec-routing: required/used/skipped`

Record a concrete reason for each skip. Open Questions keep the artifact draft
and make decision resolution required.

Do not start implementation until scope, solution, validation, risks, and the
next ledger item are durable.

## Project-Directed Implementation Readiness

Project-owned engineering direction is planning input only. When an approved
active plan explicitly selects an external implementation provider, promote an
`ImplementationReadinessRequirement v1` bound to that provider, the consumer
identity/revision, active change and semantic plan, target profile, exact
capabilities, accepted evidence, required limitations, and named-human-only
fallback policy. Do not infer a selection from chat, repository presence, or a
producer's internal files.

The approved plan records this applicability durably as
`implementation_readiness.required: true` in `.planning/devflow/STATE.md`;
projects whose active plan selects no external provider retain `false`.
Requirement promotion verifies that marker, `spec_approved`, `plan_written`,
the active change, and the repository-derived semantic plan before writing.

Read-only research and draft planning remain allowed while readiness is
Required or NotReady. Execution-ready status, product edits, mutating
delegation, automatic continuation into writes, passing verification, release
readiness, and archive readiness require a current Ready receipt plus every
ordinary Goal, task, dependency, authority, and Human Gate. Ready is evidence,
not authorization. Doctors and hooks report the stable issue and next action;
they never discover, select, install, activate, invoke, or silently replace a
provider.

## Goal Workflow

Use `define-goal` when the user asks for goal-backed work or when the task is
long-running, migration/release oriented, broad, cross-context, delegation
backed, or likely to lose its definition of done. The Goal Contract names
outcome, verification evidence, scope, non-goals, success threshold, and stop
conditions. DevFlow scripts may recommend goal mode but never call goal tools
automatically.

## AI Coding Planning Rules

Unless the user explicitly requests a prototype or partial target, plan and
implement the complete Target State. Do not use MVP, Future Work, calendar
estimates, staffing, or delivery phases to defer required behavior.

A technical plan contains:

1. Target State and Scope / Non-Goals.
2. Architecture Decisions.
3. Completion Contract.
4. Dependency-ordered, production-complete Capability Slices.
5. Execution Ledger with owner, write set, evidence, and human gate.
6. Acceptance Criteria and exact Validation Commands.
7. Risks, rollback, review, and Final Verification.

## Incidental Finding Lifecycle

Classify every problem discovered outside the active task's required behavior
before expanding work:

- `CONTINUE_WITH_MINIMAL_GUARD`: the finding blocks safe completion, and one
  bounded RED/GREEN guard fits the approved contract and write set.
- `DEFER_AND_CONTINUE`: the finding does not block the Completion Contract and
  the current mitigation keeps the critical path safe.
- `BLOCKED_AWAITING_HUMAN`: continuing would expand material scope or authority,
  risk severe harm, or choose an unresolved product or ownership decision.

Apply fail-closed precedence: `BLOCKED_AWAITING_HUMAN` wins over a possible
guard or deferral. The required Completion Contract behavior and failing
acceptance criteria may not be deferred. Record every deferred or blocked
finding in the tracked `TASK_LEDGER.md` Incidental Finding Register; chat and
`.planning/devflow/` alone are not durable cross-machine records. The register
does not authorize follow-up work.

For a severe or ambiguous finding, stop mutation after safe read-only diagnosis,
record evidence and options, and ask the human one concrete decision. Promote
that decision into OpenSpec or the active ledger before resuming. A truthful
completion may disclose non-blocking deferred findings and ask the human to
accept, reject, or defer the recommended follow-up; it may not automatically
start that follow-up. An unresolved `BLOCKED_AWAITING_HUMAN` finding blocks
continuation, completion, verification claims, and archive readiness.

## Workflow Mode Routing

- `Full OpenSpec` is mandatory for behavior, API, data model, persistence,
  integration, migration, permission, error handling, and compatibility work.
- `Lightweight Ledger` is limited to configured docs-only, test-only, internal
  maintenance, or low-risk fixes; it still requires Target State, Scope /
  Non-Goals, Validation Commands, Execution Log, and Completion Claim.
- `Prototype Mode` requires an explicit prototype, spike, proof-of-concept, or
  demo request and records non-production status plus cleanup or promotion
  criteria.

Project mode: brownfield

For brownfield work, inspect architecture, conventions, tests, and specs first;
prefer minimal compatible changes and add characterization tests before risky
edits. For greenfield work, establish Target State, Completion Contract,
OpenSpec, and test/lint/build baselines before implementation.

## Execution and Bounded Subagents

Use `execute-task` for one approved ledger item at a time. Prefer test-first
execution for business logic, bugs, refactors, and risky behavior.

Delegate only when work is independently verifiable and materially benefits
from parallelism. Before delegation, validate an Agent Task Contract containing
Goal, Scope, Constraints, Verification, Evidence, and Human Gate.

- Give every worker a unique ID and an explicit, disjoint write set.
- Reject exact and parent/child path overlap across all active contracts.
- The main agent owns OpenSpec, root control-plane files,
  `.planning/devflow/**`, release metadata, generated `plugins/**`, integration,
  and the final completion claim.
- Workers stop on scope expansion, shared-file needs, dependency changes,
  ambiguous deletion, failing production contracts, or new external effects.
- The main agent reviews every worker diff and reruns integrated validation.

Do not expand scope, add a dependency, or change a public contract without
updating the canonical plan and approval boundary.

## Continuous Execution

After implementation is approved, use `auto-until-terminal`. `execute-task`
completes one dependency-ready item and returns evidence; `project-orchestrator`
then derives `CONTINUE_NEXT_ITEM`, `CHECKPOINT_AND_CONTINUE`,
`VERIFY_ACTIVE_CHANGE`, `AWAIT_HUMAN`, `READY_FOR_EXTERNAL_EFFECT`, or
`COMPLETE`. For the first three outcomes, continue immediately through the next
approved action. Item, slice, review, verification, checkpoint, and active-
change boundaries do not end the user request.

Prefer the active Full OpenSpec task list as the execution source and use
`TASK_LEDGER.md` only when it is the configured active ledger. Do not merge the
two or create another queue. A phase label is not a Human Gate.

Stop only for unresolved product or ownership decisions, material scope/write-
set/public-contract expansion, dependencies or migrations, destructive or
external effects, severe or unknown risk, explicit per-stage confirmation, or
another missing authority. Before asking, record the concrete gate and next
question durably; use both `current_stage: awaiting_human` and
`current_change.status: awaiting_human` so read-only Stop policy can distinguish
a real gate from premature completion. Promote the answer into OpenSpec or the
active ledger, restore executable state, and resume automatically.

Checkpoint/compact is advisory and recoverable. Active-change verification is
not overall completion when approved work remains. Release, archive, commit,
push, PR, install/update, migration apply, and destructive work remain separate
authorization boundaries and are never implied by automatic continuation.

## Git Transport vs GitHub Control Plane

A gh authentication failure is not Git transport failure. For an explicitly
authorized push, use `git_transport_preflight.py` based on `git ls-remote`.
Native push uses `git.push`; PR/release/settings use
`github.control_plane_write`. For deterministic tag-bound releases, prefer
validated repository GitHub Actions over local gh authentication, require
publication readback before local promotion, and preserve the tag if
publication fails. Allow one diagnosis and at most one applicable remediation
attempt for a direct GitHub control-plane fallback, then stop that path without
blocking native Git. `git.push_pr` is compatibility-only.

## Verification and Archive

Before claiming completion, run fresh focused and broad checks, update the
Execution Ledger and `.planning/devflow/STATE.md`, record evidence, inspect the
diff, and report residual risks. Archive requires synchronized specs, complete
tasks, passing verification, explicit intent, and the archive authorization
gate.

## Plugin Eval Gate

When creating or updating Codex plugins or skills, resolve the release
counterpart and run `plugin-eval analyze <target> --format markdown` against
that release target. Development-path analysis is diagnostic only when a
release package exists. Default to fixing or optimizing failures and actionable
warnings. Verification evidence must record the score, findings, and
optimization decisions. Deferral is an exception and records reason, residual
risk and follow-up path.

## Local Reference Update Reminder

After major plugin or skill changes, update local Codex references and start
with the read-only check:

```bash
python3 dev/scripts/codex_auto_update_plugins_skills.py --json
```

Report source/release drift, installed plugin cache freshness, and project-local
skill links drift. Applying cache refresh or project migration requires explicit
authorization.

## Project Refresh Impact Gate

Every DevFlow change must classify its effect on established projects as
`changed`, `verified-unchanged`, or `not-applicable`. Inspect the declared
refresh-sensitive configuration, readers, migration registry/state, AGENTS
guidance, control-plane templates, project-local Skill inventory, dependency
layout, fixtures, and refresh Skill contract. Record concrete evidence in the
versioned refresh contract. A tracked-byte change requires a refresh-contract
revision; a configuration-sensitive change requires a new immutable config
target, project-schema advance, unique migration step, and supported fixture.
Pre-promotion and release verification fail closed on stale evidence, missing
coverage, immutable-target mutation, or source/release/cache identity drift.

## DevFlow Refresh Workflow

Use `dev-flow-refresh` after a DevFlow upgrade or when an established project
needs its DevFlow workflow refreshed. Refresh the named plugin first with
`codex plugin add dev-flow@cy-codex-skills --json`, then run project diagnostics
before any project write. Use the existing `plugin_project_migration.py`
`plan`/`apply`/`verify`/`rollback` interface as the only project writer. Treat
`AGENTS.md.generated` as a merge-only candidate and merge only durable workflow
rules. Workflow-configuration migration, legacy skill cleanup, and consumer-
project apply require their own authorization.

## Legacy Configuration

Current runtime readers reject retired selection keys and direct the operator
to the isolated, read-only inspector:

```bash
python3 scripts/inspect_legacy_workflow_config.py --repo . --json
```

The inspector may classify old files and recommend a target configuration. It
has no apply, cleanup, install, activation, rollback, or network path. Preserve
ambiguous, user-authored, and historical data until a separately authorized
migration lists exact files and rollback evidence.

## Repair Solution Discipline

For a repair, after investigation, present the systemic and thorough solution
first: root cause, affected contracts, prevention, tests, docs, compatibility,
and verification. Then compare systemic repair, a minimal fix, staged repair,
or deferral against the current scope and risk.

## Context Checkpoint and Compaction

At setup, design, OpenSpec planning, verification, and archive boundaries,
persist state, changed files, command results, risks, and next action.
Repository artifacts remain authoritative after compaction.

## Forbidden Without Explicit Approval

- destructive cleanup or broad architecture rewrite;
- public API or persistence-schema changes;
- production dependencies;
- bypassing failed tests;
- project migration apply, release sync apply, archive, commit, push, or PR
  creation.
