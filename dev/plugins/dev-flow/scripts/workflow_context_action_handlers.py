from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from workflow_context_action_config import append_disabled_skill, ensure_backup, set_plugin_enabled
from workflow_project_skill_paths import guard_project_skill_write


def execute_action(action: dict[str, Any], backups: dict[Path, Path], timestamp: str | None) -> dict[str, Any]:
    handlers = {
        "disable_global_plugin": disable_global_plugin,
        "disable_global_skill": disable_global_skill,
        "install_project_skill": install_project_skill,
    }
    handler = handlers.get(action["type"])
    if handler is None:
        raise ValueError(f"unsupported action type: {action['type']}")
    if action["type"] == "install_project_skill":
        return handler(action)
    return handler(action, backups, timestamp)


def disable_global_plugin(action: dict[str, Any], backups: dict[Path, Path], timestamp: str | None) -> dict[str, Any]:
    payload = action["payload"]
    config_path = Path(payload["configPath"])
    ensure_backup(config_path, backups, timestamp)
    text = config_path.read_text() if config_path.exists() else ""
    config_path.write_text(set_plugin_enabled(text, payload["pluginKey"], False))
    return {"id": action["id"], "type": action["type"], "status": "applied"}


def disable_global_skill(action: dict[str, Any], backups: dict[Path, Path], timestamp: str | None) -> dict[str, Any]:
    payload = action["payload"]
    config_path = Path(payload["configPath"])
    ensure_backup(config_path, backups, timestamp)
    text = config_path.read_text() if config_path.exists() else ""
    config_path.write_text(append_disabled_skill(text, payload["skillPath"]))
    return {"id": action["id"], "type": action["type"], "status": "applied"}


def install_project_skill(action: dict[str, Any]) -> dict[str, Any]:
    payload = action["payload"]
    source = Path(payload["sourcePath"])
    destination = Path(payload["destinationPath"])
    guard_project_skill_write(Path(payload["repo"]), destination)
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source.parent, destination, dirs_exist_ok=True)
    return {"id": action["id"], "type": action["type"], "status": "applied"}
