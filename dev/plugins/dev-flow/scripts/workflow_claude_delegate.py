from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from workflow_paths import rel, repo_path


Runner = Callable[..., subprocess.CompletedProcess[str]]
PathResolver = Callable[[str], str | None]


PLAN_DELEGATION_CONTRACT = "\n".join(
    [
        "DevFlow Claude Code delegation contract (plan mode):",
        "- You are Claude Code running as the delegated worker for Codex.",
        "- Claude Code must complete the full analysis, review, or planning deliverable requested below inside "
        "this Claude Code run.",
        "- Do not edit files in plan mode.",
        "- Report key process evidence, assumptions, risks, and blockers.",
        "- Codex will independently verify the process and result evidence after you return.",
    ]
)


APPLY_DELEGATION_CONTRACT = "\n".join(
    [
        "DevFlow Claude Code delegation contract (apply mode):",
        "- You are Claude Code running as the delegated worker for Codex.",
        "- Claude Code must complete all in-scope execution inside this Claude Code run: inspect relevant files, "
        "edit files, run requested or relevant checks, update docs or workflow files, and perform Git operations "
        "only when the delegated task explicitly asks for them.",
        "- Do not leave required delegated execution for Codex unless you are blocked; report the blocker instead.",
        "- Report files changed, commands run, verification results, Git operations, remaining risks, and blockers.",
        "- Codex will independently verify the process and result evidence after you return.",
    ]
)


@dataclass
class ClaudeDelegateOptions:
    repo: Path
    task: str = ""
    task_file: Path | None = None
    apply: bool = False
    allow_dirty: bool = False
    max_budget_usd: str = "1.00"
    model: str | None = None
    effort: str | None = None
    add_dirs: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    log: bool = True

    @property
    def mode(self) -> str:
        return "apply" if self.apply else "plan"


def check_claude_capability(
    *,
    path_resolver: PathResolver = shutil.which,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    claude_path = path_resolver("claude")
    if not claude_path:
        return {
            "ok": False,
            "reason": "claude-not-found",
            "message": "Claude Code is an optional runtime capability and the `claude` executable was not found.",
        }
    result = runner([claude_path, "--version"], text=True, capture_output=True, check=False)
    version = (result.stdout or result.stderr or "").strip()
    if result.returncode != 0:
        return {
            "ok": False,
            "reason": "claude-version-failed",
            "message": "Claude Code was found, but version detection failed.",
            "claudePath": claude_path,
            "exitCode": result.returncode,
            "stderr": (result.stderr or "").strip(),
        }
    return {
        "ok": True,
        "claudePath": claude_path,
        "claudeVersion": version,
    }


def delegate_to_claude(
    options: ClaudeDelegateOptions,
    *,
    path_resolver: PathResolver = shutil.which,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    repo = repo_path(options.repo)
    capability = check_claude_capability(path_resolver=path_resolver, runner=runner)
    if not capability["ok"]:
        return {
            **capability,
            "mode": options.mode,
            "command": [],
        }

    if options.apply:
        dirty = dirty_worktree_report(repo, runner=runner)
        if dirty["dirty"] and not options.allow_dirty:
            return {
                "ok": False,
                "reason": "dirty-worktree",
                "message": (
                    "Refusing apply-mode Claude Code delegation because the git dirty worktree safety gate is active."
                ),
                "mode": options.mode,
                "claudePath": capability["claudePath"],
                "claudeVersion": capability.get("claudeVersion", ""),
                "dirtyFiles": dirty["files"],
            }
        if dirty.get("error"):
            return {
                "ok": False,
                "reason": "git-status-failed",
                "message": "Could not verify Git worktree cleanliness before apply-mode delegation.",
                "mode": options.mode,
                "claudePath": capability["claudePath"],
                "claudeVersion": capability.get("claudeVersion", ""),
                "stderr": dirty.get("stderr", ""),
            }

    raw_task = task_text(options)
    if not raw_task.strip():
        return {
            "ok": False,
            "reason": "missing-task",
            "message": "Claude Code delegation requires --task or --task-file.",
            "mode": options.mode,
            "claudePath": capability["claudePath"],
            "claudeVersion": capability.get("claudeVersion", ""),
            "command": [],
        }
    task = delegated_task_prompt(options, raw_task)

    command = build_claude_command(capability["claudePath"], options)
    result = runner(
        command,
        input=task,
        text=True,
        cwd=repo,
        capture_output=True,
        check=False,
    )
    report = normalize_claude_result(result, options, capability, command)
    if options.log:
        report["runLog"] = write_run_log(repo, report)
    return report


def task_text(options: ClaudeDelegateOptions) -> str:
    if options.task_file:
        return Path(options.task_file).expanduser().read_text()
    return options.task


def delegated_task_prompt(options: ClaudeDelegateOptions, task: str) -> str:
    contract = APPLY_DELEGATION_CONTRACT if options.apply else PLAN_DELEGATION_CONTRACT
    return f"{contract}\n\nDelegated task:\n{task.strip()}\n"


def dirty_worktree_report(repo: Path, *, runner: Runner = subprocess.run) -> dict[str, Any]:
    result = runner(["git", "status", "--porcelain"], text=True, cwd=repo, capture_output=True, check=False)
    if result.returncode != 0:
        return {"dirty": False, "error": True, "stderr": (result.stderr or "").strip()}
    files = [line for line in (result.stdout or "").splitlines() if line.strip()]
    return {"dirty": bool(files), "files": files}


def build_claude_command(claude_path: str, options: ClaudeDelegateOptions) -> list[str]:
    command = [
        claude_path,
        "-p",
        "--output-format=json",
        "--no-session-persistence",
        "--permission-mode",
        "bypassPermissions" if options.apply else "plan",
        "--max-budget-usd",
        str(options.max_budget_usd),
    ]
    if options.model:
        command.extend(["--model", options.model])
    if options.effort:
        command.extend(["--effort", options.effort])
    for directory in options.add_dirs:
        command.extend(["--add-dir", directory])
    if options.allowed_tools:
        command.extend(["--allowedTools", ",".join(options.allowed_tools)])
    return command


def normalize_claude_result(
    result: subprocess.CompletedProcess[str],
    options: ClaudeDelegateOptions,
    capability: dict[str, Any],
    command: list[str],
) -> dict[str, Any]:
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    try:
        payload = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        return {
            "ok": False,
            "reason": "invalid-json",
            "message": "Claude Code returned non-JSON output.",
            "mode": options.mode,
            "claudePath": capability["claudePath"],
            "claudeVersion": capability.get("claudeVersion", ""),
            "command": command,
            "exitCode": result.returncode,
            "stdoutPreview": stdout[:1200],
            "stderr": stderr,
        }

    is_error = bool(payload.get("is_error")) or result.returncode != 0
    report = {
        "ok": not is_error,
        "mode": options.mode,
        "claudePath": capability["claudePath"],
        "claudeVersion": capability.get("claudeVersion", ""),
        "command": command,
        "exitCode": result.returncode,
        "resultType": payload.get("type"),
        "resultSubtype": payload.get("subtype"),
        "isError": bool(payload.get("is_error")),
        "sessionId": payload.get("session_id"),
        "costUsd": payload.get("total_cost_usd"),
        "text": payload.get("result") or payload.get("message") or "",
        "errors": payload.get("errors") or [],
    }
    if stderr:
        report["stderr"] = stderr
    return report


def write_run_log(repo: Path, report: dict[str, Any]) -> str:
    runs = repo / ".dev-flow" / "claude-code" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    path = runs / f"{timestamp}-{report.get('mode', 'unknown')}.json"
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": report.get("mode"),
        "ok": report.get("ok"),
        "exitCode": report.get("exitCode"),
        "resultType": report.get("resultType"),
        "resultSubtype": report.get("resultSubtype"),
        "isError": report.get("isError"),
        "sessionId": report.get("sessionId"),
        "costUsd": report.get("costUsd"),
        "claudeVersion": report.get("claudeVersion"),
    }
    path.write_text(f"{json.dumps(payload, indent=2)}\n")
    return rel(repo, path)
