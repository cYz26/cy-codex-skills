---
name: project-orchestrator
description: Use when routing Codex setup, planning, execution, verification, or workflow repair.
---

# Project Orchestrator

Use `AGENTS.md`, DevFlow state, OpenSpec, and the active ledger as canonical.

## Route

1. Missing workflow files route to `project-setup`.
2. Classify with `feature-intake`; behavioral and compatibility changes require
   Full OpenSpec.
3. Diagnose exact capabilities and preview activation before apply.
4. External uncertainty uses `capability-research` and its Capability Evidence Gate.
5. Route plans to `change-plan`, work to `execute-task`, completion to
   `verify-and-archive`, drift to `workflow-doctor` with
   `root-cause-diagnosis`, and technical plans to `ai-native-tech-plan`.

Before product mutation run:

```bash
python3 scripts/implementation_readiness.py check-mutation --repo <repo> \
  --change-id <change> --ordinary-authority --json
```

When `implementation_readiness.required: true`, Required, NotReady, or stale
Ready evidence is technical repair. Ready is evidence, not authority. Only
concrete missing authority reaches the Human Gate recorder.

## Continuous Execution

After approval use `auto-until-terminal` and keep the enclosing
`execute -> evidence -> decide -> continue` loop:

1. Select the active Full OpenSpec tasks, or `TASK_LEDGER.md` only when no
   OpenSpec task list is active.
2. Send one dependency-ready item to `execute-task`, verify its completion
   receipt, and update canonical task and state evidence.
3. Derive `CONTINUE_NEXT_ITEM`, `CHECKPOINT_AND_CONTINUE`,
   `VERIFY_ACTIVE_CHANGE`, `AWAIT_HUMAN`, `READY_FOR_EXTERNAL_EFFECT`, or
   `COMPLETE`; continue immediately for the first three.

A phase label is not a Human Gate. Technical failure is
`FAIL_CLOSED_REPAIR`. Only a concrete authority delta may persist
`AWAIT_HUMAN` with aligned evidence and state. Recheck readiness before writes
and after resume.

For `model.*`, the exact stable identity is Standing Goal Execution Authority.
A one-use attempt receipt protects replay; it is not one-use permission.
Record actual monetary cost. Same-authority repair, refreeze, review, and retry
continue without another question; provider, model, account, credential
privilege, or acceptance-contract changes are material deltas. Optional work
uses `DEFER_AND_CONTINUE` and stays off the critical path.

A standing milestone covers only its exact reviewed external chain; archive,
PR, merge, force, and undeclared targets remain excluded.

## Generated Artifact Lifecycle

After the owning process exits, automatically apply and verify only a fresh
`AUTO_CLEAN` plan; direct CLI use still requires `cleanup --apply`. Preserve
the cleanup receipt. `WAIT_OWNER` retries, `RETAIN` preserves, and drift is
technical repair. Legacy `HUMAN_GATE` is resolver input, not permission to
write awaiting state. Hooks, doctors, and validators never clean artifacts.

## Git Transport vs GitHub Control Plane

A gh authentication failure is not Git transport failure. Authorized push
uses expected-base and fast-forward proof plus `git ls-remote`; PR, release,
and settings use `github.control_plane_write`.

For immutable-tag release prefer `github_actions`, then `github_cli`, then
`human_web`. The workflow exists in the immutable tag target, repository policy
allows it, and `GITHUB_TOKEN` has least privilege. Require publication readback
before local promotion. On failure, preserve the tag and reviewed identity.
For `github_cli`, allow one diagnosis and at most one applicable remediation
attempt. Details live in `docs/git_transport_routing.md`.

## Capability Routing

Use stable IDs from `workflow_methodology.py`: `decision-resolution`,
`implementation-planning`, `test-first-execution`, `root-cause-diagnosis`,
`change-review`, `completion-proof`, `execution-orchestration`,
`architecture-guidance`, and triggered `domain-language-modeling`. Matt skills
are bounded primitives; DevFlow and OpenSpec own canonical plans and evidence.

## Goal Gate

Route goal-backed, long-running, multi-slice, migration/release, or
cross-context work to `define-goal`. Record outcome, verification, scope,
non-goals, success threshold, and stop conditions. Scripts only recommend Goal
mode.

## SubAgent Decision Gate

Delegate when independent domains and disjoint write sets materially help.
First require a validated Agent Task Contract containing Goal, Scope,
Constraints, Verification, Evidence, and Human Gate. The main agent owns
OpenSpec, `.planning/devflow/`, shared control-plane and release files, and
final integration. Delegation uses `execution-orchestration` and reports
status, files, commands, risks, and review needs.

## Incidental Finding Lifecycle

Route through the central resolver: `CONTINUE_WITH_MINIMAL_GUARD` for a bounded
required guard, `DEFER_AND_CONTINUE` for recorded optional work, and
`BLOCKED_AWAITING_HUMAN` only for concrete material scope, authority, risk,
ownership, or product-decision deltas. Unknowns fail closed. The register does
not authorize follow-up, and Completion Contract work cannot be deferred.

## Completion

Routing names mode, capabilities, canonical artifacts, blockers, authority,
next skill, and validation. The request ends only at `COMPLETE`.
