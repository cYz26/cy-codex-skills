---
name: claude-code-delegate
description: Use when Codex should delegate a bounded planning, review, or explicitly approved execution task to Claude Code through the DevFlow wrapper.
---

# Claude Code Delegation

Use this skill when Codex should ask Claude Code to analyze, review, plan, or execute a well-scoped task while keeping DevFlow gates authoritative.

## Rules

- Keep OpenSpec, GSD, Superpowers, and DevFlow verification gates authoritative.
- Prefer plan-only delegation first.
- Use apply mode only when the active plan explicitly allows Claude Code to edit files.
- Apply mode runs Claude Code with `--permission-mode bypassPermissions` by default so explicitly delegated execution can proceed without interactive permission prompts.
- Inspect any resulting diff yourself before accepting it.
- Run relevant tests and record verification before claiming completion.

## Commands

Check whether Claude Code is available:

```bash
python3 scripts/claude_code_delegate.py --repo /path/to/repo --check --json
```

Delegate a plan-only task:

```bash
python3 scripts/claude_code_delegate.py \
  --repo /path/to/repo \
  --task "Review this OpenSpec task and propose the smallest implementation plan." \
  --json
```

Delegate an edit-capable task only after approval:

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
4. Use apply mode only for explicit execution tasks.
5. After Claude returns, read the normalized JSON result and inspect local diffs.
6. Run Codex-owned verification commands.
7. Record evidence in the active OpenSpec tasks and DevFlow verification files.
