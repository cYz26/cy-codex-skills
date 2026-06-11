#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUNTIME_DIR = ".dev-flow/plugin-project-migration"


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
        write_report_file(repo, report)
        append_history(repo, "none", "not_applicable", [])
        return report

    plugin = inspect_plugin(repo, plugin_root, adapter)
    conflicts = list(plugin["conflicts"])
    changes: list[dict[str, Any]] = []
    for skill in adapter.get("projectLocalSkills", []):
        source = plugin_root / "skills" / skill
        target = repo / ".codex" / "skills" / skill
        if not (source / "SKILL.md").exists():
            conflicts.append(conflict(skill, target, source, "missing-source"))
            continue
        if target.exists() and not target.is_symlink():
            conflicts.append(conflict(skill, target, source, "target-exists-not-symlink"))
            continue
        if target.is_symlink() and target.resolve() == source.resolve():
            continue
        if target.is_symlink():
            target.unlink()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source, target_is_directory=True)
        changes.append({"kind": "project-local-skill", "skill": skill, "target": str(target), "source": str(source)})

    plugin["conflicts"] = conflicts
    plugin["changes"] = changes
    plugin["staleProjectSkills"] = []
    plugin["missingProjectSkills"] = []
    if conflicts:
        status = "blocked"
        ok = False
    else:
        status = "applied"
        ok = True
        update_state(repo, adapter, plugin)

    report = base_report(repo, plugin_root, codex_home_path, status, [plugin])
    report["ok"] = ok
    write_report_file(repo, report)
    append_history(repo, plugin["name"], status, changes, conflicts)
    return report


def project_migration_sync_result(
    repo: str | Path,
    plugin_root: str | Path,
    codex_home: str | Path | None = None,
) -> dict[str, Any]:
    report = sync_project_migrations(repo, plugin_root, codex_home)
    plugin = report["plugins"][0] if report["plugins"] else {"name": "none"}
    status = report["status"].replace("_", "-")
    if status == "migration-pending":
        detail = f"project migration drift detected; run plugin-project-migration for {plugin['name']}"
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
        source = plugin_root / "skills" / skill
        target = repo / ".codex" / "skills" / skill
        if target.is_symlink():
            if target.resolve() != source.resolve():
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
        "changes": [],
    }


def plugin_report_status(plugin: dict[str, Any]) -> str:
    if (
        plugin["state"] == "missing"
        or plugin["pendingVersion"]
        or plugin["staleProjectSkills"]
        or plugin["missingProjectSkills"]
        or plugin["conflicts"]
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
    if not path.exists():
        return {"schemaVersion": "1.0", "plugins": {}}
    try:
        return read_json(path)
    except json.JSONDecodeError:
        return {"schemaVersion": "1.0", "plugins": {}}


def update_state(repo: Path, adapter: dict[str, Any], plugin: dict[str, Any]) -> None:
    state = read_state(repo)
    state.setdefault("schemaVersion", "1.0")
    state.setdefault("plugins", {})
    state["plugins"][plugin["name"]] = {
        "version": plugin["runtimeVersion"],
        "lastSyncedAt": now_iso(),
        "projectLocalSkills": list(adapter.get("projectLocalSkills", [])),
        "managedFiles": list(adapter.get("managedFiles", [])),
    }
    write_json(runtime_root(repo) / "state.json", state)


def write_report_file(repo: Path, report: dict[str, Any]) -> None:
    write_json(runtime_root(repo) / "reports" / "latest.json", report)


def append_history(
    repo: Path,
    plugin: str,
    status: str,
    changes: list[dict[str, Any]],
    conflicts: list[dict[str, Any]] | None = None,
) -> None:
    path = runtime_root(repo) / "migration-history.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": now_iso(),
        "plugin": plugin,
        "status": status,
        "changes": changes,
        "conflicts": conflicts or [],
    }
    with path.open("a") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


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
        "recommendation": recommendation(status),
    }


def recommendation(status: str) -> str:
    if status == "migration_pending":
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
    return repo / RUNTIME_DIR


def normalize_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync or apply Codex plugin project migrations.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--plugin-root", default=default_plugin_root())
    parser.add_argument("--codex-home", default=Path.home() / ".codex")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.apply:
        report = apply_project_migrations(args.repo, args.plugin_root, args.codex_home)
    else:
        report = sync_project_migrations(args.repo, args.plugin_root, args.codex_home, args.write_report)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"{report['status']}: {report['recommendation']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
