#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from workflow_claude_delegate import ClaudeDelegateOptions, check_claude_capability, delegate_to_claude
from workflow_paths import repo_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Delegate a bounded task from Codex to Claude Code.")
    parser.add_argument("--repo", required=True, help="Repository root for the delegated task.")
    parser.add_argument("--task", default="", help="Task prompt to pass to Claude Code via stdin.")
    parser.add_argument("--task-file", help="Read the task prompt from this file.")
    parser.add_argument("--apply", action="store_true", help="Allow edit-capable Claude Code delegation.")
    parser.add_argument("--allow-dirty", action="store_true", help="Allow apply mode on a dirty Git worktree.")
    parser.add_argument("--max-budget-usd", default="1.00", help="Maximum Claude Code API spend for this run.")
    parser.add_argument("--model", help="Claude Code model or alias.")
    parser.add_argument("--effort", help="Claude Code effort level.")
    parser.add_argument(
        "--add-dir",
        action="append",
        default=[],
        help="Additional directory to allow Claude Code to access.",
    )
    parser.add_argument(
        "--allowed-tool",
        action="append",
        default=[],
        help="Claude Code tool allowlist entry. Repeat for multiple entries.",
    )
    parser.add_argument("--check", action="store_true", help="Only report whether Claude Code delegation is available.")
    parser.add_argument("--no-log", action="store_true", help="Do not write .dev-flow/claude-code run metadata.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output. Included for consistency with other scripts.",
    )
    args = parser.parse_args()

    if args.check:
        report = check_claude_capability()
    else:
        report = delegate_to_claude(
            ClaudeDelegateOptions(
                repo=repo_path(args.repo),
                task=args.task,
                task_file=Path(args.task_file).expanduser() if args.task_file else None,
                apply=args.apply,
                allow_dirty=args.allow_dirty,
                max_budget_usd=args.max_budget_usd,
                model=args.model,
                effort=args.effort,
                add_dirs=args.add_dir,
                allowed_tools=args.allowed_tool,
                log=not args.no_log,
            )
        )
    print(json.dumps(report, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
