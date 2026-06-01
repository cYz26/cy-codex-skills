# Design: Claude Code Delegate Execution Contract

## Target State

`claude-code-delegate` becomes a complete-task delegation mechanism. Codex
still decides whether a task is safe and bounded, prepares scope and acceptance
criteria, invokes Claude Code through the DevFlow wrapper, and independently
verifies the result. Claude Code owns the actual delegated work inside its run:
analysis for plan mode, and implementation, local checks, documentation updates,
or Git operations for apply mode when those actions are in the delegated task.

If Claude Code returns with required delegated work unfinished, Codex does not
quietly finish the task itself. Codex verifies what happened, records the gap,
and either re-delegates a narrower follow-up or reports the block.

## Completion Contract

- The wrapper prepends a mode-specific delegation contract before the user's
  task reaches Claude Code.
- Apply-mode delegated prompts instruct Claude Code to complete all in-scope
  execution inside the run and to report files changed, commands run, tests or
  checks, Git operations when requested, and blockers.
- Plan-mode delegated prompts instruct Claude Code to complete the requested
  analysis, review, or plan without editing files.
- The skill and README state that Codex supervises and verifies; it does not
  take over execution that was delegated to Claude Code.
- Tests prove the contract is present in the actual prompt passed to Claude and
  the packaged skill includes the supervision-only boundary.

## Capability Evidence

Local evidence collected on 2026-06-01:

- `claude --help` confirms non-interactive execution with `-p/--print`,
  structured output with `--output-format json|stream-json`, permission modes
  including `plan` and `bypassPermissions`, tool allowlists, additional
  directories, and `--max-budget-usd`.
- The current wrapper already runs apply mode with `--permission-mode
  bypassPermissions`, so the missing piece is not edit capability; it is the
  delegation contract and Codex/Claude boundary.

## Design Decisions

### Decision 1: Put the contract in the wrapper, not only the skill

Skill text guides Codex, but the wrapper is the stable point every delegated
Claude Code run passes through. The wrapper will compose a short contract with
the user task so the runtime receives the boundary even when a task file is
brief.

### Decision 2: Keep Codex verification outside the Claude run

Codex remains responsible for inspecting diffs, checking Git state, rerunning
relevant tests, updating `.planning` and OpenSpec evidence, and reporting
residual risk. This preserves DevFlow gates while avoiding split execution.

### Decision 3: Treat unfinished delegated execution as a failed delegation

Codex may re-delegate a smaller follow-up or report a blocker. It should not
silently finish the delegated work itself, because that hides whether the
Claude Code process is actually useful and auditable.

## Risks

- Claude Code may still stop early or make partial changes. Mitigation: the
  contract asks for blockers and Codex independently verifies completion.
- The prepended contract increases prompt size slightly. Mitigation: keep it
  concise and avoid embedding full workflow manuals.
- Existing task files may already contain role instructions. Mitigation: the
  wrapper contract is explicit and mode-scoped, and the user's task remains
  intact after the contract.
