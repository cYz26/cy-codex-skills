# Relax compact pending stop gate

## Why

DevFlow already distinguishes continuation checkpoints from stable stopping
points, but Stop hook checks still treat any `compact_status: pending` as a
hard action gate. In Codex environments with automatic context compaction and
PostCompact recovery, that can interrupt long-running work solely because a
compact reminder exists. Compact should preserve recoverability, not become the
default reason to wait for a human.

## What Changes

- Downgrade `compact_status: pending` from a Stop-hook blocking failure to an
  advisory checkpoint warning.
- Keep hard blocking behavior for invalid compact states, missing required
  checkpoints, `failed`, and `blocked` compact results.
- Update checkpoint compact guidance to say human `/compact` prompting belongs
  at stable boundaries or when automatic recovery is unavailable.
- Add regression tests for Stop hook and aggregate DevFlow Stop behavior.

## Target State

Pending compact means: durable checkpoint exists, compact is recommended for
context hygiene, and automatic PostCompact recovery may clear it. It does not
by itself require stopping a task that can otherwise continue safely. Human
intervention is only required when the checkpoint/compact contract is invalid,
blocked, failed, or missing required recovery context.

## Skill Routing Ledger

- kind: workflow-repair
- workflow mode: Full OpenSpec because hook behavior and user-visible workflow
  compatibility change.
- capability-research: used; local DevFlow source, release package, installed
  cache, hooks, and tests were inspected.
- brainstorming: skipped; the user decision and desired boundary are explicit.
- decision-grilling: skipped; no open behavior question remains after local
  evidence scan.
- writing-plans: used; plan is persisted in this OpenSpec change.
- OpenSpec/GSD routing: OpenSpec change only; no GSD phase change.

## Capability Evidence

- authoritative_current: local DevFlow source is the authority for plugin
  behavior in this repository; current installed cache path is
  `/Users/cY/.codex-switch/homes/internal/plugins/cache/cy-codex-skills/dev-flow/0.3.0+codex.20260529145038`.
- local_scan: inspected `workflow_compact_policy.py`,
  `workflow_checkpoint_create.py`, `stop_checkpoint_policy.py`,
  `devflow_stop_hook.py`, `checkpoint-compact/SKILL.md`, compact policy
  references, and compact-focused tests in dev and release plugin roots.
- comparison: keep the existing continuation-aware checkpoint policy and
  PostCompact recovery; change only Stop/checkpoint gate severity for pending
  compact.
- assumptions: Codex may auto-compact and run PostCompact hooks; when it does
  not, repository checkpoint files remain the source of truth.
- contract: OpenSpec scenarios plus focused unit tests prove pending is
  advisory while failed/blocked/invalid states still require action.

## Scope

- Project mode: brownfield
- Change type: workflow-repair
- In scope: Stop hook compact severity, checkpoint compact skill guidance,
  focused tests, release package sync.
- Out of scope: implementing a `/compact` runner, changing Codex automatic
  compaction behavior, changing compact status names, or broad plugin
  packaging refactors.

## Completion Contract

- [x] `stop_checkpoint_policy.py` does not block solely on
  `compact_status: pending`.
- [x] `devflow_stop_hook.py` reports pending compact as advisory/acceptable.
- [x] `failed`, `blocked`, unsupported compact statuses, and missing
  checkpoint requirements still block.
- [x] `checkpoint-compact` guidance no longer instructs agents to interrupt
  long-running work only to request compact.
- [x] Dev and release tests pass for the changed compact gate behavior.

## Risks

- Agents may ignore compact recommendations too long. Mitigation: keep pending
  as an explicit warning/detail and preserve PostCompact recovery.
- Existing tests may assume pending compact is high risk. Mitigation: update
  tests to distinguish advisory Stop behavior from context-health risk signals.
