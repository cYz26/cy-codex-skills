#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workflow_project_activation import managed_project_skills
from workflow_project_skill_paths import (
    official_project_skill_dir,
    scan_project_skill_layout,
)
from workflow_contract_control_plane import control_plane_status
from workflow_project_refresh import (
    PROJECT_REFRESH_AUTHORIZATION,
    WORKFLOW_CONFIG_AUTHORIZATION,
    apply_project_refresh,
    plan_project_refresh,
    rollback_project_refresh,
    verify_project_refresh,
)
from workflow_planning_paths import (
    append_devflow_text,
    atomic_write_devflow,
    guard_devflow_write,
    PlanningOwnershipError,
    plugin_migration_root,
)


def default_plugin_root() -> Path:
    configured = os.environ.get("DEVFLOW_PLUGIN_ROOT") or os.environ.get("PLUGIN_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[1]


def sync_project_migrations(
    repo: str | Path,
    plugin_root: str | Path,
    codex_home: str | Path | None = None,
    write_report: bool = False,
) -> dict[str, Any]:
    repo = normalize_path(repo)
    plugin_root = normalize_path(plugin_root)
    codex_home_path = normalize_path(codex_home or Path.home() / ".codex")
    plugin_root = resolve_project_source_plugin_root(repo, plugin_root)
    adapter = load_adapter(plugin_root)
    if adapter is None:
        report = base_report(repo, plugin_root, codex_home_path, "not_applicable", [])
    else:
        plugin = inspect_plugin(repo, plugin_root, adapter)
        status = plugin_report_status(plugin)
        report = base_report(repo, plugin_root, codex_home_path, status, [plugin])
    if write_report:
        write_report_file(repo, report)
    return report


def apply_project_migrations(
    repo: str | Path,
    plugin_root: str | Path,
    codex_home: str | Path | None = None,
    allow_dirty: bool = False,
) -> dict[str, Any]:
    del allow_dirty
    repo = normalize_path(repo)
    plugin_root = normalize_path(plugin_root)
    codex_home_path = normalize_path(codex_home or Path.home() / ".codex")
    plugin_root = resolve_project_source_plugin_root(repo, plugin_root)
    adapter = load_adapter(plugin_root)
    if adapter is None:
        report = base_report(repo, plugin_root, codex_home_path, "not_applicable", [])
        return report

    plugin_before = inspect_plugin(repo, plugin_root, adapter)
    refresh_plan = plan_project_refresh(repo, plugin_root, codex_home_path)
    conflicts = list(plugin_before["conflicts"])
    blocking_manual = _blocking_refresh_manual_actions(refresh_plan)
    if not refresh_plan.get("ok") or blocking_manual or conflicts:
        for item in blocking_manual:
            conflicts.append(
                {
                    "status": "conflict",
                    "reason": item.get("reason", "manual-review-required"),
                    "target": str(repo / str(item.get("path") or "")),
                    "source": None,
                    "skill": Path(str(item.get("path") or "unknown")).name,
                }
            )
        plugin_before["conflicts"] = conflicts
        report = base_report(repo, plugin_root, codex_home_path, "blocked", [plugin_before])
        report["ok"] = False
        report["refreshEngine"] = _compatibility_refresh_result(
            refresh_plan,
            status="blocked",
            ok=False,
            next_action="Resolve project ownership conflicts and produce a fresh plan.",
        )
        return report

    selected = {
        str(action["id"])
        for action in refresh_plan.get("actions", [])
        if action.get("authorization") == PROJECT_REFRESH_AUTHORIZATION
    }
    if selected:
        refresh_result = apply_project_refresh(
            repo,
            plugin_root,
            expected_plan=str(refresh_plan["planSha256"]),
            authorizations={PROJECT_REFRESH_AUTHORIZATION},
            selected_actions=selected,
            codex_home=codex_home_path,
        )
    else:
        refresh_result = _compatibility_refresh_result(
            refresh_plan,
            status=(
                "authorization_required"
                if WORKFLOW_CONFIG_AUTHORIZATION in refresh_plan.get("requiredAuthorizations", [])
                else refresh_plan.get("status", "current")
            ),
            ok=refresh_plan.get("status") == "current",
            next_action=(
                "Use the project-refresh apply command with explicit workflow-config-migration authorization."
                if WORKFLOW_CONFIG_AUTHORIZATION in refresh_plan.get("requiredAuthorizations", [])
                else str(refresh_plan.get("nextAction") or "No project migration action needed.")
            ),
        )
    if not refresh_result.get("ok"):
        plugin_before["conflicts"] = conflicts
        report = base_report(repo, plugin_root, codex_home_path, "blocked", [plugin_before])
        report["ok"] = False
        report["refreshEngine"] = refresh_result
        return report

    plugin = inspect_plugin(repo, plugin_root, adapter)
    changes = _legacy_changes_from_refresh(repo, refresh_plan, selected)
    plugin["changes"] = changes
    plugin["conflicts"] = []
    plugin["staleProjectSkills"] = []
    plugin["missingProjectSkills"] = []
    status = "applied"
    report = base_report(repo, plugin_root, codex_home_path, status, [plugin])
    report["ok"] = True
    report["refreshEngine"] = refresh_result
    write_report_file(repo, report)
    append_history(repo, plugin["name"], status, changes, [])
    return report


def _blocking_refresh_manual_actions(plan: dict[str, Any]) -> list[dict[str, Any]]:
    blocking_reasons = {
        "target_exists_not_symlink",
        "managed_file_ownership_ambiguous",
        "candidate_ownership_ambiguous",
        "candidate_content_conflict",
        "missing_or_untrusted_source",
        "missing_or_untrusted_template",
    }
    return [
        item
        for item in plan.get("manualActions", [])
        if isinstance(item, dict) and item.get("reason") in blocking_reasons
    ]


def _compatibility_refresh_result(
    plan: dict[str, Any],
    *,
    status: str,
    ok: bool,
    next_action: str,
) -> dict[str, Any]:
    return {
        "schemaVersion": "1.0",
        "kind": "devflow-project-refresh-result",
        "ok": ok,
        "status": status,
        "repo": plan.get("repo"),
        "planSha256": plan.get("planSha256"),
        "changedPaths": [],
        "preservedPaths": list(plan.get("preservedPaths", [])),
        "rollbackStatus": "not_started",
        "receiptPath": None,
        "retryability": str(plan.get("retryability") or "after_remediation"),
        "remainingAuthorizations": sorted(
            set(map(str, plan.get("requiredAuthorizations", [])))
        ),
        "manualActions": list(plan.get("manualActions", [])),
        "nextAction": next_action,
    }


def _legacy_changes_from_refresh(
    repo: Path,
    plan: dict[str, Any],
    selected: set[str],
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for action in plan.get("actions", []):
        if str(action.get("id")) not in selected:
            continue
        relative = str(action.get("path") or "")
        if action.get("kind") in {"create_symlink", "replace_symlink"}:
            source = action.get("source") if isinstance(action.get("source"), dict) else {}
            changes.append(
                {
                    "kind": "project-local-skill",
                    "skill": Path(relative).name,
                    "target": str(repo / relative),
                    "source": str(source.get("target") or ""),
                    "pathKind": "official_repo_skill_path",
                }
            )
        elif str(action.get("id", "")).startswith("create-control-plane:"):
            changes.append(
                {
                    "kind": "control-plane-file",
                    "path": relative,
                    "template": Path(str(action.get("source", {}).get("path") or "")).name,
                }
            )
        elif action.get("id") == "create-agents-merge-candidate":
            changes.append({"kind": "agents-merge-candidate", "path": relative})
    return changes


def project_migration_sync_result(
    repo: str | Path,
    plugin_root: str | Path,
    codex_home: str | Path | None = None,
) -> dict[str, Any]:
    report = sync_project_migrations(repo, plugin_root, codex_home)
    plugin = report["plugins"][0] if report["plugins"] else {"name": "none"}
    status = report["status"].replace("_", "-")
    skill_layout = plugin.get("skillLayout", {}) if isinstance(plugin, dict) else {}
    layout_status = skill_layout.get("status")
    if layout_status in {"legacy_detected", "legacy_duplicate", "skill_layout_conflict"}:
        command = " ".join(skill_layout.get("dryRunCommand", []))
        detail = f"legacy skill layout {layout_status.replace('_', '-')}; run dry-run migration first: {command}"
    elif status == "migration-pending":
        detail = f"project migration drift detected; run plugin-project-migration for {plugin['name']}"
    elif status == "blocked":
        plugin_conflicts = [
            str(item.get("reason") or item)
            for item in plugin.get("conflicts", [])
        ]
        reasons = [str(item) for item in plugin_conflicts]
        detail = "project migration is blocked; resolve: " + (
            "; ".join(reasons[:5]) if reasons else "manual review required"
        )
    elif status == "not-applicable":
        detail = "plugin has no project migration adapter"
    else:
        detail = "project migration state is current"
    return {
        "kind": "project-migration-sync",
        "name": plugin["name"],
        "status": status,
        "detail": detail,
        "repo": str(normalize_path(repo)),
        "skillLayoutStatus": layout_status,
        "skillLayoutDryRunCommand": skill_layout.get("dryRunCommand"),
    }


def migration_reminder(repo: str | Path, plugin_root: str | Path, codex_home: str | Path | None = None) -> str:
    result = project_migration_sync_result(repo, plugin_root, codex_home)
    if result["status"] != "migration-pending":
        return ""
    return f"DevFlow: {result['detail']}."


def inspect_plugin(repo: Path, plugin_root: Path, adapter: dict[str, Any]) -> dict[str, Any]:
    manifest = read_json(plugin_root / ".codex-plugin" / "plugin.json")
    state = read_state(repo)
    plugin_name = str(adapter.get("plugin") or manifest.get("name") or plugin_root.name)
    plugin_state = state.get("plugins", {}).get(plugin_name)
    stale: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for skill in adapter.get("projectLocalSkills", []):
        source = preferred_project_skill_source(repo, plugin_root, plugin_name, skill)
        accepted_sources = project_skill_sources(repo, plugin_root, plugin_name, skill)
        target = official_project_skill_dir(repo, skill)
        if target.is_symlink():
            if not target_matches_any_source(target, accepted_sources):
                stale.append(skill_record(skill, target, source, "stale-link"))
        elif target.exists():
            conflicts.append(conflict(skill, target, source, "target-exists-not-symlink"))
        else:
            missing.append(skill_record(skill, target, source, "missing-target"))
    runtime_version = str(manifest.get("version") or "unknown")
    stored_version = plugin_state.get("version") if isinstance(plugin_state, dict) else None
    return {
        "name": plugin_name,
        "runtimeVersion": runtime_version,
        "storedVersion": stored_version,
        "state": "missing" if plugin_state is None else "present",
        "pendingVersion": stored_version != runtime_version,
        "staleProjectSkills": stale,
        "missingProjectSkills": missing,
        "conflicts": conflicts,
        "skillLayout": scan_project_skill_layout(
            repo,
            migration_skill_layout_scope(adapter),
            script_path=Path(__file__).with_name("activate_project_dependencies.py"),
        ),
        "changes": [],
        "controlPlane": control_plane_status(repo),
    }


def migration_skill_layout_scope(adapter: dict[str, Any]) -> list[str]:
    return sorted({*adapter.get("projectLocalSkills", []), *managed_project_skills()})


def preferred_project_skill_source(repo: Path, plugin_root: Path, plugin_name: str, skill: str) -> Path:
    dev_root = source_repo_dev_plugin_root(repo, plugin_root, plugin_name)
    if dev_root is not None:
        dev_source = dev_root / "skills" / skill
        if (dev_source / "SKILL.md").exists():
            return dev_source
    return plugin_root / "skills" / skill


def project_skill_sources(repo: Path, plugin_root: Path, plugin_name: str, skill: str) -> list[Path]:
    sources = [plugin_root / "skills" / skill]
    dev_root = source_repo_dev_plugin_root(repo, plugin_root, plugin_name)
    if dev_root is not None:
        dev_source = dev_root / "skills" / skill
        if (dev_source / "SKILL.md").exists():
            sources.append(dev_source)
    return sources


def source_repo_dev_plugin_root(repo: Path, plugin_root: Path, plugin_name: str) -> Path | None:
    release_root = (repo / "plugins" / plugin_name).resolve()
    if plugin_root.resolve() != release_root:
        return None
    candidate = (repo / "dev" / "plugins" / plugin_name).resolve()
    if candidate == release_root:
        return None
    candidate_manifest = candidate / ".codex-plugin" / "plugin.json"
    candidate_adapter = candidate / ".codex-plugin" / "project-migration.json"
    if not candidate_manifest.exists() or not candidate_adapter.exists():
        return None
    try:
        candidate_name = str(read_json(candidate_manifest).get("name") or candidate.name)
    except json.JSONDecodeError:
        return None
    return candidate if candidate_name == plugin_name else None


def target_matches_any_source(target: Path, sources: list[Path]) -> bool:
    resolved = target.resolve()
    return any(resolved == source.resolve() for source in sources)


def plugin_report_status(plugin: dict[str, Any]) -> str:
    if (
        plugin["state"] == "missing"
        or plugin["pendingVersion"]
        or plugin["staleProjectSkills"]
        or plugin["missingProjectSkills"]
        or plugin["conflicts"]
        or plugin.get("controlPlane", {}).get("status") != "current"
        or plugin.get("skillLayout", {}).get("status") != "current"
    ):
        return "migration_pending"
    return "current"


def load_adapter(plugin_root: Path) -> dict[str, Any] | None:
    path = plugin_root / ".codex-plugin" / "project-migration.json"
    if not path.exists():
        return None
    data = read_json(path)
    if not data.get("plugin"):
        manifest = read_json(plugin_root / ".codex-plugin" / "plugin.json")
        data["plugin"] = manifest.get("name", plugin_root.name)
    data.setdefault("projectLocalSkills", [])
    data.setdefault("managedFiles", [])
    return data


def resolve_project_source_plugin_root(repo: Path, plugin_root: Path) -> Path:
    manifest = read_json(plugin_root / ".codex-plugin" / "plugin.json")
    plugin_name = str(manifest.get("name") or plugin_root.name)
    candidate = marketplace_plugin_root(repo, plugin_name)
    if candidate is None:
        return plugin_root
    candidate_manifest = candidate / ".codex-plugin" / "plugin.json"
    candidate_adapter = candidate / ".codex-plugin" / "project-migration.json"
    if not candidate_manifest.exists() or not candidate_adapter.exists():
        return plugin_root
    try:
        candidate_name = str(read_json(candidate_manifest).get("name") or candidate.name)
    except json.JSONDecodeError:
        return plugin_root
    return candidate if candidate_name == plugin_name else plugin_root


def marketplace_plugin_root(repo: Path, plugin_name: str) -> Path | None:
    for marketplace in (repo / ".agents" / "plugins").glob("marketplace*.json"):
        try:
            data = read_json(marketplace)
        except (OSError, json.JSONDecodeError):
            continue
        for record in data.get("plugins", []):
            if record.get("name") != plugin_name:
                continue
            raw_path = marketplace_record_path(record)
            if not raw_path:
                continue
            for candidate in resolve_marketplace_path(repo, marketplace, raw_path):
                if (candidate / ".codex-plugin" / "plugin.json").exists():
                    return candidate
    return None


def marketplace_record_path(record: dict[str, Any]) -> str | None:
    source = record.get("source")
    if isinstance(source, dict) and source.get("path"):
        return str(source["path"])
    if record.get("path"):
        return str(record["path"])
    return None


def resolve_marketplace_path(repo: Path, marketplace: Path, raw_path: str) -> list[Path]:
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return [path.resolve()]
    return [(repo / path).resolve(), (marketplace.parent / path).resolve()]


def read_state(repo: Path) -> dict[str, Any]:
    path = runtime_root(repo) / "state.json"
    guard_devflow_write(repo, path)
    if not path.exists():
        return {"schemaVersion": "1.0", "plugins": {}}
    try:
        return read_json(path)
    except json.JSONDecodeError:
        return {"schemaVersion": "1.0", "plugins": {}}


def write_report_file(repo: Path, report: dict[str, Any]) -> None:
    write_json(repo, runtime_root(repo) / "reports" / "latest.json", report)


def append_history(
    repo: Path,
    plugin: str,
    status: str,
    changes: list[dict[str, Any]],
    conflicts: list[dict[str, Any]] | None = None,
) -> None:
    path = runtime_root(repo) / "migration-history.jsonl"
    record = {
        "timestamp": now_iso(),
        "plugin": plugin,
        "status": status,
        "changes": changes,
        "conflicts": conflicts or [],
    }
    append_devflow_text(repo, path, json.dumps(record, sort_keys=True) + "\n")


def base_report(
    repo: Path,
    plugin_root: Path,
    codex_home: Path,
    status: str,
    plugins: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "ok": status not in {"blocked"},
        "status": status,
        "repo": str(repo),
        "pluginRoot": str(plugin_root),
        "codexHome": str(codex_home),
        "checkedAt": now_iso(),
        "plugins": plugins,
        "recommendation": recommendation(status, plugins),
    }


def recommendation(status: str, plugins: list[dict[str, Any]] | None = None) -> str:
    if status == "migration_pending":
        for plugin in plugins or []:
            layout = plugin.get("skillLayout", {})
            if layout.get("status") in {"legacy_detected", "legacy_duplicate", "skill_layout_conflict"}:
                return "Run the official skill-layout dry-run migration after reviewing the sync report: " + " ".join(
                    layout.get("dryRunCommand", [])
                )
        return "Run plugin-project-migration migrate after reviewing the sync report."
    if status == "blocked":
        return "Resolve conflicts, then rerun plugin-project-migration migrate."
    return "No project migration action needed."


def skill_record(skill: str, target: Path, source: Path, status: str) -> dict[str, Any]:
    return {"skill": skill, "status": status, "target": str(target), "source": str(source)}


def conflict(skill: str, target: Path, source: Path, reason: str) -> dict[str, Any]:
    payload = skill_record(skill, target, source, "conflict")
    payload["reason"] = reason
    return payload


def runtime_root(repo: Path) -> Path:
    return plugin_migration_root(repo)


def normalize_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def write_json(repo: Path, path: Path, payload: dict[str, Any]) -> None:
    atomic_write_devflow(repo, path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _add_common_arguments(parser: argparse.ArgumentParser, *, defaults: bool) -> None:
    default = None if defaults else argparse.SUPPRESS
    parser.add_argument("--repo", default="." if defaults else default)
    parser.add_argument("--plugin-root", default=default_plugin_root() if defaults else default)
    parser.add_argument("--codex-home", default=Path.home() / ".codex" if defaults else default)
    parser.add_argument("--json", action="store_true", default=False if defaults else default)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect, plan, apply, verify, or roll back one DevFlow project refresh."
    )
    _add_common_arguments(parser, defaults=True)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--apply", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    subparsers = parser.add_subparsers(dest="command")

    plan_parser = subparsers.add_parser("plan", help="Produce a deterministic read-only refresh plan.")
    _add_common_arguments(plan_parser, defaults=False)

    apply_parser = subparsers.add_parser("apply", help="Apply an explicitly authorized sealed plan.")
    _add_common_arguments(apply_parser, defaults=False)
    apply_parser.add_argument("--expect-plan", "--plan-sha256", dest="plan_sha256", required=True)
    apply_parser.add_argument("--allow", "--authorize", dest="authorize", action="append", default=[])
    apply_parser.add_argument("--action", action="append", default=None)

    verify_parser = subparsers.add_parser("verify", help="Verify a successful apply receipt afresh.")
    _add_common_arguments(verify_parser, defaults=False)
    verify_parser.add_argument("--receipt", required=True)

    rollback_parser = subparsers.add_parser("rollback", help="Plan or explicitly apply receipt-bound rollback.")
    _add_common_arguments(rollback_parser, defaults=False)
    rollback_parser.add_argument("--receipt", required=True)
    rollback_parser.add_argument("--apply", action="store_true", dest="rollback_apply")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "plan":
            report = plan_project_refresh(args.repo, args.plugin_root, args.codex_home)
        elif args.command == "apply":
            report = apply_project_refresh(
                args.repo,
                args.plugin_root,
                expected_plan=args.plan_sha256,
                authorizations=set(args.authorize),
                selected_actions=set(args.action) if args.action is not None else None,
                codex_home=args.codex_home,
            )
        elif args.command == "verify":
            report = verify_project_refresh(
                args.repo,
                args.plugin_root,
                args.receipt,
                codex_home=args.codex_home,
            )
        elif args.command == "rollback":
            report = rollback_project_refresh(
                args.repo,
                args.plugin_root,
                args.receipt,
                apply=args.rollback_apply,
            )
        elif args.apply:
            report = apply_project_migrations(args.repo, args.plugin_root, args.codex_home)
        else:
            report = sync_project_migrations(
                args.repo,
                args.plugin_root,
                args.codex_home,
                args.write_report,
            )
    except Exception as error:
        expected = isinstance(
            error,
            (OSError, ValueError, json.JSONDecodeError, PlanningOwnershipError),
        )
        report = {
            "schemaVersion": "1.0",
            "kind": "devflow-project-refresh-result",
            "ok": False,
            "status": "invalid_request" if expected else "internal_failure",
            "repo": str(Path(args.repo).expanduser().resolve()),
            "changedPaths": [],
            "preservedPaths": [],
            "rollbackStatus": "not_started",
            "receiptPath": None,
            "retryability": "after_correction" if expected else "after_repair",
            "errorType": type(error).__name__,
            "nextAction": (
                "Correct the request or trusted path and retry."
                if expected
                else "Inspect the internal failure before retrying."
            ),
        }
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        detail = report.get("nextAction") or report.get("recommendation") or "No next action recorded."
        print(f"{report['status']}: {detail}")
    if args.command is None:
        return 0 if report["ok"] else 1
    return project_refresh_exit_code(report)


def project_refresh_exit_code(report: dict[str, Any]) -> int:
    status = str(report.get("status") or "internal_error")
    if status in {"current", "not_applicable", "applied_and_verified", "verified", "rolled_back"}:
        return 0
    if status in {
        "migration_pending",
        "authorization_required",
        "manual_review_required",
        "baseline_ambiguous",
        "applied_incomplete",
        "verified_incomplete",
        "rollback_blocked",
    }:
        return 2
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
