# Specification Delta: DevFlow compact hook recovery

## ADDED Requirements

### Requirement: Manual PostCompact recovery

DevFlow SHALL record completed compact status from Codex `PostCompact` events when a manual compact completes for a pending workflow checkpoint.

#### Scenario: Manual PostCompact records completed compact

- GIVEN `.planning/STATE.md` has `context_management.compact_status: pending`
- AND the state references an existing checkpoint file
- WHEN the `PostCompact` compact recovery hook receives `trigger: manual`
- THEN it records a completed compact result with source `cli`
- AND `.planning/STATE.md` has `compact_status: completed`
- AND `.planning/compact-results/<checkpoint-id>.json` exists.

#### Scenario: Automatic PostCompact is ignored by default

- GIVEN `.planning/STATE.md` has `context_management.compact_status: pending`
- WHEN the compact recovery hook receives `trigger: auto`
- THEN it exits successfully
- AND it does not change `.planning/STATE.md`.

#### Scenario: Non-pending state is idempotent

- GIVEN `.planning/STATE.md` has `context_management.compact_status: completed`
- WHEN the compact recovery hook receives `trigger: manual`
- THEN it exits successfully
- AND it does not write another compact result.

#### Scenario: Missing checkpoint no-ops

- GIVEN `.planning/STATE.md` has `context_management.compact_status: pending`
- AND the referenced checkpoint file does not exist
- WHEN the compact recovery hook receives `trigger: manual`
- THEN it exits successfully
- AND it does not change `.planning/STATE.md`.

### Requirement: Recovery hook packaging

DevFlow SHALL package the compact recovery hook in development and release plugin roots.

#### Scenario: Hook config includes manual PostCompact recovery

- WHEN `hooks.json` is inspected in the development or release DevFlow plugin root
- THEN `PostCompact` includes `compact_recovery_hook.py --event post_compact`
- AND that hook group has matcher `^manual$`.
