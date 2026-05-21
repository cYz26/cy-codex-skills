from __future__ import annotations

import json
import re
import shutil
import tomllib
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


SIGNAL_KEYWORDS = {
    "javascript": {"web", "frontend", "node", "react", "next", "vite", "shadcn"},
    "react": {"react", "frontend", "web", "next", "shadcn"},
    "nextjs": {"next", "react", "frontend", "web"},
    "python": {"python", "pytest", "django", "fastapi"},
    "go": {"go", "golang"},
    "rust": {"rust", "cargo"},
    "swift": {"swift", "swiftui", "ios", "macos", "xcode"},
    "ios": {"ios", "swiftui", "xcode"},
    "android": {"android", "gradle", "kotlin"},
    "godot": {"godot"},
}


def audit_context_tools(
    codex_home: Path,
    repo: Path | None = None,
    config_path: Path | None = None,
    source_catalogs: list[Path] | None = None,
    source_urls: list[str] | None = None,
) -> dict[str, Any]:
    codex_home = Path(codex_home).expanduser().resolve()
    repo = Path(repo).expanduser().resolve() if repo else None
    config_path = Path(config_path).expanduser().resolve() if config_path else codex_home / "config.toml"
    config = read_config(config_path)
    inventory = {
        "globalPlugins": global_plugins(config),
        "globalSkills": global_skills(codex_home, config),
        "projectSkills": project_skills(repo),
        "installedSkills": installed_cache_skills(codex_home),
        "sourceTools": source_tools(source_catalogs or [], source_urls or []),
    }
    signals = project_signals(repo)
    findings: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    add_cleanup_recommendations(inventory, config_path, findings, recommendations, actions)
    add_install_recommendations(inventory, repo, signals, recommendations, actions)
    add_source_recommendations(inventory, signals, recommendations)
    return {
        "ok": True,
        "contextPressure": context_pressure(inventory),
        "codexHome": str(codex_home),
        "config": str(config_path),
        "repo": str(repo) if repo else None,
        "inventory": inventory,
        "projectSignals": signals,
        "findings": findings,
        "recommendations": recommendations,
        "actions": actions,
    }


def read_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    return tomllib.loads(config_path.read_text())


def global_plugins(config: dict[str, Any]) -> list[dict[str, Any]]:
    plugins = []
    for key, settings in sorted(config.get("plugins", {}).items()):
        plugins.append(
            {
                "key": key,
                "name": plugin_name(key),
                "enabled": settings.get("enabled") is True,
                "settings": dict(settings),
            }
        )
    return plugins


def global_skills(codex_home: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    skills_root = codex_home / "skills"
    if not skills_root.exists():
        return []
    skills = []
    disabled = disabled_skill_paths(config)
    for path in sorted(skills_root.glob("*/SKILL.md")):
        skills.append(
            {
                "name": path.parent.name,
                "path": str(path),
                "enabled": str(path) not in disabled,
            }
        )
    return skills


def project_skills(repo: Path | None) -> list[dict[str, Any]]:
    if repo is None:
        return []
    skills_root = repo / ".codex" / "skills"
    if not skills_root.exists():
        return []
    return [{"name": path.parent.name, "path": str(path)} for path in sorted(skills_root.glob("*/SKILL.md"))]


def installed_cache_skills(codex_home: Path) -> list[dict[str, Any]]:
    cache = codex_home / "plugins" / "cache"
    if not cache.exists():
        return []
    skills = []
    for path in sorted(cache.rglob("skills/*/SKILL.md")):
        plugin, source = cache_plugin_parts(cache, path)
        skills.append(
            {
                "name": path.parent.name,
                "path": str(path),
                "plugin": plugin,
                "source": source,
                "key": f"{plugin}@{source}" if source else plugin,
            }
        )
    return skills


def disabled_skill_paths(config: dict[str, Any]) -> set[str]:
    disabled = set()
    for entry in config.get("skills", {}).get("config", []):
        if entry.get("enabled") is False and entry.get("path"):
            disabled.add(str(entry["path"]))
    return disabled


def cache_plugin_parts(cache: Path, skill_path: Path) -> tuple[str, str]:
    relative = skill_path.relative_to(cache)
    parts = relative.parts
    if len(parts) >= 4:
        return parts[1], parts[0]
    return "unknown", ""


def plugin_name(key: str) -> str:
    return key.split("@", 1)[0]


def project_signals(repo: Path | None) -> list[str]:
    if repo is None:
        return []
    signals: set[str] = set()
    package_json = repo / "package.json"
    if package_json.exists():
        signals.add("javascript")
        text = package_json.read_text(errors="ignore").lower()
        if "react" in text:
            signals.add("react")
        if "next" in text:
            signals.add("nextjs")
    if (repo / "pyproject.toml").exists() or (repo / "requirements.txt").exists():
        signals.add("python")
    if (repo / "go.mod").exists():
        signals.add("go")
    if (repo / "Cargo.toml").exists():
        signals.add("rust")
    if (repo / "Package.swift").exists():
        signals.add("swift")
    if list(repo.glob("*.xcodeproj")) or list(repo.glob("*.xcworkspace")):
        signals.update({"swift", "ios"})
    if (repo / "project.godot").exists():
        signals.add("godot")
    if (repo / "settings.gradle").exists() or (repo / "settings.gradle.kts").exists():
        signals.add("android")
    return sorted(signals)


def context_pressure(inventory: dict[str, Any]) -> str:
    enabled_plugins = [item for item in inventory["globalPlugins"] if item["enabled"]]
    enabled_skills = [item for item in inventory["globalSkills"] if item["enabled"]]
    active_count = len(enabled_plugins) + len(enabled_skills)
    if active_count >= 3:
        return "high"
    if active_count:
        return "medium"
    return "low"


def add_cleanup_recommendations(
    inventory: dict[str, Any],
    config_path: Path,
    findings: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    actions: list[dict[str, Any]],
) -> None:
    for plugin in inventory["globalPlugins"]:
        if not plugin["enabled"]:
            continue
        action = {
            "id": f"disable-global-plugin-{slug(plugin['key'])}",
            "type": "disable_global_plugin",
            "title": f"Disable global plugin {plugin['key']}",
            "reason": "Global plugins occupy every session; prefer project-local tools when possible.",
            "safety": "safe",
            "requiresAuthorization": True,
            "payload": {"configPath": str(config_path), "pluginKey": plugin["key"]},
        }
        actions.append(action)
        findings.append({"level": "warning", "message": f"Global plugin is enabled: {plugin['key']}"})
        recommendations.append(recommendation("cleanup", action, action["reason"]))
    for skill in inventory["globalSkills"]:
        if not skill["enabled"]:
            continue
        action = {
            "id": f"disable-global-skill-{slug(skill['name'])}",
            "type": "disable_global_skill",
            "title": f"Disable global skill {skill['name']}",
            "reason": "Global skills occupy baseline context; prefer repo-local activation.",
            "safety": "safe",
            "requiresAuthorization": True,
            "payload": {"configPath": str(config_path), "skillPath": skill["path"], "skillName": skill["name"]},
        }
        actions.append(action)
        findings.append({"level": "warning", "message": f"Global skill is active: {skill['name']}"})
        recommendations.append(recommendation("cleanup", action, action["reason"]))


def add_install_recommendations(
    inventory: dict[str, Any],
    repo: Path | None,
    signals: list[str],
    recommendations: list[dict[str, Any]],
    actions: list[dict[str, Any]],
) -> None:
    if repo is None:
        return
    active_project_skills = {item["name"] for item in inventory["projectSkills"]}
    for skill in inventory["installedSkills"]:
        if skill["name"] in active_project_skills or not relevant_to_project(skill, signals):
            continue
        destination = repo / ".codex" / "skills" / skill["name"]
        action = {
            "id": f"install-project-skill-{slug(skill['name'])}",
            "type": "install_project_skill",
            "title": f"Install project-local skill {skill['name']}",
            "reason": f"Installed skill matches project signals: {', '.join(signals)}.",
            "safety": "safe",
            "requiresAuthorization": True,
            "payload": {
                "sourcePath": skill["path"],
                "destinationPath": str(destination),
                "repo": str(repo),
                "skillName": skill["name"],
            },
        }
        actions.append(action)
        recommendations.append(recommendation("install", action, action["reason"]))


def add_source_recommendations(
    inventory: dict[str, Any],
    signals: list[str],
    recommendations: list[dict[str, Any]],
) -> None:
    for tool in inventory["sourceTools"]:
        if tool.get("error") or not relevant_to_project(tool, signals):
            continue
        name = tool.get("name", "unknown")
        tool_type = tool.get("type", "tool")
        recommendations.append(
            {
                "kind": "discovery",
                "actionId": None,
                "title": f"Consider {tool_type} {name}",
                "reason": f"Source catalog entry matches project signals: {', '.join(signals)}.",
            }
        )


def recommendation(kind: str, action: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "actionId": action["id"],
        "title": action["title"],
        "reason": reason,
    }


def relevant_to_project(tool: dict[str, Any], signals: list[str]) -> bool:
    if not signals:
        return False
    haystack = " ".join(str(tool.get(key, "")) for key in ["name", "plugin", "key", "description"]).lower()
    for signal in signals:
        keywords = SIGNAL_KEYWORDS.get(signal, {signal})
        if any(keyword in haystack for keyword in keywords):
            return True
    return False


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def source_tools(source_catalogs: list[Path], source_urls: list[str]) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for catalog in source_catalogs:
        tools.extend(read_catalog(Path(catalog), str(catalog)))
    for url in source_urls:
        tools.extend(read_url_catalog(url))
    return tools


def read_catalog(path: Path, source: str) -> list[dict[str, Any]]:
    if not path.exists():
        return [{"source": source, "error": "missing"}]
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return [{"source": source, "error": str(exc)}]
    return normalize_catalog_tools(data, source)


def read_url_catalog(url: str) -> list[dict[str, Any]]:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # pragma: no cover - network failure shape varies.
        return [{"source": url, "error": str(exc)}]
    return normalize_catalog_tools(data, url)


def normalize_catalog_tools(data: dict[str, Any], source: str) -> list[dict[str, Any]]:
    tools = []
    for plugin in data.get("plugins", []):
        tools.append(
            {
                "source": source,
                "type": "plugin",
                "name": plugin.get("name", ""),
                "description": plugin.get("description", ""),
            }
        )
    return tools


def apply_context_tool_actions(
    report: dict[str, Any],
    action_ids: list[str] | None = None,
    all_safe: bool = False,
    apply: bool = False,
    timestamp: str | None = None,
) -> dict[str, Any]:
    missing = missing_action_ids(report.get("actions", []), action_ids or [])
    if missing:
        return {"ok": False, "dryRun": not apply, "applied": [], "errors": [f"unknown actions: {', '.join(missing)}"]}
    selected = select_actions(report.get("actions", []), action_ids or [], all_safe)
    if not selected:
        return {"ok": False, "dryRun": not apply, "applied": [], "errors": ["no actions selected"]}
    backups: dict[Path, Path] = {}
    results = []
    errors = []
    for action in selected:
        try:
            if apply:
                results.append(execute_action(action, backups, timestamp))
            else:
                results.append({"id": action["id"], "type": action["type"], "status": "dry-run"})
        except Exception as exc:
            errors.append(f"{action['id']}: {exc}")
    return {
        "ok": not errors,
        "dryRun": not apply,
        "applied": results,
        "errors": errors,
        "backups": [str(path) for path in backups.values()],
    }


def missing_action_ids(actions: list[dict[str, Any]], action_ids: list[str]) -> list[str]:
    available = {action["id"] for action in actions}
    return sorted(set(action_ids) - available)


def select_actions(actions: list[dict[str, Any]], action_ids: list[str], all_safe: bool) -> list[dict[str, Any]]:
    selected_ids = set(action_ids)
    selected = []
    for action in actions:
        if action["id"] in selected_ids or (all_safe and action.get("safety") == "safe"):
            selected.append(action)
    return selected


def execute_action(action: dict[str, Any], backups: dict[Path, Path], timestamp: str | None) -> dict[str, Any]:
    action_type = action["type"]
    if action_type == "disable_global_plugin":
        return disable_global_plugin(action, backups, timestamp)
    if action_type == "disable_global_skill":
        return disable_global_skill(action, backups, timestamp)
    if action_type == "install_project_skill":
        return install_project_skill(action)
    raise ValueError(f"unsupported action type: {action_type}")


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
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source.parent, destination, dirs_exist_ok=True)
    return {"id": action["id"], "type": action["type"], "status": "applied"}


def ensure_backup(config_path: Path, backups: dict[Path, Path], timestamp: str | None) -> Path:
    config_path = config_path.resolve()
    if config_path in backups:
        return backups[config_path]
    stamp = timestamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = config_path.with_name(f"{config_path.name}.bak-{stamp}")
    if config_path.exists():
        shutil.copy2(config_path, backup)
    else:
        backup.write_text("")
    backups[config_path] = backup
    return backup


def set_plugin_enabled(text: str, plugin_key: str, enabled: bool) -> str:
    lines = text.splitlines()
    header = f'[plugins."{plugin_key}"]'
    enabled_line = f"enabled = {'true' if enabled else 'false'}"
    for index, line in enumerate(lines):
        if line.strip() != header:
            continue
        end = next_section_index(lines, index + 1)
        for line_index in range(index + 1, end):
            if re.match(r"\s*enabled\s*=", lines[line_index]):
                indent = re.match(r"(\s*)", lines[line_index]).group(1)
                lines[line_index] = f"{indent}{enabled_line}"
                return "\n".join(lines) + "\n"
        lines.insert(index + 1, enabled_line)
        return "\n".join(lines) + "\n"
    if lines and lines[-1].strip():
        lines.append("")
    lines.extend([header, enabled_line])
    return "\n".join(lines) + "\n"


def next_section_index(lines: list[str], start: int) -> int:
    for index in range(start, len(lines)):
        if lines[index].lstrip().startswith("["):
            return index
    return len(lines)


def append_disabled_skill(text: str, skill_path: str) -> str:
    block = ["", "[[skills.config]]", f'path = "{escape_toml_string(skill_path)}"', "enabled = false"]
    stripped = text.rstrip("\n")
    return stripped + "\n" + "\n".join(block) + "\n"


def escape_toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
