## MODIFIED Requirements

### Requirement: Apply-mode delegation is explicit and guarded
The system SHALL require explicit apply mode before asking Claude Code to
perform edit-capable task execution, and apply-mode delegation SHALL place the
complete bounded execution task inside the Claude Code run.

#### Scenario: Apply mode is requested on a dirty worktree
- **WHEN** Codex requests apply-mode delegation in a Git worktree with
  uncommitted changes
- **AND** Codex has not explicitly allowed dirty-worktree delegation
- **THEN** the wrapper refuses to invoke Claude Code
- **AND** the normalized result explains the dirty-worktree safety gate.

#### Scenario: Apply mode is explicitly allowed
- **WHEN** Codex requests apply-mode delegation
- **AND** the dirty-worktree safety gate passes or is explicitly overridden
- **THEN** the wrapper invokes Claude Code non-interactively with JSON output
- **AND** the wrapper selects an edit-capable permission mode
- **AND** the normalized result records `mode` as `apply`.

#### Scenario: Apply-mode task is delegated
- **WHEN** Codex delegates an apply-mode task
- **THEN** the prompt passed to Claude Code includes a contract that Claude Code
  owns all in-scope execution inside the run
- **AND** the contract tells Claude Code to report process evidence, result
  evidence, and blockers
- **AND** Codex treats its own role as independent verification rather than
  completing delegated work itself.

### Requirement: Plan-only delegation is the default
The system SHALL default Claude Code delegation to a non-apply planning mode,
and plan-mode delegation SHALL place the full requested analysis, review, or
planning task inside the Claude Code run.

#### Scenario: Task is delegated without apply mode
- **WHEN** Codex delegates a task without requesting apply mode
- **THEN** the wrapper invokes Claude Code non-interactively with JSON output
- **AND** the wrapper selects a plan-oriented permission mode
- **AND** the normalized result records `mode` as `plan`.

#### Scenario: Plan-mode task is delegated
- **WHEN** Codex delegates a plan-mode task
- **THEN** the prompt passed to Claude Code includes a contract that Claude Code
  owns the complete analysis, review, or planning deliverable
- **AND** the contract tells Claude Code not to edit files in plan mode.

### Requirement: Delegation remains inside DevFlow governance
The system SHALL document that Claude Code delegation does not bypass DevFlow
planning, implementation, review, or verification gates.

#### Scenario: Codex uses the delegation skill
- **WHEN** Codex uses the DevFlow Claude Code delegation skill
- **THEN** the skill instructs Codex to keep OpenSpec and Superpowers gates
  authoritative
- **AND** the skill instructs Codex to delegate the full bounded task to Claude
  Code rather than using Claude only as confirmation
- **AND** the skill instructs Codex to verify the resulting process evidence,
  diffs, tests, and Git state before claiming completion
- **AND** the skill instructs Codex to re-delegate or report a blocker when
  Claude Code leaves delegated execution unfinished.
