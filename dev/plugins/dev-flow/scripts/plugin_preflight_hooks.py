from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


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
