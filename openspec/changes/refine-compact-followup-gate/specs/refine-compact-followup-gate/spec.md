# Specification Delta: Refine compact follow-up gate

## ADDED Requirements

### Requirement: Continuation-aware compact gate

DevFlow SHALL only make compact a blocking follow-up when a checkpoint has a clear next action that continues work in the current thread.

#### Scenario: Continuation checkpoint blocks on compact

- GIVEN a major checkpoint boundary
- AND the next stage is a concrete continuation such as `feature_intake`
- WHEN the checkpoint is created
- THEN `compact_status` is `pending`
- AND the checkpoint instruction tells the user to run `/compact` before continuing.

#### Scenario: Stopping point does not block status update

- GIVEN a major checkpoint boundary
- AND the next stage is a stopping point such as `review_or_archive`, `done`, `complete`, `none`, or handoff-only
- WHEN the checkpoint is created
- THEN `compact_status` is `not_needed`
- AND the checkpoint instruction says compact is optional for a future thread or handoff
- AND workflow validation does not warn that compact is pending.

### Requirement: Fresh compact metadata per checkpoint

DevFlow SHALL reset compact metadata when writing a new checkpoint so prior compact results are not attached to the new checkpoint.

#### Scenario: New checkpoint after previous compact result

- GIVEN `.planning/STATE.md` has a previous `last_compact_result_file`
- WHEN a new checkpoint is created
- THEN state references the new checkpoint id and file
- AND `last_compact_result_file` is `none`
- AND `compact_source` is `checkpoint`
- AND `compact_skip_reason` and `compact_error` are `none`.
