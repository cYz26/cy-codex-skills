## Why

Codex users sometimes want a second coding agent to execute or cross-check a well-scoped task without leaving the Codex workflow. Calling Claude Code directly from Codex is possible through the local `claude` CLI, but doing it ad hoc makes permissions, dirty worktrees, output parsing, cost limits, and verification evidence inconsistent.

## What Changes

- Add a DevFlow-supported Claude Code task delegation capability for Codex-driven workflows.
- Provide a repo-owned wrapper that builds safe non-interactive `claude -p` invocations, normalizes JSON results, and records run metadata.
- Default delegation to plan-only mode; require an explicit apply mode for workspace edits.
- Block apply-mode delegation on dirty worktrees unless the caller explicitly overrides that safety gate.
- Add a project-local skill describing when and how Codex may delegate work to Claude Code without bypassing OpenSpec, TDD, review, or verification gates.
- Document the workflow in the DevFlow README and package the same behavior in both development and release plugin copies.

## Capabilities

### New Capabilities

- `claude-code-task-delegation`: Covers controlled Codex-to-Claude Code task delegation, invocation safety, output normalization, run metadata, and workflow guardrails.

### Modified Capabilities

- None.

## Impact

- Affected code: DevFlow plugin scripts, skills, tests, and README files under `dev/plugins/dev-flow/` and `plugins/dev-flow/`.
- Affected workflow: Codex gains a standard way to ask Claude Code for plan-only assistance or explicit apply-mode task execution.
- Dependencies: No new production dependency. The local `claude` executable is an optional runtime capability detected by the wrapper.
- Compatibility: Existing DevFlow planning, OpenSpec, Superpowers, checkpoint, and verification gates remain authoritative; delegation does not replace them.
