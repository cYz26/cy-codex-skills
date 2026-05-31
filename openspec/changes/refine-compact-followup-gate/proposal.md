# Refine compact follow-up gate

## Why

DevFlow currently treats every major checkpoint boundary as a blocking compact gate. That is too strict when a task has reached a stable stopping point or is complete: state should be updated immediately, and the user should not have to return to the same thread only to compact and clear status. Compact should only block when there is a clear next action that will continue in the current thread.

## What Changes

- Add continuation-aware compact policy for checkpoint creation and compact recommendations.
- Keep checkpoints durable at major boundaries, but set `compact_status: pending` only when continuation is required.
- For completed/stopping-point checkpoints, set compact to `not_needed` and keep state up to date.
- Update checkpoint and compact policy guidance to describe optional compact for handoff/new-thread scenarios.

## Target State

- A checkpoint can represent either a continuation gate or a stopping point.
- Continuation gates still ask for `/compact` and use PostCompact to clear `pending`.
- Stopping-point checkpoints update state immediately and do not require PostCompact to finish the task status.
- State metadata for compact results is reset for each new checkpoint so stale compact result files do not appear to apply to a newer checkpoint.

## Scope

- Project mode: brownfield
- Change type: behavior-change

## Capability Evidence

- authoritative/current: Not an external platform capability change; this is local DevFlow workflow behavior.
- local scan: `workflow_checkpoint_create.py`, `workflow_compact_policy.py`, checkpoint/compact templates, checkpoint compact skill, pre-next-phase and stop hooks, compact recovery tests.
- comparison: Keep existing PostCompact behavior for true continuation gates; make stopping-point compact non-blocking with existing `not_needed` status.

## Non-Goals

- Do not remove checkpoint creation.
- Do not remove PostCompact recovery.
- Do not change Codex `/compact` behavior.
- Do not add new production dependencies.

## Completion Contract

- [x] Checkpoint creation distinguishes continuation-required and stopping-point checkpoints.
- [x] Compact recommendation returns no blocking compact instruction when no continuation is required.
- [x] State for a new checkpoint does not keep stale compact result metadata.
- [x] Skill and template guidance explains when compact blocks and when it is optional.
- [x] Dev/release plugin roots and installed cache are synchronized.

## Risks

- Existing callers that rely on major boundaries blocking compact must continue to work when next stage clearly requires continuation.
- Ambiguous next-stage values could be misclassified; provide an explicit CLI override.
