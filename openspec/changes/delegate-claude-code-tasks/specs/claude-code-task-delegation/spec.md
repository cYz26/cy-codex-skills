## ADDED Requirements

### Requirement: Claude Code delegation capability check

The system SHALL provide a DevFlow command that reports whether Claude Code delegation is locally available.

#### Scenario: Claude Code is available

- **WHEN** Codex runs the delegation command in capability-check mode and the `claude` executable is available
- **THEN** the command reports success in JSON
- **AND** the JSON includes the executable path and detected Claude Code version.

#### Scenario: Claude Code is unavailable

- **WHEN** Codex runs the delegation command in capability-check mode and the `claude` executable cannot be resolved
- **THEN** the command reports failure in JSON
- **AND** the JSON explains that Claude Code is an optional runtime capability.

### Requirement: Plan-only delegation is the default

The system SHALL default Claude Code delegation to a non-apply planning mode.

#### Scenario: Task is delegated without apply mode

- **WHEN** Codex delegates a task without requesting apply mode
- **THEN** the wrapper invokes Claude Code non-interactively with JSON output
- **AND** the wrapper selects a plan-oriented permission mode
- **AND** the normalized result records `mode` as `plan`.

### Requirement: Apply-mode delegation is explicit and guarded

The system SHALL require explicit apply mode before asking Claude Code to perform edit-capable task execution.

#### Scenario: Apply mode is requested on a dirty worktree

- **WHEN** Codex requests apply-mode delegation in a Git worktree with uncommitted changes
- **AND** Codex has not explicitly allowed dirty-worktree delegation
- **THEN** the wrapper refuses to invoke Claude Code
- **AND** the normalized result explains the dirty-worktree safety gate.

#### Scenario: Apply mode is explicitly allowed

- **WHEN** Codex requests apply-mode delegation
- **AND** the dirty-worktree safety gate passes or is explicitly overridden
- **THEN** the wrapper invokes Claude Code non-interactively with JSON output
- **AND** the wrapper selects an edit-capable permission mode
- **AND** the normalized result records `mode` as `apply`.

### Requirement: Delegation output is normalized

The system SHALL normalize Claude Code command output into a stable JSON object for Codex.

#### Scenario: Claude Code returns JSON

- **WHEN** Claude Code returns JSON output
- **THEN** the wrapper emits JSON that includes execution status, process exit code, Claude result type or subtype when present, error status when present, session id when present, cost when present, user-visible text when present, and run metadata path when logging is enabled.

#### Scenario: Claude Code returns non-JSON output

- **WHEN** Claude Code exits with non-JSON output
- **THEN** the wrapper emits a structured JSON failure
- **AND** the failure includes stderr and a bounded stdout preview for debugging.

### Requirement: Delegation run metadata is recorded safely

The system SHALL record lightweight runtime metadata for delegated Claude Code runs.

#### Scenario: Delegation completes with logging enabled

- **WHEN** a delegated run completes with logging enabled
- **THEN** the wrapper writes metadata under `.dev-flow/claude-code/runs/`
- **AND** the metadata records command mode, exit status, Claude result status, cost when present, and timestamp
- **AND** the metadata does not store the full task prompt by default.

### Requirement: Delegation remains inside DevFlow governance

The system SHALL document that Claude Code delegation does not bypass DevFlow planning, implementation, review, or verification gates.

#### Scenario: Codex uses the delegation skill

- **WHEN** Codex uses the DevFlow Claude Code delegation skill
- **THEN** the skill instructs Codex to keep OpenSpec and Superpowers gates authoritative
- **AND** the skill instructs Codex to inspect resulting diffs and run verification before claiming completion.
