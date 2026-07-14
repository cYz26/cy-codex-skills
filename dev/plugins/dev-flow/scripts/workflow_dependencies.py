from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

from workflow_context_config import read_config
from workflow_dependency_checks import check_external_dependencies
from workflow_dependency_provenance import dependency_provenance_report
from workflow_methodology import CAPABILITY_IDS, required_matt_skills, route_capability
from workflow_mode_routing import read_workflow_mode_config
from workflow_paths import repo_path


def dependency_report(
    plugin_root: Path,
    codex_home: Path | None = None,
    config_path: Path | None = None,
    strict: bool = False,
    repo: Path | None = None,
    triggered_capabilities: set[str] | None = None,
) -> dict[str, Any]:
    plugin_root = repo_path(plugin_root)
    codex_home = repo_path(codex_home or Path.home() / ".codex")
    config_path = repo_path(config_path or codex_home / "config.toml")
    repo = repo_path(repo) if repo else None
    requested = set(triggered_capabilities or set())
    unknown = requested.difference(CAPABILITY_IDS)
    if unknown:
        raise ValueError(
            "unsupported DevFlow capability: " + ", ".join(sorted(unknown))
        )

    config = read_config(config_path)
    project_config_path = repo / ".codex" / "config.toml" if repo else None
    checks: list[dict[str, Any]] = []
    codex_cli = shutil.which("codex")
    add_check(checks, "python runtime", True, True, sys.version.split()[0])
    add_check(
        checks,
        "codex cli available",
        codex_cli is not None,
        True,
        codex_cli if codex_cli else "missing",
    )
    add_check(
        checks,
        "plugin root",
        (plugin_root / ".codex-plugin" / "plugin.json").exists(),
        True,
        str(plugin_root),
    )
    workflow_config = read_workflow_mode_config(repo) if repo else None
    if workflow_config is not None:
        add_check(
            checks,
            "workflow config current",
            bool(workflow_config["valid"]),
            True,
            (
                workflow_config["source"]
                if workflow_config["valid"]
                else "; ".join(workflow_config["config_errors"])
            ),
        )

    methodology = check_external_dependencies(
        checks,
        codex_home,
        config,
        strict,
        repo,
        plugin_root=plugin_root,
        triggered_capabilities=requested,
    )
    selected_dependencies = {"openspec-cli"}
    if strict:
        selected_dependencies.add("plugin-eval")
    provenance = dependency_provenance_report(
        plugin_root,
        repo,
        included_names=selected_dependencies,
    )
    scope_provenance_requiredness(provenance, strict)
    checks.extend(provenance["checks"])

    required_ok = all(item["ok"] for item in checks if item["required"])
    recommended_ok = all(item["ok"] for item in checks)
    capabilities = capability_report(requested, methodology, required_ok)
    return {
        "ok": required_ok,
        "status": dependency_status(required_ok, recommended_ok),
        "codex_home": str(codex_home),
        "config": str(config_path),
        "repo": str(repo) if repo else None,
        "project_config": str(project_config_path) if project_config_path else None,
        "workflowConfig": workflow_config,
        "provenance": provenance["provenance"],
        "dependencies": provenance["dependencies"],
        "methodology": methodology,
        "capabilities": capabilities,
        "workflowReady": required_ok,
        "triggeredCapabilities": sorted(requested),
        "checks": checks,
    }


def capability_report(
    requested: set[str],
    methodology: dict[str, Any],
    workflow_ready: bool,
) -> dict[str, Any]:
    report: dict[str, Any] = {}
    ready_matt = {
        skill
        for skill, result in methodology.get("skills", {}).items()
        if result.get("ready")
    }
    for capability in CAPABILITY_IDS:
        route = route_capability(capability)
        matt = required_matt_skills({capability})
        triggered = capability in requested
        ready = workflow_ready and all(skill in ready_matt for skill in matt)
        report[capability] = {
            **route,
            "triggered": triggered,
            "ready": ready if triggered else True,
            "status": "ready" if (ready or not triggered) else "missing",
        }
    return report


def scope_provenance_requiredness(
    provenance: dict[str, Any],
    strict: bool,
) -> None:
    required = {"openspec-cli": True, "plugin-eval": strict}
    for dependency in provenance["dependencies"]:
        dependency["required"] = required.get(dependency["name"], False)
    for check in provenance["checks"]:
        name = check["name"].removeprefix("external dependency: ")
        check["required"] = required.get(name, False)


def add_check(
    checks: list[dict[str, Any]],
    name: str,
    ok: bool,
    required: bool,
    detail: str = "",
) -> None:
    checks.append(
        {"name": name, "ok": bool(ok), "required": bool(required), "detail": detail}
    )


def dependency_status(required_ok: bool, recommended_ok: bool) -> str:
    if not required_ok:
        return "missing_required"
    if not recommended_ok:
        return "ready_with_recommendations"
    return "ready"
