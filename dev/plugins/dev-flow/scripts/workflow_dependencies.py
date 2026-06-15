from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

from workflow_context_config import read_config
from workflow_dependency_checks import check_external_dependencies
from workflow_dependency_provenance import dependency_provenance_report
from workflow_paths import repo_path


def dependency_report(
    plugin_root: Path,
    codex_home: Path | None = None,
    config_path: Path | None = None,
    strict: bool = False,
    repo: Path | None = None,
) -> dict[str, Any]:
    plugin_root = repo_path(plugin_root)
    codex_home = repo_path(codex_home or Path.home() / ".codex")
    config_path = repo_path(config_path or codex_home / "config.toml")
    repo = repo_path(repo) if repo else None
    config = read_config(config_path)
    project_config_path = repo / ".codex" / "config.toml" if repo else None
    checks: list[dict[str, Any]] = []
    codex_cli = shutil.which("codex")
    add_check(checks, "python runtime", True, True, sys.version.split()[0])
    add_check(checks, "codex cli available", codex_cli is not None, True, codex_cli if codex_cli else "missing")
    add_check(checks, "plugin root", (plugin_root / ".codex-plugin" / "plugin.json").exists(), True, str(plugin_root))
    check_external_dependencies(checks, codex_home, config, strict, repo)
    provenance = dependency_provenance_report(plugin_root, repo)
    checks.extend(provenance["checks"])
    required_ok = all(item["ok"] for item in checks if item["required"])
    recommended_ok = all(item["ok"] for item in checks)
    return {
        "ok": required_ok,
        "status": dependency_status(required_ok, recommended_ok),
        "codex_home": str(codex_home),
        "config": str(config_path),
        "repo": str(repo) if repo else None,
        "project_config": str(project_config_path) if project_config_path else None,
        "provenance": provenance["provenance"],
        "dependencies": provenance["dependencies"],
        "checks": checks,
    }

def add_check(checks: list[dict[str, Any]], name: str, ok: bool, required: bool, detail: str = "") -> None:
    checks.append({"name": name, "ok": bool(ok), "required": bool(required), "detail": detail})


def dependency_status(required_ok: bool, recommended_ok: bool) -> str:
    if not required_ok:
        return "missing_required"
    if not recommended_ok:
        return "ready_with_recommendations"
    return "ready"
