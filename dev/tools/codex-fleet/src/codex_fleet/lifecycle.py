from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from typing import Any

from .adapters import DevFlowAdapter, project_lock
from .core import (
    FleetError,
    SCHEMA_VERSION,
    _atomic_write,
    canonical_bytes,
    digest_value,
    read_trusted_bytes,
    runtime_inventory,
    tree_digest,
    trusted_path,
)
from .executor import _verify_global_identities
from .sync import _bytes_digest, _read_json, _validate_profile


def verify_fleet_receipt(receipt_path: Path) -> dict[str, Any]:
    try:
        receipt = _load_receipt(receipt_path)
        if not receipt.get("ok"):
            raise FleetError("only a successful fleet receipt can be verified", status="invalid_receipt")
        plan = receipt["plan"]
        _verify_static_post_state(receipt)
        manifest, _ = _read_json(Path(plan["paths"]["manifest"]), "manifest")
        lock, _ = _read_json(Path(plan["paths"]["lock"]), "lock")
        device, _ = _read_json(Path(plan["paths"]["device"]), "device overlay")
        codex_home = Path(plan["paths"]["codexHome"])
        profile = _validate_profile(manifest, lock, device, codex_home)
        runtime = runtime_inventory(codex_home=codex_home)
        identities, resolved_lock = _verify_global_identities(
            profile=profile,
            current_lock=lock,
            runtime=runtime,
            codex_home=codex_home,
            advance_lock=False,
        )
        if identities != receipt.get("afterIdentities") or canonical_bytes(
            resolved_lock
        ) != _verification_bytes(Path(plan["paths"]["lock"]), "current lock"):
            raise FleetError("current global identity differs from the receipt", status="verification_failed")

        project_results = _verify_project_receipts(receipt, identities=identities, codex_home=codex_home)
        manual_actions = list(receipt.get("manualActions", []))
        status = "verified_with_manual_actions" if manual_actions else "verified"
        return {
            "schemaVersion": SCHEMA_VERSION,
            "kind": "codex-fleet-verification",
            "ok": True,
            "status": status,
            "receiptPath": str(receipt_path.expanduser().resolve()),
            "planSha256": receipt["planSha256"],
            "identities": identities,
            "actions": [
                {"kind": "global-verify"},
                *[
                    {
                        "kind": "project-verify",
                        "projectId": item["projectId"],
                        "selector": item["selector"],
                    }
                    for item in receipt.get("projectResults", [])
                    if item.get("adapterReceipt")
                ],
            ],
            "results": project_results,
            "projectResults": project_results,
            "manualActions": manual_actions,
            "nextAction": (
                "Review the named manual actions; verified routine state remains current."
                if manual_actions
                else "No verification repair is required."
            ),
        }
    except FleetError as error:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "kind": "codex-fleet-verification",
            "ok": False,
            "status": "verification_failed" if error.status != "invalid_receipt" else error.status,
            "receiptPath": str(receipt_path.expanduser().resolve()),
            "error": str(error),
            "projectResults": [],
            "actions": [],
            "results": [],
            "manualActions": [],
            "nextAction": "Repair the reported drift or use an intact successful receipt.",
        }


def rollback_fleet_receipt(receipt_path: Path, *, apply: bool) -> dict[str, Any]:
    rollback_path: Path | None = None
    try:
        receipt = _load_receipt(receipt_path)
        rollback_path = _rollback_receipt_path(receipt_path, receipt)
        prior_attempt = _load_rollback_attempt(rollback_path, receipt)
        if prior_attempt is not None:
            return {
                "schemaVersion": SCHEMA_VERSION,
                "kind": "codex-fleet-rollback",
                "ok": False,
                "status": "rollback_blocked",
                "apply": apply,
                "receiptPath": str(receipt_path.expanduser().resolve()),
                "rollbackReceiptPath": str(rollback_path),
                "actions": prior_attempt.get("actions", []),
                "results": prior_attempt.get("results", []),
                "manualActions": prior_attempt.get("manualActions", []),
                "error": "a receipt-bound rollback was already attempted; automatic retry is unsafe",
                "nextAction": prior_attempt.get(
                    "nextAction",
                    "Inspect the durable rollback attempt and recover pending actions manually.",
                ),
            }
        _preflight_rollback(receipt)
    except FleetError as error:
        report = {
            "schemaVersion": SCHEMA_VERSION,
            "kind": "codex-fleet-rollback",
            "ok": False,
            "status": "rollback_blocked",
            "apply": apply,
            "receiptPath": str(receipt_path.expanduser().resolve()),
            "actions": [],
            "results": [],
            "manualActions": [],
            "error": str(error),
            "nextAction": "Restore the exact receipt-bound postimage or stop for manual recovery.",
        }
        if rollback_path is not None and rollback_path.exists():
            report["rollbackReceiptPath"] = str(rollback_path)
        return report

    actions = _rollback_actions(receipt)
    manual_actions = [
        {
            "kind": "native-global-effect",
            "effect": effect,
            "reason": "no receipt-bound native downgrade command is available",
        }
        for effect in receipt.get("nonReversibleEffects", [])
    ]
    if not apply:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "kind": "codex-fleet-rollback",
            "ok": False,
            "status": "rollback_preview",
            "apply": False,
            "receiptPath": str(receipt_path.expanduser().resolve()),
            "actions": actions,
            "results": [],
            "manualActions": manual_actions,
            "nextAction": "Review the reverse plan, then repeat with --apply for reversible state only.",
        }

    plan = receipt["plan"]
    codex_home = Path(plan["paths"]["codexHome"])
    state_dir = receipt_path.expanduser().resolve().parent.parent
    if rollback_path is None:
        raise FleetError("rollback receipt path is unavailable", status="rollback_blocked")
    results: list[dict[str, Any]] = []
    try:
        for action in actions:
            if action["kind"] != "project-rollback":
                continue
            adapter = _adapter_from_result(action["projectResult"], receipt, codex_home=codex_home)
            with project_lock(
                state_dir,
                profile=plan["profile"],
                project_id=action["projectId"],
            ):
                result = adapter.rollback(Path(action["adapterReceipt"]), apply=True)
            results.append(
                {
                    "actionId": action["id"],
                    "kind": "project-rollback",
                    "projectId": action["projectId"],
                    "selector": action["selector"],
                    "status": result["status"],
                    "result": result,
                }
            )
        lock_change = receipt["lockChange"]
        if lock_change.get("changed"):
            lock_path = Path(lock_change["path"])
            if _bytes_digest(
                read_trusted_bytes(
                    lock_path,
                    label="lock postimage",
                    status="rollback_blocked",
                )
            ) != lock_change["afterSha256"]:
                raise FleetError("lock postimage changed during rollback", status="rollback_blocked")
            before_content = lock_change.get("beforeContent")
            if not isinstance(before_content, str):
                raise FleetError("receipt has no lock preimage", status="rollback_blocked")
            _atomic_write(lock_path, before_content.encode("utf-8"), mode=0o644)
            results.append(
                {
                    "actionId": action["id"],
                    "kind": "lock-restore",
                    "status": "restored",
                    "path": str(lock_path),
                }
            )
    except (FleetError, OSError) as error:
        completed = [item["actionId"] for item in results]
        pending = [
            _public_rollback_action(action)
            for action in actions
            if action["id"] not in completed
        ]
        next_action = (
            "Do not retry automatically. Inspect completed and pending actions, then recover "
            "the pending receipt-bound state manually."
        )
        failure_receipt = _write_rollback_receipt(
            rollback_path,
            source_receipt_path=receipt_path,
            source_receipt=receipt,
            status="rollback_failed",
            ok=False,
            actions=[_public_rollback_action(action) for action in actions],
            results=results,
            manual_actions=manual_actions,
            pending_actions=pending,
            error=str(error),
            next_action=next_action,
        )
        return {
            "schemaVersion": SCHEMA_VERSION,
            "kind": "codex-fleet-rollback",
            "ok": False,
            "status": "rollback_failed",
            "apply": True,
            "receiptPath": str(receipt_path.expanduser().resolve()),
            "rollbackReceiptPath": str(rollback_path),
            "actions": actions,
            "results": results,
            "manualActions": manual_actions,
            "error": str(error),
            "rollbackReceiptSha256": failure_receipt["receiptSha256"],
            "nextAction": next_action,
        }

    status = "rollback_incomplete" if manual_actions else "rolled_back"
    next_action = (
        "Complete the named native remediation before claiming full rollback."
        if manual_actions
        else "Receipt-bound reversible state has been rolled back."
    )
    rollback_receipt = _write_rollback_receipt(
        rollback_path,
        source_receipt_path=receipt_path,
        source_receipt=receipt,
        status=status,
        ok=not manual_actions,
        actions=[_public_rollback_action(action) for action in actions],
        results=results,
        manual_actions=manual_actions,
        pending_actions=[],
        error=None,
        next_action=next_action,
    )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "kind": "codex-fleet-rollback",
        "ok": True,
        "status": status,
        "apply": True,
        "receiptPath": str(receipt_path.expanduser().resolve()),
        "rollbackReceiptPath": str(rollback_path),
        "actions": actions,
        "results": results,
        "manualActions": manual_actions,
        "rollbackReceiptSha256": rollback_receipt["receiptSha256"],
        "nextAction": next_action,
    }


def _rollback_receipt_path(receipt_path: Path, receipt: dict[str, Any]) -> Path:
    identity = receipt["receiptSha256"].removeprefix("sha256:")
    return receipt_path.expanduser().resolve().parent / f"rollback-{identity}.json"


def _load_rollback_attempt(
    path: Path,
    source_receipt: dict[str, Any],
) -> dict[str, Any] | None:
    if not path.exists() and not path.is_symlink():
        return None
    try:
        payload = json.loads(
            read_trusted_bytes(
                path,
                label="rollback attempt receipt",
                status="rollback_blocked",
            )
        )
    except (FleetError, json.JSONDecodeError) as error:
        if isinstance(error, FleetError):
            raise
        raise FleetError("rollback attempt receipt is invalid", status="rollback_blocked") from error
    if not isinstance(payload, dict) or payload.get("kind") != "codex-fleet-rollback-receipt":
        raise FleetError("rollback attempt receipt kind is invalid", status="rollback_blocked")
    expected = payload.get("receiptSha256")
    unsigned = dict(payload)
    unsigned.pop("receiptSha256", None)
    if expected != digest_value(unsigned):
        raise FleetError("rollback attempt receipt identity is invalid", status="rollback_blocked")
    if (
        payload.get("sourceReceiptSha256") != source_receipt["receiptSha256"]
        or payload.get("retryAllowed") is not False
        or not isinstance(payload.get("completedActionIds"), list)
        or not isinstance(payload.get("pendingActions"), list)
    ):
        raise FleetError("rollback attempt receipt binding is invalid", status="rollback_blocked")
    return payload


def _write_rollback_receipt(
    path: Path,
    *,
    source_receipt_path: Path,
    source_receipt: dict[str, Any],
    status: str,
    ok: bool,
    actions: list[dict[str, Any]],
    results: list[dict[str, Any]],
    manual_actions: list[dict[str, Any]],
    pending_actions: list[dict[str, Any]],
    error: str | None,
    next_action: str,
) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "kind": "codex-fleet-rollback-receipt",
        "ok": ok,
        "status": status,
        "sourceReceiptPath": str(source_receipt_path.expanduser().resolve()),
        "sourceReceiptSha256": source_receipt["receiptSha256"],
        "actions": actions,
        "results": results,
        "completedActionIds": [item["actionId"] for item in results],
        "pendingActions": pending_actions,
        "manualActions": manual_actions,
        "retryAllowed": False,
        "nextAction": next_action,
    }
    if error is not None:
        receipt["error"] = error
    receipt["receiptSha256"] = digest_value(receipt)
    _atomic_write(path, canonical_bytes(receipt), mode=0o600)
    return receipt


def _public_rollback_action(action: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in action.items() if key != "projectResult"}


def _load_receipt(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(
            read_trusted_bytes(
                path,
                label="fleet receipt",
                status="invalid_receipt",
            )
        )
    except FleetError:
        raise
    except json.JSONDecodeError as error:
        raise FleetError("fleet receipt is not valid JSON", status="invalid_receipt") from error
    if not isinstance(payload, dict) or payload.get("schemaVersion") != SCHEMA_VERSION or payload.get(
        "kind"
    ) != "codex-fleet-receipt":
        raise FleetError("fleet receipt schema or kind is invalid", status="invalid_receipt")
    expected = payload.get("receiptSha256")
    unsigned = dict(payload)
    unsigned.pop("receiptSha256", None)
    if expected != digest_value(unsigned):
        raise FleetError("fleet receipt identity is invalid", status="invalid_receipt")
    _validate_receipt_structure(payload)
    return payload


def _validate_receipt_structure(receipt: dict[str, Any]) -> None:
    plan = receipt.get("plan")
    if not isinstance(plan, dict) or plan.get("kind") != "codex-fleet-plan":
        raise FleetError("fleet receipt has no valid sealed plan", status="invalid_receipt")
    sealed_digest = plan.get("planSha256")
    unsigned_plan = dict(plan)
    unsigned_plan.pop("planSha256", None)
    if (
        not isinstance(sealed_digest, str)
        or receipt.get("planSha256") != sealed_digest
        or sealed_digest != digest_value(unsigned_plan)
    ):
        raise FleetError("fleet receipt plan identity is invalid", status="invalid_receipt")
    paths = plan.get("paths")
    bindings = plan.get("bindings")
    if not isinstance(paths, dict) or not all(
        isinstance(paths.get(name), str) and paths[name]
        for name in ("manifest", "lock", "device", "codexHome")
    ):
        raise FleetError("fleet receipt plan paths are invalid", status="invalid_receipt")
    if not isinstance(bindings, dict) or not all(
        isinstance(bindings.get(name), expected_type)
        for name, expected_type in (
            ("manifest", str),
            ("lock", str),
            ("device", str),
            ("runtime", str),
            ("projectMarkers", dict),
            ("projectPaths", dict),
            ("sourceIdentities", dict),
        )
    ):
        raise FleetError("fleet receipt plan bindings are invalid", status="invalid_receipt")
    before_identities = receipt.get("beforeIdentities")
    after_identities = receipt.get("afterIdentities")
    identities = receipt.get("identities")
    lock_change = receipt.get("lockChange")
    for name, snapshot in (
        ("before identities", before_identities),
        ("after identities", after_identities),
        ("identity compatibility view", identities),
    ):
        if not isinstance(snapshot, dict) or not all(
            isinstance(snapshot.get(layer), dict)
            for layer in ("marketplaces", "plugins", "caches")
        ):
            raise FleetError(f"fleet receipt {name} are invalid", status="invalid_receipt")
    if identities != after_identities:
        raise FleetError("fleet receipt after identities are inconsistent", status="invalid_receipt")
    restart = receipt.get("restart")
    if (
        not isinstance(restart, dict)
        or not isinstance(restart.get("required"), bool)
        or restart.get("scope") != "codex-session"
        or not isinstance(restart.get("guidance"), str)
        or not restart["guidance"]
        or receipt.get("restartRequired") != restart["required"]
    ):
        raise FleetError("fleet receipt restart guidance is invalid", status="invalid_receipt")
    if not isinstance(lock_change, dict) or not all(
        key in lock_change
        for key in ("path", "changed", "beforeSha256", "afterSha256")
    ):
        raise FleetError("fleet receipt lock record is invalid", status="invalid_receipt")
    for name in (
        "results",
        "projectResults",
        "manualActions",
        "nonReversibleEffects",
        "changedManagedFiles",
    ):
        if not isinstance(receipt.get(name), list):
            raise FleetError(f"fleet receipt {name} is invalid", status="invalid_receipt")
    project_paths = bindings["projectPaths"]
    for item in receipt["projectResults"]:
        if not isinstance(item, dict):
            raise FleetError("fleet receipt project result is invalid", status="invalid_receipt")
        project_id = item.get("projectId")
        selector = item.get("selector")
        if (
            not isinstance(project_id, str)
            or not isinstance(selector, str)
            or item.get("projectPath") != project_paths.get(project_id)
            or selector not in identities["plugins"]
            or item.get("adapter") != DevFlowAdapter.name
        ):
            raise FleetError("fleet receipt project binding is invalid", status="invalid_receipt")


def _verify_static_post_state(receipt: dict[str, Any]) -> None:
    plan = receipt["plan"]
    for name in ("manifest", "device"):
        path = Path(plan["paths"][name])
        if _bytes_digest(_verification_bytes(path, f"bound {name}")) != plan["bindings"][name]:
            raise FleetError(f"bound {name} changed after apply", status="verification_failed")
    lock_path = Path(plan["paths"]["lock"])
    if _bytes_digest(_verification_bytes(lock_path, "lock postimage")) != receipt["lockChange"]["afterSha256"]:
        raise FleetError("lock postimage differs from receipt", status="verification_failed")
    for project_id, expected in plan["bindings"]["projectMarkers"].items():
        marker = Path(plan["bindings"]["projectPaths"][project_id]) / ".codex-fleet" / "project.json"
        if _bytes_digest(_verification_bytes(marker, f"project marker {project_id}")) != expected:
            raise FleetError(f"project marker changed after apply: {project_id}", status="verification_failed")


def _verification_bytes(path: Path, label: str) -> bytes:
    return read_trusted_bytes(path, label=label, status="verification_failed")


def _verify_project_receipts(
    receipt: dict[str, Any], *, identities: dict[str, Any], codex_home: Path
) -> list[dict[str, Any]]:
    selected = [item for item in receipt.get("projectResults", []) if item.get("adapterReceipt")]

    def verify(item: dict[str, Any]) -> dict[str, Any]:
        adapter = _adapter_from_result(item, receipt, codex_home=codex_home)
        result = adapter.verify(Path(item["adapterReceipt"]))
        return {
            "projectId": item["projectId"],
            "selector": item["selector"],
            "adapter": item["adapter"],
            "status": result["status"],
            "result": result,
        }

    if not selected:
        return []
    with ThreadPoolExecutor(max_workers=min(8, len(selected))) as pool:
        results = list(pool.map(verify, selected))
    return sorted(results, key=lambda item: (item["projectId"], item["selector"]))


def _adapter_from_result(
    item: dict[str, Any], receipt: dict[str, Any], *, codex_home: Path
) -> DevFlowAdapter:
    if item.get("adapter") != DevFlowAdapter.name:
        raise FleetError("receipt references an unknown adapter", status="invalid_receipt")
    selector = item["selector"]
    plugin_name, marketplace = selector.rsplit("@", 1)
    identity = receipt["identities"]["plugins"][selector]
    plugin_root = codex_home / "plugins" / "cache" / marketplace / plugin_name / identity["version"]
    return DevFlowAdapter(
        project=Path(item["projectPath"]),
        plugin_root=plugin_root,
        codex_home=codex_home,
        expected_tree_sha256=identity["treeSha256"],
    )


def _preflight_rollback(receipt: dict[str, Any]) -> None:
    _verify_static_post_state(receipt)
    plan = receipt.get("plan")
    identities = receipt.get("identities")
    if not isinstance(plan, dict) or not isinstance(identities, dict):
        raise FleetError("receipt has no verified identity binding", status="rollback_blocked")
    codex_home = Path(str(plan.get("paths", {}).get("codexHome") or ""))
    manifest, _ = _read_json(Path(plan["paths"]["manifest"]), "manifest")
    lock, _ = _read_json(Path(plan["paths"]["lock"]), "lock")
    device, _ = _read_json(Path(plan["paths"]["device"]), "device overlay")
    _validate_profile(manifest, lock, device, codex_home)
    plugin_identities = identities.get("plugins")
    if not isinstance(plugin_identities, dict):
        raise FleetError("receipt has no plugin identities", status="rollback_blocked")
    for selector, identity in plugin_identities.items():
        if not isinstance(selector, str) or selector.count("@") != 1 or not isinstance(identity, dict):
            raise FleetError("receipt plugin identity is invalid", status="rollback_blocked")
        plugin_name, marketplace = selector.rsplit("@", 1)
        version = identity.get("version")
        expected_tree = identity.get("treeSha256")
        if not isinstance(version, str) or not isinstance(expected_tree, str):
            raise FleetError("receipt plugin identity is incomplete", status="rollback_blocked")
        cache = codex_home / "plugins" / "cache" / marketplace / plugin_name / version
        if tree_digest(cache) != expected_tree:
            raise FleetError(
                f"verified plugin cache changed before rollback: {selector}",
                status="rollback_blocked",
            )
    lock_change = receipt.get("lockChange")
    if not isinstance(lock_change, dict):
        raise FleetError("receipt has no lock change record", status="rollback_blocked")
    if lock_change.get("changed"):
        path = Path(str(lock_change.get("path") or ""))
        current = read_trusted_bytes(
            path,
            label="lock postimage",
            status="rollback_blocked",
        )
        if _bytes_digest(current) != lock_change.get("afterSha256"):
            raise FleetError("lock postimage differs from receipt", status="rollback_blocked")
        if not isinstance(lock_change.get("beforeContent"), str):
            raise FleetError("lock preimage is unavailable", status="rollback_blocked")
    for item in receipt.get("projectResults", []):
        value = item.get("adapterReceipt")
        if value:
            adapter_receipt = trusted_path(
                Path(value),
                label=f"Adapter receipt for {item.get('projectId')}",
                status="rollback_blocked",
            )
            project_path = Path(item["projectPath"])
            if not adapter_receipt.is_relative_to(project_path) or not adapter_receipt.is_file():
                raise FleetError(
                    f"Adapter receipt is unavailable: {item.get('projectId')}",
                    status="rollback_blocked",
                )


def _rollback_actions(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for item in reversed(receipt.get("projectResults", [])):
        if not item.get("adapterReceipt"):
            continue
        actions.append(
            {
                "id": f"project-rollback:{item['projectId']}:{item['selector']}",
                "kind": "project-rollback",
                "projectId": item["projectId"],
                "selector": item["selector"],
                "adapter": item["adapter"],
                "adapterReceipt": item["adapterReceipt"],
                "projectResult": item,
            }
        )
    if receipt.get("lockChange", {}).get("changed"):
        actions.append(
            {
                "id": "lock-restore",
                "kind": "lock-restore",
                "path": receipt["lockChange"]["path"],
                "expectedPostimage": receipt["lockChange"]["afterSha256"],
                "preimage": receipt["lockChange"]["beforeSha256"],
            }
        )
    return actions
