from __future__ import annotations

from pathlib import Path
from typing import Any

from .session import Contributor
from .util import approx_tokens, load_toml, read_text, safe_rel

AI_CONFIG_NAMES = {"AGENTS.md", "AGENTS.override.md", "CLAUDE.md", "GEMINI.md", ".cursorrules", ".windsurfrules"}
LEGACY_AI_CONFIG_NAMES = {"CLAUDE.md", "GEMINI.md", ".cursorrules", ".windsurfrules"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache"}
DEFAULT_PROJECT_DOC_MAX_BYTES = 32768


def scan_project_sources(
    repo: Path | None,
    cwd: Path | None = None,
    fallback_names: list[str] | None = None,
    project_doc_max_bytes: int | None = None,
) -> tuple[list[Contributor], dict[str, Any]]:
    if repo is None or not repo.exists():
        return [], {"agents_files": 0, "legacy_ai_files": 0, "project_skills": 0, "instruction_chain": []}
    project_config = load_toml(repo / ".codex" / "config.toml")
    project_fallbacks = list(project_config.get("project_doc_fallback_filenames") or [])
    fallback_names = dedupe([*(fallback_names or []), *project_fallbacks])
    project_doc_max_bytes = int(project_config.get("project_doc_max_bytes") or project_doc_max_bytes or DEFAULT_PROJECT_DOC_MAX_BYTES)
    instruction_names = {"AGENTS.md", "AGENTS.override.md", *fallback_names}
    contributors: list[Contributor] = []
    inventory: dict[str, Any] = {
        "agents_files": 0,
        "legacy_ai_files": 0,
        "project_skills": 0,
        "has_planning_state": False,
        "has_openspec": False,
        "has_project_config": bool(project_config),
        "project_mcp_servers": count_table(project_config.get("mcp_servers")),
        "project_agents": count_table(project_config.get("agents")),
        "project_doc_fallback_filenames": fallback_names,
        "project_doc_max_bytes": project_doc_max_bytes,
    }
    for path in walk_files(repo):
        rel = safe_rel(path, repo)
        if rel == ".codex/config.toml":
            contributors.append(file_contributor(path, "project Codex config.toml", "config", "project", repo))
        elif path.name in instruction_names:
            inventory["agents_files"] += 1
            contributors.append(file_contributor(path, instruction_label(path.name), "agents", "project", repo))
        elif path.name in LEGACY_AI_CONFIG_NAMES:
            inventory["legacy_ai_files"] += 1
            contributors.append(file_contributor(path, f"legacy AI config: {path.name}", "legacy_ai_config", "project", repo))
        elif rel.startswith(".codex/skills/") and rel.endswith("/SKILL.md"):
            inventory["project_skills"] += 1
            contributors.append(skill_metadata_contributor(path, f"project skill metadata: {path.parent.name}", "project", repo))
        elif rel == ".planning/STATE.md":
            inventory["has_planning_state"] = True
            contributors.append(file_contributor(path, "planning state", "workflow_state", "project", repo))
        elif rel == "openspec/config.yaml":
            inventory["has_openspec"] = True
            contributors.append(file_contributor(path, "OpenSpec config", "workflow_config", "project", repo))
    chain = discover_project_instruction_chain(repo, cwd or repo, fallback_names, project_doc_max_bytes)
    inventory["instruction_chain"] = chain
    inventory["instruction_chain_bytes"] = sum(item["bytes"] for item in chain if item["status"] in {"loaded", "truncated"})
    inventory["instruction_chain_truncated"] = any(item["status"] == "truncated" for item in chain)
    return contributors, inventory


def scan_codex_home(codex_home: Path) -> tuple[list[Contributor], dict[str, Any]]:
    config_path = codex_home / "config.toml"
    config = load_toml(config_path)
    profile_name = config.get("profile")
    profile = active_profile(config)
    contributors: list[Contributor] = []
    if config_path.exists():
        contributors.append(file_contributor(config_path, "global Codex config.toml", "config", "global", codex_home))
    global_instruction = select_global_instruction(codex_home)
    if global_instruction:
        contributors.append(file_contributor(global_instruction, f"global instruction: {global_instruction.name}", "agents", "global", codex_home))
    global_skills = list((codex_home / "skills").glob("*/SKILL.md")) if (codex_home / "skills").exists() else []
    for path in global_skills:
        contributors.append(skill_metadata_contributor(path, f"global skill metadata: {path.parent.name}", "global", codex_home))
    plugins = config.get("plugins", {}) if isinstance(config.get("plugins"), dict) else {}
    enabled_plugins = [key for key, value in plugins.items() if not isinstance(value, dict) or value.get("enabled") is not False]
    mcp_servers = config.get("mcp_servers", {}) if isinstance(config.get("mcp_servers"), dict) else {}
    features = config.get("features", {}) if isinstance(config.get("features"), dict) else {}
    return contributors, {
        "enabled_global_plugins": len(enabled_plugins),
        "enabled_global_plugin_keys": sorted(enabled_plugins),
        "global_skills": len(global_skills),
        "mcp_servers": len(mcp_servers),
        "mcp_server_keys": sorted(mcp_servers),
        "enabled_features": sorted(key for key, value in features.items() if value is True),
        "global_instruction_file": safe_rel(global_instruction, codex_home) if global_instruction else None,
        "model": profile.get("model") or config.get("model"),
        "profile": profile_name,
        "project_doc_max_bytes": profile.get("project_doc_max_bytes") or config.get("project_doc_max_bytes"),
        "project_doc_fallback_filenames": list(profile.get("project_doc_fallback_filenames") or config.get("project_doc_fallback_filenames") or []),
    }


def file_contributor(path: Path, label: str, kind: str, scope: str, root: Path) -> Contributor:
    text = read_text(path)
    return Contributor(label, kind, scope, approx_tokens(text), len(text), "estimated", path=safe_rel(path, root))


def skill_metadata_contributor(path: Path, label: str, scope: str, root: Path) -> Contributor:
    text = read_text(path)
    metadata = skill_metadata(text)
    return Contributor(label, "skill_metadata", scope, approx_tokens(metadata), len(metadata), "estimated", path=safe_rel(path, root))


def skill_metadata(text: str) -> str:
    if not text.startswith("---"):
        return "\n".join(text.splitlines()[:20])
    marker = "\n---"
    end = text.find(marker, 3)
    if end == -1:
        return "\n".join(text.splitlines()[:40])
    return text[: end + len(marker)]


def walk_files(root: Path):
    for child in root.iterdir():
        if child.is_dir():
            if child.name in SKIP_DIRS:
                continue
            yield from walk_files(child)
        elif child.is_file():
            yield child


def instruction_label(name: str) -> str:
    if name == "AGENTS.md":
        return "project AGENTS.md"
    if name == "AGENTS.override.md":
        return "project AGENTS.override.md"
    return f"project fallback instruction: {name}"


def select_global_instruction(codex_home: Path) -> Path | None:
    for name in ("AGENTS.override.md", "AGENTS.md"):
        path = codex_home / name
        if path.exists() and path.stat().st_size > 0:
            return path
    return None


def discover_project_instruction_chain(repo: Path, cwd: Path, fallback_names: list[str], max_bytes: int) -> list[dict[str, Any]]:
    try:
        cwd = cwd.resolve()
    except FileNotFoundError:
        cwd = cwd.parent.resolve()
    repo = repo.resolve()
    if not is_relative_to(cwd, repo):
        cwd = repo
    dirs = path_chain(repo, cwd if cwd.is_dir() else cwd.parent)
    chain: list[dict[str, Any]] = []
    loaded_bytes = 0
    names = ["AGENTS.override.md", "AGENTS.md", *fallback_names]
    for directory in dirs:
        selected = first_existing_instruction(directory, names)
        if not selected:
            continue
        text = read_text(selected)
        size = len(text)
        status = "loaded"
        if loaded_bytes >= max_bytes:
            status = "over_limit"
        elif loaded_bytes + size > max_bytes:
            status = "truncated"
        if status in {"loaded", "truncated"}:
            loaded_bytes += size
        chain.append(
            {
                "path": safe_rel(selected, repo),
                "source_name": selected.name,
                "bytes": size,
                "estimated_tokens": approx_tokens(text),
                "status": status,
            }
        )
        if loaded_bytes >= max_bytes:
            break
    return chain


def first_existing_instruction(directory: Path, names: list[str]) -> Path | None:
    for name in names:
        path = directory / name
        if path.exists() and path.is_file() and path.stat().st_size > 0:
            return path
    return None


def path_chain(root: Path, leaf: Path) -> list[Path]:
    if root == leaf:
        return [root]
    chain = [leaf]
    current = leaf
    while current != root and current.parent != current:
        current = current.parent
        chain.append(current)
    return list(reversed(chain))


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def count_table(value: Any) -> int:
    return len(value) if isinstance(value, dict) else 0


def dedupe(values: list[str]) -> list[str]:
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def active_profile(config: dict[str, Any]) -> dict[str, Any]:
    name = config.get("profile")
    profiles = config.get("profiles")
    if isinstance(name, str) and isinstance(profiles, dict) and isinstance(profiles.get(name), dict):
        return profiles[name]
    return {}
