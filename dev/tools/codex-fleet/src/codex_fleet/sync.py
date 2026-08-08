from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .core import (
    FleetError,
    KNOWN_ADAPTERS,
    PROJECT_ID_PATTERN,
    SCHEMA_VERSION,
    ProjectCandidate,
    digest_value,
    read_trusted_bytes,
    runtime_inventory,
    tree_digest,
    trusted_path,
)


def plan_sync(
    *,
    manifest_path: Path,
    lock_path: Path,
    device_path: Path,
    codex_home: Path,
    advance_lock: bool,
) -> dict[str, Any]:
    manifest, manifest_bytes = _read_json(manifest_path, "manifest")
    lock, lock_bytes = _read_json(lock_path, "lock")
    device, device_bytes = _read_json(device_path, "device overlay")
    profile = _validate_profile(manifest, lock, device, codex_home)

    runtime = runtime_inventory(codex_home=codex_home)
    runtime_marketplaces = {item["name"]: item for item in runtime["marketplaces"]}
    blockers: list[dict[str, Any]] = []
    source_identities: dict[str, dict[str, Any]] = {}
    marker_bindings: dict[str, str] = {}

    for marketplace in profile["marketplaces"]:
        name = marketplace["name"]
        observed = runtime_marketplaces.get(name)
        if observed is None:
            blockers.append(_blocker("marketplace_missing", name, "configured marketplace is missing"))
            continue
        expected_source = _resolve_marketplace_source(marketplace, profile["deviceMarketplaces"])
        if observed["sourceType"] != marketplace["sourceType"] or observed["source"] != expected_source:
            blockers.append(
                _blocker(
                    "marketplace_source_mismatch",
                    name,
                    "configured marketplace source does not match the managed profile",
                    expected={"sourceType": marketplace["sourceType"], "source": expected_source},
                    actual={"sourceType": observed["sourceType"], "source": observed["source"]},
                )
            )
            continue
        if marketplace["sourceType"] == "git" and observed.get("ref") != marketplace.get("ref"):
            blockers.append(
                _blocker(
                    "marketplace_ref_mismatch",
                    name,
                    "configured marketplace ref does not match the managed profile",
                    expected=marketplace.get("ref"),
                    actual=observed.get("ref"),
                )
            )
            continue
        locked_marketplace = lock["marketplaces"][name]
        current_marketplace_identity = _marketplace_identity(observed, marketplace)
        source_identities[f"marketplace:{name}"] = current_marketplace_identity
        if not advance_lock and current_marketplace_identity != locked_marketplace:
            blockers.append(
                _blocker(
                    "locked_marketplace_drift",
                    name,
                    "current marketplace identity differs from the portable lock",
                    expected=locked_marketplace,
                    actual=current_marketplace_identity,
                )
            )

    for plugin in profile["plugins"]:
        selector = plugin["selector"]
        marketplace = runtime_marketplaces.get(plugin["marketplace"])
        if marketplace is None:
            continue
        try:
            source = _plugin_source(Path(marketplace["root"]), plugin["name"])
            identity = _plugin_source_identity(source)
        except FleetError as error:
            blockers.append(_blocker(error.status, selector, str(error)))
            continue
        source_identities[f"plugin:{selector}"] = identity
        if not advance_lock and identity != lock["plugins"][selector]:
            blockers.append(
                _blocker(
                    "locked_plugin_source_drift",
                    selector,
                    "marketplace plugin source differs from the portable lock",
                    expected=lock["plugins"][selector],
                    actual=identity,
                )
            )

    eligible_projects: list[dict[str, Any]] = []
    for project in profile["projects"]:
        project_id = project["id"]
        binding = profile["deviceProjects"][project_id]
        project_path = Path(binding["path"])
        marker_path = project_path / ".codex-fleet" / "project.json"
        try:
            marker, marker_bytes = _read_json(marker_path, f"project marker {project_id}")
            _validate_project_marker(marker, project, profile["profile"])
        except FleetError as error:
            blockers.append(_blocker("project_adoption_mismatch", project_id, str(error)))
            continue
        marker_bindings[project_id] = _bytes_digest(marker_bytes)
        eligible_projects.append({**project, "path": str(project_path), "marker": str(marker_path)})

    actions = _plan_actions(profile, eligible_projects, advance_lock=advance_lock)
    if blockers:
        actions = [item for item in actions if not item["kind"].startswith("project-")]
        actions = [item for item in actions if item["kind"] != "lock-promote"]

    plan: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "kind": "codex-fleet-plan",
        "ok": not blockers,
        "status": "planned" if not blockers else "blocked",
        "apply": False,
        "advanceLock": advance_lock,
        "profile": profile["profile"],
        "paths": {
            "manifest": str(manifest_path),
            "lock": str(lock_path),
            "device": str(device_path),
            "codexHome": str(codex_home),
        },
        "bindings": {
            "manifest": _bytes_digest(manifest_bytes),
            "lock": _bytes_digest(lock_bytes),
            "device": _bytes_digest(device_bytes),
            "runtime": digest_value(runtime),
            "projectMarkers": marker_bindings,
            "projectPaths": {
                project["id"]: project["path"] for project in eligible_projects
            },
            "sourceIdentities": source_identities,
        },
        "actions": actions,
        "results": [],
        "blockers": blockers,
        "nextAction": (
            "Repeat this command with --apply to execute the sealed in-process plan."
            if not blockers
            else "Correct every blocker and create a fresh plan before applying."
        ),
    }
    plan["planSha256"] = digest_value(plan)
    return plan


def _validate_profile(
    manifest: dict[str, Any],
    lock: dict[str, Any],
    device: dict[str, Any],
    codex_home: Path,
) -> dict[str, Any]:
    for label, value in (("manifest", manifest), ("lock", lock), ("device overlay", device)):
        if value.get("schemaVersion") != SCHEMA_VERSION:
            raise FleetError(f"unsupported {label} schema", status="invalid_profile")
    profile_name = manifest.get("profile")
    if not isinstance(profile_name, str) or not profile_name:
        raise FleetError("manifest profile is missing", status="invalid_profile")
    if device.get("profile") != profile_name:
        raise FleetError("device overlay profile does not match manifest", status="invalid_profile")
    manifest_sha = digest_value(manifest)
    if lock.get("manifestSha256") != manifest_sha or device.get("manifestSha256") != manifest_sha:
        raise FleetError("manifest identity does not match lock and device overlay", status="invalid_profile")
    selected_home = trusted_path(
        Path(str(device.get("codexHome") or "")),
        label="device Codex home",
    )
    if selected_home != codex_home:
        raise FleetError("selected Codex home does not match device overlay", status="invalid_profile")

    marketplaces = manifest.get("marketplaces")
    plugins = manifest.get("plugins")
    projects = manifest.get("projects")
    device_marketplaces = device.get("marketplaces", {})
    device_projects = device.get("projects", {})
    lock_marketplaces = lock.get("marketplaces")
    lock_plugins = lock.get("plugins")
    if not isinstance(marketplaces, list) or not isinstance(plugins, list) or not isinstance(projects, list):
        raise FleetError("manifest collections must be lists", status="invalid_profile")
    if not all(isinstance(value, dict) for value in (device_marketplaces, device_projects, lock_marketplaces, lock_plugins)):
        raise FleetError("lock or device collections have an unsupported shape", status="invalid_profile")
    _unique(marketplaces, "name", "marketplace")
    _unique(plugins, "selector", "plugin selector")
    _unique(projects, "id", "project id")
    marketplace_names = {str(item.get("name")) for item in marketplaces}
    if set(lock_marketplaces) != marketplace_names:
        raise FleetError("lock marketplace identities do not match manifest", status="invalid_profile")
    normalized_marketplaces: list[dict[str, Any]] = []
    for item in marketplaces:
        name = item.get("name")
        source_type = item.get("sourceType")
        source = item.get("source")
        channel = item.get("channel")
        if not all(isinstance(value, str) and value for value in (name, source_type, source, channel)):
            raise FleetError("marketplace record is incomplete", status="invalid_profile")
        if source_type not in {"local", "git"} or channel not in {"device-local", "stable", "development"}:
            raise FleetError(f"marketplace policy is invalid: {name}", status="invalid_profile")
        if source_type == "local" and source != f"device://{name}":
            raise FleetError(f"local marketplace must use its device URI: {name}", status="invalid_profile")
        if source_type == "git" and not (
            isinstance(item.get("ref"), str) and item["ref"]
        ):
            raise FleetError(f"Git marketplace ref is missing: {name}", status="invalid_profile")
        if channel == "stable" and item.get("ref") == "main":
            raise FleetError(f"stable marketplace cannot target main: {name}", status="invalid_profile")
        locked_marketplace = lock_marketplaces[name]
        if not isinstance(locked_marketplace, dict):
            raise FleetError(f"marketplace lock is invalid: {name}", status="invalid_profile")
        if source_type == "git" and not isinstance(locked_marketplace.get("revision"), str):
            raise FleetError(f"Git marketplace lock has no revision: {name}", status="invalid_profile")
        if source_type == "local" and not isinstance(
            locked_marketplace.get("treeSha256"), str
        ):
            raise FleetError(f"local marketplace lock has no tree identity: {name}", status="invalid_profile")
        normalized_marketplaces.append(dict(item))

    local_marketplace_names = {
        item["name"] for item in normalized_marketplaces if item["sourceType"] == "local"
    }
    if set(device_marketplaces) != local_marketplace_names:
        raise FleetError(
            "device marketplace mappings do not match local manifest sources",
            status="invalid_profile",
        )
    for marketplace in normalized_marketplaces:
        if marketplace["sourceType"] == "local":
            _resolve_marketplace_source(marketplace, device_marketplaces)

    normalized_plugins: list[dict[str, Any]] = []
    for item in plugins:
        selector = item.get("selector")
        if not isinstance(selector, str) or selector.count("@") != 1:
            raise FleetError("plugin selector is invalid", status="invalid_profile")
        name, marketplace = selector.rsplit("@", 1)
        if not name or not marketplace:
            raise FleetError("plugin selector is invalid", status="invalid_profile")
        if marketplace not in marketplace_names or item.get("enabled") is not True:
            raise FleetError(f"plugin is not enabled in a managed marketplace: {selector}", status="invalid_profile")
        adapter = item.get("projectAdapter")
        if adapter is not None and adapter not in KNOWN_ADAPTERS:
            raise FleetError(f"unknown project adapter: {adapter}", status="invalid_profile")
        if selector not in lock_plugins:
            raise FleetError(f"plugin is missing from lock: {selector}", status="invalid_profile")
        locked_plugin = lock_plugins[selector]
        if not isinstance(locked_plugin, dict) or not all(
            isinstance(locked_plugin.get(name), str) and locked_plugin[name]
            for name in ("version", "treeSha256")
        ):
            raise FleetError(f"plugin lock is invalid: {selector}", status="invalid_profile")
        normalized_plugins.append(
            {**item, "name": name, "marketplace": marketplace, "projectAdapter": adapter}
        )

    plugin_by_selector = {item["selector"]: item for item in normalized_plugins}
    if set(lock_plugins) != set(plugin_by_selector):
        raise FleetError("lock plugin identities do not match manifest", status="invalid_profile")
    normalized_projects: list[dict[str, Any]] = []
    for item in projects:
        project_id = item.get("id")
        selected_plugins = item.get("plugins")
        if not isinstance(project_id, str) or not PROJECT_ID_PATTERN.fullmatch(project_id):
            raise FleetError("project id is invalid", status="invalid_profile")
        if (
            not isinstance(selected_plugins, list)
            or not all(isinstance(selector, str) and selector for selector in selected_plugins)
            or len(set(selected_plugins)) != len(selected_plugins)
        ):
            raise FleetError(f"project plugin list is invalid: {project_id}", status="invalid_profile")
        unknown = sorted(set(selected_plugins).difference(plugin_by_selector))
        if unknown:
            raise FleetError(f"project references unknown plugins: {project_id}", status="invalid_profile")
        binding = device_projects.get(project_id)
        if not isinstance(binding, dict) or binding.get("trusted") is not True:
            raise FleetError(f"project is not trusted on this device: {project_id}", status="invalid_profile")
        raw_path = binding.get("path")
        if not isinstance(raw_path, str) or not Path(raw_path).is_absolute():
            raise FleetError(f"project path must be absolute: {project_id}", status="invalid_profile")
        resolved_path = trusted_path(Path(raw_path), label=f"project path for {project_id}")
        if not resolved_path.is_dir():
            raise FleetError(f"project path is unavailable: {project_id}", status="invalid_profile")
        binding["path"] = str(resolved_path)
        normalized_projects.append({"id": project_id, "plugins": sorted(selected_plugins)})

    if set(device_projects) != {item["id"] for item in normalized_projects}:
        raise FleetError("device project mappings do not match manifest", status="invalid_profile")

    return {
        "profile": profile_name,
        "marketplaces": sorted(normalized_marketplaces, key=lambda item: item["name"]),
        "plugins": sorted(normalized_plugins, key=lambda item: item["selector"]),
        "projects": sorted(normalized_projects, key=lambda item: item["id"]),
        "deviceMarketplaces": device_marketplaces,
        "deviceProjects": device_projects,
    }


def _resolve_marketplace_source(
    marketplace: dict[str, Any], device_marketplaces: dict[str, Any]
) -> str:
    if marketplace["sourceType"] == "git":
        return marketplace["source"]
    binding = device_marketplaces.get(marketplace["name"])
    if not isinstance(binding, dict) or binding.get("trusted") is not True:
        raise FleetError(
            f"local marketplace is not trusted on this device: {marketplace['name']}",
            status="invalid_profile",
        )
    source = binding.get("source")
    if not isinstance(source, str) or not Path(source).is_absolute():
        raise FleetError(
            f"local marketplace source must be absolute: {marketplace['name']}",
            status="invalid_profile",
        )
    return str(trusted_path(Path(source), label=f"local marketplace source {marketplace['name']}"))


def _marketplace_identity(observed: dict[str, Any], desired: dict[str, Any]) -> dict[str, Any]:
    identity: dict[str, Any] = {
        "sourceType": desired["sourceType"],
        "source": desired["source"],
    }
    if desired["sourceType"] == "git":
        identity["ref"] = desired["ref"]
        revision = observed.get("revision")
        if not isinstance(revision, str) or not revision:
            raise FleetError(
                f"Git marketplace revision is unavailable: {desired['name']}",
                status="identity_unavailable",
            )
        identity["revision"] = revision
    else:
        identity["treeSha256"] = tree_digest(Path(observed["root"]))
    return identity


def _plugin_source(root: Path, plugin_name: str) -> Path:
    root = trusted_path(
        root,
        label=f"marketplace root for {plugin_name}",
        status="identity_unavailable",
    )
    candidates: list[Path] = []
    root_manifest = root / ".codex-plugin" / "plugin.json"
    if root_manifest.is_file():
        candidates.append(root)
    catalog = root / ".agents" / "plugins" / "marketplace.json"
    if catalog.exists() or catalog.is_symlink():
        try:
            payload = json.loads(
                read_trusted_bytes(
                    catalog,
                    label="marketplace catalog",
                    status="identity_unavailable",
                )
            )
        except FleetError:
            raise
        except json.JSONDecodeError as error:
            raise FleetError(f"marketplace catalog is invalid: {catalog}", status="identity_unavailable") from error
        if not isinstance(payload, dict):
            raise FleetError(
                f"marketplace catalog must contain a JSON object: {catalog}",
                status="identity_unavailable",
            )
        catalog_plugins = payload.get("plugins", [])
        if not isinstance(catalog_plugins, list):
            raise FleetError(
                f"marketplace catalog plugins must be a JSON array: {catalog}",
                status="identity_unavailable",
            )
        for record in catalog_plugins:
            if not isinstance(record, dict):
                raise FleetError(
                    f"marketplace catalog plugin record must be a JSON object: {catalog}",
                    status="identity_unavailable",
                )
            if record.get("name") != plugin_name:
                continue
            source = record.get("source")
            relative = source.get("path") if isinstance(source, dict) else None
            if isinstance(relative, str):
                candidate = trusted_path(
                    root / relative,
                    label=f"marketplace plugin source {plugin_name}",
                    status="identity_unavailable",
                )
                if not candidate.is_relative_to(root):
                    raise FleetError(
                        f"marketplace plugin path escapes its root: {plugin_name}",
                        status="identity_unavailable",
                    )
                candidates.append(candidate)
    candidates.extend([root / "plugins" / plugin_name, root / plugin_name])
    seen: set[str] = set()
    for candidate in candidates:
        candidate = trusted_path(
            candidate,
            label=f"marketplace plugin source {plugin_name}",
            status="identity_unavailable",
        )
        if not candidate.is_relative_to(root):
            raise FleetError(
                f"marketplace plugin path escapes its root: {plugin_name}",
                status="identity_unavailable",
            )
        if str(candidate) in seen:
            continue
        seen.add(str(candidate))
        manifest = candidate / ".codex-plugin" / "plugin.json"
        if not manifest.exists() and not manifest.is_symlink():
            continue
        try:
            payload = json.loads(
                read_trusted_bytes(
                    manifest,
                    label=f"plugin manifest for {plugin_name}",
                    status="identity_unavailable",
                )
            )
        except FleetError:
            raise
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            raise FleetError(
                f"plugin manifest must contain a JSON object: {manifest}",
                status="identity_unavailable",
            )
        if payload.get("name") == plugin_name:
            return candidate
    raise FleetError(f"marketplace plugin source is unavailable: {plugin_name}", status="identity_unavailable")


def _plugin_source_identity(source: Path) -> dict[str, str]:
    manifest = source / ".codex-plugin" / "plugin.json"
    try:
        payload = json.loads(
            read_trusted_bytes(
                manifest,
                label="plugin manifest",
                status="identity_unavailable",
            )
        )
    except FleetError:
        raise
    except json.JSONDecodeError as error:
        raise FleetError(f"plugin manifest is unreadable: {manifest}", status="identity_unavailable") from error
    if not isinstance(payload, dict):
        raise FleetError(
            f"plugin manifest must contain a JSON object: {manifest}",
            status="identity_unavailable",
        )
    version = payload.get("version")
    if not isinstance(version, str) or not version:
        raise FleetError(f"plugin version is unavailable: {source}", status="identity_unavailable")
    return {"version": version, "treeSha256": tree_digest(source)}


def _validate_project_marker(
    marker: dict[str, Any], project: dict[str, Any], profile_name: str
) -> None:
    expected = {
        "schemaVersion": SCHEMA_VERSION,
        "profile": profile_name,
        "projectId": project["id"],
        "adopted": True,
        "managedPlugins": project["plugins"],
    }
    if marker != expected:
        raise FleetError(f"project marker does not match managed identity: {project['id']}")


def _plan_actions(
    profile: dict[str, Any],
    projects: list[dict[str, Any]],
    *,
    advance_lock: bool,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    marketplace_action_ids: dict[str, str] = {}
    if advance_lock:
        for marketplace in profile["marketplaces"]:
            if marketplace["sourceType"] != "git":
                continue
            action_id = f"marketplace-upgrade:{marketplace['name']}"
            marketplace_action_ids[marketplace["name"]] = action_id
            actions.append(
                {
                    "id": action_id,
                    "kind": "marketplace-upgrade",
                    "stage": 1,
                    "marketplace": marketplace["name"],
                    "dependsOn": [],
                }
            )
    cache_actions: dict[str, str] = {}
    plugin_by_selector = {item["selector"]: item for item in profile["plugins"]}
    for plugin in profile["plugins"]:
        action_id = f"plugin-install:{plugin['selector']}"
        dependencies = []
        if plugin["marketplace"] in marketplace_action_ids:
            dependencies.append(marketplace_action_ids[plugin["marketplace"]])
        actions.append(
            {
                "id": action_id,
                "kind": "plugin-install",
                "stage": 2,
                "selector": plugin["selector"],
                "marketplace": plugin["marketplace"],
                "dependsOn": dependencies,
            }
        )
    for plugin in profile["plugins"]:
        action_id = f"cache-verify:{plugin['selector']}"
        cache_actions[plugin["selector"]] = action_id
        actions.append(
            {
                "id": action_id,
                "kind": "cache-verify",
                "stage": 3,
                "selector": plugin["selector"],
                "marketplace": plugin["marketplace"],
                "dependsOn": [f"plugin-install:{plugin['selector']}"],
            }
        )
    project_verify_ids: list[str] = []
    for project in projects:
        for selector in project["plugins"]:
            plugin = plugin_by_selector[selector]
            if plugin.get("projectAdapter") is None:
                continue
            base = f"{project['id']}:{selector}"
            plan_id = f"project-plan:{base}"
            apply_id = f"project-apply:{base}"
            verify_id = f"project-verify:{base}"
            actions.extend(
                [
                    {
                        "id": plan_id,
                        "kind": "project-plan",
                        "stage": 4,
                        "projectId": project["id"],
                        "projectPath": project["path"],
                        "selector": selector,
                        "adapter": plugin["projectAdapter"],
                        "dependsOn": [cache_actions[selector]],
                    },
                    {
                        "id": apply_id,
                        "kind": "project-apply",
                        "stage": 5,
                        "projectId": project["id"],
                        "projectPath": project["path"],
                        "selector": selector,
                        "adapter": plugin["projectAdapter"],
                        "dependsOn": [plan_id],
                    },
                    {
                        "id": verify_id,
                        "kind": "project-verify",
                        "stage": 6,
                        "projectId": project["id"],
                        "projectPath": project["path"],
                        "selector": selector,
                        "adapter": plugin["projectAdapter"],
                        "dependsOn": [apply_id],
                    },
                ]
            )
            project_verify_ids.append(verify_id)
    if advance_lock:
        dependencies = sorted(set(cache_actions.values()).union(project_verify_ids))
        actions.append(
            {
                "id": "lock-promote",
                "kind": "lock-promote",
                "stage": 7,
                "dependsOn": dependencies,
            }
        )
    return actions


def _read_json(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        content = read_trusted_bytes(path, label=label, status="invalid_profile")
        payload = json.loads(content)
    except FleetError:
        raise
    except json.JSONDecodeError as error:
        raise FleetError(f"{label} is not valid JSON: {path}", status="invalid_profile") from error
    if not isinstance(payload, dict):
        raise FleetError(f"{label} must contain a JSON object", status="invalid_profile")
    return payload, content


def _unique(records: list[Any], key: str, label: str) -> None:
    seen: set[str] = set()
    for item in records:
        if not isinstance(item, dict) or not isinstance(item.get(key), str):
            raise FleetError(f"{label} record is invalid", status="invalid_profile")
        value = item[key]
        if value in seen:
            raise FleetError(f"duplicate {label}: {value}", status="invalid_profile")
        seen.add(value)


def _blocker(code: str, subject: str, detail: str, **evidence: Any) -> dict[str, Any]:
    return {"code": code, "subject": subject, "detail": detail, **evidence}


def _bytes_digest(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()
