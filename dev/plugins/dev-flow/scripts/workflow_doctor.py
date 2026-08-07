from __future__ import annotations

from pathlib import Path
from typing import Optional

from workflow_paths import render_template, repo_path
from workflow_validate import validate_workflow_state
from workflow_constants import resolve_plugin_root
from workflow_project_refresh import project_refresh_contract_snapshot
from workflow_stop_scope import stop_hook_protocol_check


def doctor_workflow(
    repo: Path,
    write_report: bool = False,
    *,
    plugin_root: Optional[Path] = None,
    codex_home: Optional[Path] = None,
    check_cache_drift: bool = False,
) -> dict[str, object]:
    repo = repo_path(repo)
    drift_plugin_root = plugin_root
    if check_cache_drift and drift_plugin_root is None:
        drift_plugin_root = resolve_plugin_root()
    validation = validate_workflow_state(
        repo,
        plugin_root=drift_plugin_root,
        codex_home=codex_home,
    )
    stop_hook_protocol = stop_hook_protocol_check()
    project_refresh = project_refresh_diagnostics(
        repo,
        plugin_root=drift_plugin_root,
        codex_home=codex_home,
    )
    issues = validation["issues"] + validation["warnings"] + stop_hook_protocol["issues"]
    recommendations = repair_recommendations(issues)
    status = (
        "healthy"
        if validation["ok"] and not validation["warnings"] and stop_hook_protocol["ok"]
        else "needs repair"
    )
    report = {
        "diagnosis": status,
        "issues": issues,
        "recommendations": recommendations,
        "validation": validation,
        "generatedArtifacts": validation["generatedArtifacts"],
        "stopHookProtocol": stop_hook_protocol,
        "projectRefresh": project_refresh,
    }
    if write_report:
        write_doctor_reports(repo, status, issues, recommendations)
    return report


def project_refresh_diagnostics(
    repo: Path,
    *,
    plugin_root: Optional[Path],
    codex_home: Optional[Path],
) -> dict[str, object]:
    source_root = repo / "dev" / "plugins" / "dev-flow"
    release_root = repo / "plugins" / "dev-flow"
    active_root = Path(plugin_root).expanduser().resolve() if plugin_root is not None else None
    cache_roots: list[Path] = []
    if codex_home is not None:
        cache_base = Path(codex_home).expanduser().resolve() / "plugins" / "cache"
        if cache_base.is_dir() and not cache_base.is_symlink():
            cache_roots = sorted(
                path.resolve()
                for path in cache_base.glob("*/dev-flow/*")
                if path.is_dir() and not path.is_symlink()
            )
    if active_root is not None and "cache" in active_root.parts and active_root not in cache_roots:
        cache_roots.append(active_root)
    source = _project_refresh_snapshot(source_root)
    release = _project_refresh_snapshot(release_root)
    active = _project_refresh_snapshot(active_root)
    caches = [_project_refresh_snapshot(path) for path in cache_roots]
    identities = [
        item.get("identity")
        for item in [source, release, active, *caches]
        if item.get("available") and item.get("ok")
    ]
    comparable = len(identities) >= 2
    identities_match = comparable and all(identity == identities[0] for identity in identities[1:])
    return {
        "status": (
            "current"
            if identities_match
            else ("drift" if comparable else "partial_or_unavailable")
        ),
        "source": source,
        "release": release,
        "active": active,
        "cache": caches,
        "identitiesMatch": identities_match if comparable else None,
        "registrationOnlySatisfiesFreshness": False,
    }


def _project_refresh_snapshot(root: Optional[Path]) -> dict[str, object]:
    if root is None:
        return {"available": False, "root": None, "ok": False, "identity": None, "errors": []}
    root = Path(root).expanduser().resolve()
    manifest = root / ".codex-plugin" / "project-migration.json"
    if manifest.is_symlink() or not manifest.is_file():
        return {
            "available": False,
            "root": str(root),
            "ok": False,
            "identity": None,
            "errors": ["refresh_manifest_missing_or_untrusted"],
        }
    snapshot = project_refresh_contract_snapshot(root)
    return {"available": True, **snapshot}


def repair_recommendations(issues: list[str]) -> list[str]:
    if not issues:
        return ["No workflow repair needed."]
    return [f"Repair: {issue}" for issue in issues] + ["Run validate_workflow_state.py after repairs."]


def write_doctor_reports(
    repo: Path,
    status: str,
    issues: list[str],
    recommendations: list[str],
) -> None:
    values = {"status": status, "issues": issues, "recommendations": recommendations}
    (repo / "workflow-diagnosis.md").write_text(render_template("DIAGNOSIS.md.template", values))
    (repo / "repair-plan.md").write_text(render_template("REPAIR_PLAN.md.template", values))
