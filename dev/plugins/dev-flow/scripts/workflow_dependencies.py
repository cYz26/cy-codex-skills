from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

from workflow_context_config import read_config
from workflow_dependency_checks import check_external_dependencies
from workflow_dependency_provenance import dependency_provenance_report, load_dependency_provenance
from workflow_paths import repo_path
from workflow_provider_profiles import diagnose_provider_selection, resolve_provider_selection
from workflow_provider_activation import (
    apply_provider_selection_overrides,
    apply_provider_source_overrides,
)


def dependency_report(
    plugin_root: Path,
    codex_home: Path | None = None,
    config_path: Path | None = None,
    strict: bool = False,
    repo: Path | None = None,
    triggered_capabilities: set[str] | None = None,
    methodology_profile: str | None = None,
    roadmap_provider: str | None = None,
    provider_sources: list[str] | None = None,
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
    selection = resolve_provider_selection(repo, codex_home, config) if repo else None
    if selection is not None:
        selection = apply_provider_selection_overrides(
            selection,
            methodology_profile,
            roadmap_provider,
        )
        selection = apply_provider_source_overrides(
            selection,
            provider_sources,
            load_dependency_provenance(plugin_root).get("providerSources", {}),
        )
    provider_report = (
        diagnose_provider_selection(
            selection,
            repo,
            codex_home,
            triggered_capabilities=triggered_capabilities,
            core_plugin_root=plugin_root,
        )
        if selection is not None and repo is not None
        else None
    )
    superpowers = check_external_dependencies(
        checks,
        codex_home,
        config,
        strict,
        repo,
        selection=selection,
        provider_report=provider_report,
        triggered_capabilities=triggered_capabilities,
    )
    catalog_only_dependencies = (
        {"gsd-core"}
        if selection is None or selection["effectiveRoadmapProvider"] != "gsd"
        else set()
    )
    provenance = dependency_provenance_report(
        plugin_root,
        repo,
        catalog_only_names=catalog_only_dependencies,
    )
    scope_provenance_requiredness(provenance, selection, strict)
    checks.extend(provenance["checks"])
    provider_ready = provider_report is None or provider_report["ok"]
    required_ok = all(item["ok"] for item in checks if item["required"]) and provider_ready
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
        "superpowers": superpowers,
        "selection": selection,
        "providers": provider_report.get("providers", {}) if provider_report else {},
        "capabilities": provider_report.get("capabilities", {}) if provider_report else {},
        "coreReady": provider_report.get("coreReady", required_ok) if provider_report else required_ok,
        "methodologyReady": provider_report.get("methodologyReady", True) if provider_report else True,
        "roadmapReady": provider_report.get("roadmapReady", True) if provider_report else True,
        "goalReady": provider_report.get("goalReady", True) if provider_report else True,
        "triggeredCapabilities": sorted(triggered_capabilities or set()),
        "checks": checks,
    }


def scope_provenance_requiredness(
    provenance: dict[str, Any],
    selection: dict[str, Any] | None,
    strict: bool,
) -> None:
    required = {
        "openspec-cli": True,
        "gsd-core": bool(selection and selection["effectiveRoadmapProvider"] == "gsd"),
        "superpowers": bool(
            selection and selection["effectiveMethodologyProfile"] == "strict-superpowers"
        ),
        "plugin-eval": strict,
    }
    for dependency in provenance["dependencies"]:
        dependency["required"] = required.get(dependency["name"], False)
    for check in provenance["checks"]:
        name = check["name"].removeprefix("external dependency: ")
        check["required"] = required.get(name, False)

def add_check(checks: list[dict[str, Any]], name: str, ok: bool, required: bool, detail: str = "") -> None:
    checks.append({"name": name, "ok": bool(ok), "required": bool(required), "detail": detail})


def dependency_status(required_ok: bool, recommended_ok: bool) -> str:
    if not required_ok:
        return "missing_required"
    if not recommended_ok:
        return "ready_with_recommendations"
    return "ready"
