from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from workflow_planning_paths import atomic_write_devflow, atomic_write_text
from workflow_dependency_provenance import load_dependency_provenance
from workflow_provider_registry import (
    authorize_action,
    default_plugin_root,
    load_provider_registry,
    side_effect_decision,
)


def provider_activation_plan(
    selection: dict[str, Any],
    repo: Path,
    codex_home: Path,
    authorizations: set[str] | None = None,
) -> dict[str, Any]:
    plugin_root = default_plugin_root()
    granted = {"task_scope", *(authorizations or set())}
    actions: list[dict[str, Any]] = [
        {
            "id": "verify-openspec-core",
            "effect": "workspace.read",
            "command": ["openspec", "status", "--json"],
        }
    ]
    profile = selection["effectiveMethodologyProfile"]
    roadmap = selection["effectiveRoadmapProvider"]
    source_records = load_dependency_provenance(plugin_root).get("providerSources", {})
    if profile == "strict-superpowers":
        actions.append(provider_activation_action("superpowers", selection, source_records))
    elif profile == "lean-matt":
        actions.append(provider_activation_action("mattpocock-skills", selection, source_records))
    if roadmap == "gsd":
        actions.append(provider_activation_action("gsd", selection, source_records))
    actions = [authorize_action(plugin_root, action, granted) for action in actions]
    return {
        "ok": True,
        "dryRun": True,
        "repo": str(Path(repo).resolve()),
        "codexHome": str(Path(codex_home).resolve()),
        "selection": selection,
        "actions": actions,
    }


def provider_activation_action(
    provider: str,
    selection: dict[str, Any],
    source_records: dict[str, Any],
) -> dict[str, Any]:
    selector = selection.get("providerSelectors", {}).get(provider, {})
    sources = [
        {"source_id": source_id, **record}
        for source_id, record in source_records.items()
        if isinstance(record, dict) and record.get("provider") == provider
    ]
    source_id = selector.get("source_id") if isinstance(selector, dict) else None
    if source_id:
        sources = [source for source in sources if source.get("source_id") == source_id]
    elif isinstance(selector, dict) and selector:
        identity_keys = {
            "superpowers": ("source_channel", "version"),
            "mattpocock-skills": ("repository", "ref", "commit"),
            "gsd": ("package", "version"),
        }[provider]
        sources = [
            source
            for source in sources
            if all(
                selector.get(key) in (None, "")
                or str(selector.get(key)) == str(source.get(key))
                for key in identity_keys
            )
        ]
    if len(sources) != 1:
        return {
            "id": f"select-{provider}-source",
            "provider": provider,
            "effect": "workspace.read",
            "status": "source-selection-required",
            "command": [],
            "candidates": [source.get("source_id") for source in sources],
        }
    source = sources[0]
    return {
        "id": f"activate-{provider}",
        "provider": provider,
        "sourceId": source.get("source_id"),
        "effect": "dependency.install_update",
        "status": "planned",
        "command": list(source.get("installCommand") or source.get("updateCommand") or []),
    }


def apply_provider_source_overrides(
    selection: dict[str, Any],
    overrides: list[str] | None,
    source_records: dict[str, Any] | None = None,
) -> dict[str, Any]:
    updated = dict(selection)
    selectors = dict(selection.get("providerSelectors", {}))
    parsed: dict[str, str] = {}
    for value in overrides or []:
        provider, separator, source_id = value.partition("=")
        provider = provider.strip()
        source_id = source_id.strip()
        if not separator or not provider or not source_id:
            raise ValueError(f"invalid provider source override: {value}")
        if provider not in {"superpowers", "mattpocock-skills", "gsd"}:
            raise ValueError(f"unknown provider source override: {provider}")
        record = (source_records or {}).get(source_id)
        if not isinstance(record, dict):
            raise ValueError(f"unknown provider source id: {source_id}")
        if record.get("provider") != provider:
            raise ValueError(f"provider source {source_id} belongs to {record.get('provider')}")
        parsed[provider] = source_id
        current = dict(selectors.get(provider, {}))
        current.update({key: value for key, value in record.items() if key != "provider"})
        current["source_id"] = source_id
        selectors[provider] = current
    updated["providerSelectors"] = selectors
    updated["providerSourceOverrides"] = parsed
    if parsed and not updated.get("selectionOverrides"):
        updated["selectionSource"] = "provider_source_override"
    return updated


def apply_provider_selection_overrides(
    selection: dict[str, Any],
    methodology_profile: str | None = None,
    roadmap_provider: str | None = None,
) -> dict[str, Any]:
    registry = load_provider_registry(default_plugin_root())
    updated = dict(selection)
    overrides: dict[str, str] = {}
    if methodology_profile is not None:
        if methodology_profile not in registry["methodologyProfiles"]:
            raise ValueError(f"unknown methodology profile override: {methodology_profile}")
        updated["effectiveMethodologyProfile"] = methodology_profile
        overrides["methodology_profile"] = methodology_profile
        updated["configErrors"] = [
            item
            for item in updated.get("configErrors", [])
            if not str(item).startswith("unknown methodology profile:")
        ]
    if roadmap_provider is not None:
        if roadmap_provider not in registry["roadmapProviders"]:
            raise ValueError(f"unknown roadmap provider override: {roadmap_provider}")
        updated["effectiveRoadmapProvider"] = roadmap_provider
        overrides["roadmap_provider"] = roadmap_provider
        updated["configErrors"] = [
            item
            for item in updated.get("configErrors", [])
            if not str(item).startswith("unknown roadmap provider:")
        ]
    if overrides:
        updated["selectionOverrides"] = overrides
        updated["selectionSource"] = "cli_override"
        updated["migrationRecommended"] = False
    return updated


def persist_provider_lock(
    diagnosis: dict[str, Any],
    repo: Path,
    *,
    apply: bool = False,
    persist_selection: bool = False,
) -> dict[str, Any]:
    repo = Path(repo).resolve()
    path = repo / ".planning" / "devflow" / "providers.lock.json"
    payload = provider_lock_payload(diagnosis)
    if not apply:
        return {
            "ok": True,
            "status": "planned",
            "path": str(path),
            "payload": payload,
            "changed": False,
        }
    if not persist_selection:
        return {
            "ok": False,
            "status": "authorization_required",
            "path": str(path),
            "payload": payload,
            "changed": False,
        }
    policy = side_effect_decision(
        default_plugin_root(),
        "canonical.write",
        {"approved_promoter_write_set"},
    )
    if not policy["authorized"]:
        return {"ok": False, "status": "authorization_required", "path": str(path), "changed": False}
    rendered = f"{json.dumps(payload, indent=2, sort_keys=True)}\n"
    if path.exists() and path.read_text() == rendered:
        return {
            "ok": True,
            "status": "current",
            "path": str(path),
            "payload": payload,
            "changed": False,
        }
    atomic_write_devflow(repo, path, rendered)
    return {
        "ok": True,
        "status": "applied",
        "path": str(path),
        "payload": payload,
        "changed": True,
    }


def persist_provider_config(
    diagnosis: dict[str, Any],
    repo: Path,
    *,
    apply: bool = False,
    persist_selection: bool = False,
) -> dict[str, Any]:
    repo = Path(repo).resolve()
    path = repo / ".dev-flow.json"
    selection = diagnosis["selection"]
    if not apply:
        return {"ok": True, "status": "planned", "path": str(path), "changed": False}
    if not persist_selection:
        return {"ok": False, "status": "authorization_required", "path": str(path), "changed": False}
    policy = side_effect_decision(
        default_plugin_root(),
        "canonical.write",
        {"approved_promoter_write_set"},
    )
    if not policy["authorized"]:
        return {"ok": False, "status": "authorization_required", "path": str(path), "changed": False}
    current: dict[str, Any] = {}
    if path.exists():
        loaded = json.loads(path.read_text())
        if isinstance(loaded, dict):
            current = loaded
    workflow = current.get("workflow") if isinstance(current.get("workflow"), dict) else {}
    workflow = dict(workflow)
    workflow["methodology_profile"] = selection["effectiveMethodologyProfile"]
    workflow["roadmap_provider"] = selection["effectiveRoadmapProvider"]
    selectors = normalized_persisted_selectors(diagnosis)
    if selectors:
        workflow["provider_selectors"] = selectors
    workflow["roadmap_bindings"] = dict(selection.get("roadmapBindings", {}))
    current["workflow"] = workflow
    rendered = f"{json.dumps(current, indent=2, sort_keys=True)}\n"
    changed = not path.exists() or path.read_text() != rendered
    if changed:
        atomic_write(path, rendered)
    return {
        "ok": True,
        "status": "applied" if changed else "current",
        "path": str(path),
        "changed": changed,
    }


def persist_provider_selection_transaction(
    diagnosis: dict[str, Any],
    repo: Path,
    *,
    apply: bool,
    persist_selection: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not apply:
        return (
            persist_provider_config(
                diagnosis, repo, apply=False, persist_selection=persist_selection
            ),
            persist_provider_lock(
                diagnosis, repo, apply=False, persist_selection=persist_selection
            ),
        )
    repo = Path(repo).resolve()
    config_path = repo / ".dev-flow.json"
    lock_path = repo / ".planning" / "devflow" / "providers.lock.json"
    snapshots = {
        config_path: config_path.read_bytes() if config_path.exists() else None,
        lock_path: lock_path.read_bytes() if lock_path.exists() else None,
    }
    try:
        config_result = persist_provider_config(
            diagnosis, repo, apply=True, persist_selection=persist_selection
        )
        if not config_result["ok"]:
            return config_result, {
                "ok": False,
                "status": config_result["status"],
                "changed": False,
            }
        lock_result = persist_provider_lock(
            diagnosis, repo, apply=True, persist_selection=persist_selection
        )
        if not lock_result["ok"]:
            restore_provider_persistence(repo, snapshots)
            config_result = {
                **config_result,
                "ok": False,
                "status": "transaction_rolled_back",
                "changed": False,
            }
        return config_result, lock_result
    except Exception:
        restore_provider_persistence(repo, snapshots)
        raise


def restore_provider_persistence(repo: Path, snapshots: dict[Path, bytes | None]) -> None:
    for path, content in snapshots.items():
        if content is None:
            if path.exists() or path.is_symlink():
                if path == repo / ".planning" / "devflow" / "providers.lock.json":
                    from workflow_planning_paths import guard_devflow_write

                    guard_devflow_write(repo, path)
                path.unlink()
            continue
        text = content.decode()
        if path == repo / ".planning" / "devflow" / "providers.lock.json":
            atomic_write_devflow(repo, path, text)
        else:
            atomic_write_text(path, text)


def normalized_persisted_selectors(diagnosis: dict[str, Any]) -> dict[str, Any]:
    selection = diagnosis["selection"]
    selectors = {
        key: dict(value)
        for key, value in selection.get("providerSelectors", {}).items()
        if isinstance(value, dict)
    }
    superpowers = diagnosis.get("providers", {}).get("superpowers", {})
    if selection["effectiveMethodologyProfile"] == "strict-superpowers" and superpowers.get("ready"):
        selector = dict(selectors.get("superpowers", {}))
        selector.update(
            {
                "kind": "codex-plugin",
                "plugin_id": "superpowers",
                "source_channel": superpowers.get("sourceChannel"),
                "version": superpowers.get("version"),
            }
        )
        selectors["superpowers"] = selector
    matt = diagnosis.get("providers", {}).get("mattpocock-skills", {})
    if selection["effectiveMethodologyProfile"] == "lean-matt" and matt.get("ready"):
        selector = dict(selectors.get("mattpocock-skills", {}))
        identity = matt.get("sourceIdentity", {})
        selector.update(
            {
                key: value
                for key, value in identity.items()
                if key in {"source_id", "kind", "repository", "ref", "commit"}
            }
        )
        selectors["mattpocock-skills"] = selector
    gsd = diagnosis.get("providers", {}).get("gsd", {})
    if selection["effectiveRoadmapProvider"] == "gsd" and gsd.get("ready"):
        selector = dict(selectors.get("gsd", {}))
        identity = gsd.get("sourceIdentity", {})
        selector.update(
            {
                key: value
                for key, value in identity.items()
                if key in {"source_id", "kind", "package", "version"}
            }
        )
        selectors["gsd"] = selector
    return selectors


def atomic_write(path: Path, text: str) -> None:
    atomic_write_text(path, text)


def provider_lock_payload(diagnosis: dict[str, Any]) -> dict[str, Any]:
    providers: dict[str, Any] = {}
    selected = set(diagnosis.get("selectedProviders", []))
    reports = diagnosis.get("providers", {})
    if "superpowers" in selected:
        report = reports.get("superpowers", {})
        providers["superpowers"] = {
            "sourceRoot": report.get("root"),
            "sourceChannel": report.get("sourceChannel"),
            "version": report.get("version"),
            "manifestDigest": report.get("manifestDigest"),
            "skillHashes": report.get("skillHashes", {}),
        }
    if "mattpocock-skills" in selected:
        report = reports.get("mattpocock-skills", {})
        selector = diagnosis.get("selection", {}).get("providerSelectors", {}).get("mattpocock-skills", {})
        identity = report.get("sourceIdentity", {})
        providers["mattpocock-skills"] = {
            "sourceRoot": report.get("root"),
            "repository": selector.get("repository") or identity.get("repository"),
            "ref": selector.get("ref") or identity.get("ref"),
            "commit": selector.get("commit") or identity.get("commit"),
            "skillHashes": report.get("skillHashes", {}),
        }
    if "gsd" in selected:
        report = reports.get("gsd", {})
        providers["gsd"] = {
            "sourceRoot": str(Path(report.get("runtime", "")).parent.parent) if report.get("runtime") else None,
            "runtime": report.get("runtime"),
            "version": report.get("version"),
            "runtimeSha256": report.get("runtimeSha256"),
            "contentManifest": report.get("contentManifest"),
            "contentIdentitySha256": report.get("contentIdentitySha256"),
            "contentManifestSha256": report.get("contentManifestSha256"),
            "contentAttestation": report.get("contentAttestation", {}),
            "skillHashes": report.get("skillHashes", {}),
            "agentHashes": report.get("agentHashes", {}),
        }
    return {"schemaVersion": 1, "providers": providers}
