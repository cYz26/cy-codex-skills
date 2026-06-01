from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional


def simulate_hook(plugin_root: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="cpo-preflight-") as tmp:
        repo = Path(tmp)
        (repo / "src").mkdir()
        (repo / "src" / "main.py").write_text("print('ok')\n")
        result = subprocess.run(
            [sys.executable, str(plugin_root / "scripts" / "pre_edit_policy.py")],
            input=hook_payload(repo),
            text=True,
            capture_output=True,
            check=False,
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }


def hook_payload(repo: Path) -> str:
    return json.dumps(
        {
            "cwd": str(repo),
            "tool_name": "Edit",
            "tool_input": {"file_path": str(repo / "src" / "main.py")},
        }
    )


def hook_commands(hooks: dict[str, Any]) -> list[str]:
    commands: list[str] = []
    for entries in hooks.get("hooks", {}).values():
        for entry in entries:
            commands.extend(hook.get("command") for hook in entry.get("hooks", []))
    return [command for command in commands if command]


def hook_cache_drift_issues(plugin_root: Path, codex_home: Optional[Path] = None) -> list[str]:
    hooks_path = plugin_root / "hooks.json"
    if not hooks_path.exists():
        return []
    codex_home = codex_home or Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    hooks = json.loads(hooks_path.read_text())
    issues: list[str] = []
    for command in hook_commands(hooks):
        script_name = hook_script_name(command)
        cache_script = hook_cache_script_path(command, codex_home)
        if not script_name or not cache_script:
            continue
        source_script = plugin_root / "scripts" / script_name
        if source_script.exists() and not cache_script.exists():
            issues.append(
                "source/cache hook drift: source hook script "
                f"`scripts/{script_name}` is referenced by hooks.json but missing from installed cache "
                f"`{cache_script}`. Reinstall or refresh the dev-flow plugin cache."
            )
    return issues


def hook_script_name(command: str) -> Optional[str]:
    match = re.search(r"/scripts/([^\"'\s]+\.py)\b", command)
    if not match:
        return None
    return Path(match.group(1)).name


def hook_cache_script_path(command: str, codex_home: Path) -> Optional[Path]:
    match = re.search(r"plugins/cache/([^\"'\s]+/scripts/[^\"'\s]+\.py)\b", command)
    if not match:
        return None
    return codex_home / "plugins" / "cache" / match.group(1)
