---
name: claude-code-delegate
description: Use when Codex should delegate a complete bounded planning, review, or explicitly approved execution task to Claude Code through the DevFlow wrapper, then independently verify the result.
---

# Claude Code Delegation

Use this skill when Codex should ask Claude Code to analyze, review, plan, or execute a well-scoped task while keeping DevFlow gates authoritative.

Claude Code owns the complete bounded task after Codex delegates it. Codex verifies scope, process evidence, diffs, tests, Git state, and workflow records after Claude returns.

## Position In DevFlow

This is a low-frequency, optional execution adapter for Claude Code. It is not
the core DevFlow delegation model, and it is not the general Agent Task
Contract flow. Do not route ordinary DevFlow planning, subagent strategy,
worker contracts, or task-contract discussions here unless the user explicitly
asks to run a bounded task through Claude Code.

## Rules

- Keep OpenSpec, GSD, Superpowers, and DevFlow verification gates authoritative.
- Prefer plan-only delegation first when the required output is analysis, review, or a plan.
- Use apply mode when the approved task should be executed inside Claude Code.
- Apply mode runs Claude Code with `--permission-mode bypassPermissions` by default so explicitly delegated execution can proceed without interactive permission prompts.
- Do not use Claude only as confirmation while Codex does the actual delegated work.
- If Claude leaves required delegated execution unfinished, re-delegate or report a blocker instead of silently completing it in Codex.
- Inspect any resulting diff yourself before accepting it.
- Run relevant tests and record verification before claiming completion.

## Commands

Check whether Claude Code is available:

```bash
python3 scripts/claude_code_delegate.py --repo /path/to/repo --check --json
```

Delegate a plan-only task. Claude owns the complete non-editing deliverable:

```bash
python3 scripts/claude_code_delegate.py \
  --repo /path/to/repo \
  --task "Review this OpenSpec task and propose the smallest implementation plan." \
  --json
```

Delegate an edit-capable task only after approval. Claude owns the complete in-scope execution:

```bash
python3 scripts/claude_code_delegate.py \
  --repo /path/to/repo \
  --task-file /path/to/task.md \
  --apply \
  --json
```

If apply mode is intentionally run in a dirty worktree, pass `--allow-dirty` and record why in the active task ledger.

## Workflow

1. Confirm the task is bounded and belongs to the active approved change or review request.
2. Run `--check` when Claude Code availability is unknown.
3. Use plan mode for analysis, review, and implementation suggestions.
4. Use apply mode for explicit execution tasks, including Git operations only when the task asks for them.
5. After Claude returns, read the normalized JSON result and verify the process evidence Claude reports.
6. Inspect local diffs, Git state, and relevant files yourself.
7. Run Codex-owned verification commands.
8. Record evidence in the active OpenSpec tasks and DevFlow verification files.
