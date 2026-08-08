from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterator

from .core import FleetError, tree_digest, trusted_path


ROUTINE_DEVFLOW_AUTHORIZATION = "project-refresh-apply"


class DevFlowAdapter:
    name = "devflow-v1"

    def __init__(
        self,
        *,
        project: Path,
        plugin_root: Path,
        codex_home: Path,
        expected_tree_sha256: str,
    ) -> None:
        self.project = trusted_path(
            project,
            label="Adapter project",
            status="adapter_unavailable",
        )
        self.plugin_root = trusted_path(
            plugin_root,
            label="Adapter plugin cache",
            status="adapter_unavailable",
        )
        self.codex_home = trusted_path(
            codex_home,
            label="Adapter Codex home",
            status="adapter_unavailable",
        )
        self.expected_tree_sha256 = expected_tree_sha256
        self.script = self.plugin_root / "scripts" / "plugin_project_migration.py"
        self._attest()

    def _attest(self) -> None:
        if tree_digest(self.plugin_root) != self.expected_tree_sha256:
            raise FleetError(
                f"DevFlow cache identity changed before Adapter execution: {self.plugin_root}",
                status="adapter_unavailable",
            )
        if not self.script.is_file() or self.script.is_symlink():
            raise FleetError(
                f"verified DevFlow cache has no trusted migration CLI: {self.script}",
                status="adapter_unavailable",
            )

    def plan(self) -> dict[str, Any]:
        command = self._base("plan")
        payload = _run_adapter_json(command, allowed_codes={0, 2})
        actions = payload.get("actions")
        digest = payload.get("planSha256")
        if not isinstance(actions, list) or not isinstance(digest, str):
            raise FleetError("DevFlow adapter returned an invalid plan", status="adapter_failed")
        if not payload.get("ok") and payload.get("status") in {"blocked", "baseline_ambiguous"}:
            raise FleetError(
                f"DevFlow project plan is blocked: {payload.get('status')}",
                status="project_blocked",
            )
        safe_ids: list[str] = []
        manual_actions: list[dict[str, Any]] = []
        for action in actions:
            if not isinstance(action, dict) or not isinstance(action.get("id"), str):
                raise FleetError("DevFlow plan contains an invalid action", status="adapter_failed")
            authorization = action.get("authorization")
            if authorization == ROUTINE_DEVFLOW_AUTHORIZATION:
                safe_ids.append(action["id"])
            else:
                manual_actions.append(
                    {
                        "authorization": str(authorization or "manual-review"),
                        "actionId": action["id"],
                        "path": action.get("path"),
                        "reason": "outside_routine_sync_authority",
                    }
                )
        for item in payload.get("manualActions", []):
            if isinstance(item, dict):
                manual_actions.append(
                    {
                        "authorization": str(item.get("authorization") or "manual-review"),
                        "actionId": str(item.get("id") or item.get("kind") or "manual-action"),
                        "path": item.get("path"),
                        "reason": str(item.get("reason") or "adapter_manual_action"),
                    }
                )
        return {
            "plan": payload,
            "planSha256": digest,
            "safeActionIds": sorted(safe_ids),
            "manualActions": _deduplicate_manual_actions(manual_actions),
        }

    def apply_and_verify(self, prepared: dict[str, Any]) -> dict[str, Any]:
        safe_ids = prepared["safeActionIds"]
        if not safe_ids:
            return {
                "status": "current" if prepared["plan"].get("status") == "current" else "manual_required",
                "planSha256": prepared["planSha256"],
                "selectedActions": [],
                "changedPaths": [],
                "manualActions": prepared["manualActions"],
                "adapterReceipt": None,
                "applyResult": None,
                "verifyResult": None,
            }
        command = self._base("apply")
        command.extend(
            [
                "--expect-plan",
                prepared["planSha256"],
                "--allow",
                ROUTINE_DEVFLOW_AUTHORIZATION,
            ]
        )
        for action_id in safe_ids:
            command.extend(["--action", action_id])
        applied = _run_adapter_json(command, allowed_codes={0, 2})
        if not applied.get("ok") or applied.get("status") not in {
            "applied_and_verified",
            "applied_incomplete",
        }:
            raise FleetError(
                f"DevFlow apply failed: {applied.get('status')}",
                status="adapter_failed",
            )
        receipt_value = applied.get("receiptPath")
        if not isinstance(receipt_value, str):
            raise FleetError("DevFlow apply returned no receipt", status="adapter_failed")
        receipt = Path(receipt_value)
        if not receipt.is_absolute():
            receipt = self.project / receipt
        receipt = trusted_path(receipt, label="DevFlow Adapter receipt", status="adapter_failed")
        if not receipt.is_relative_to(self.project):
            raise FleetError("DevFlow Adapter receipt escapes its project", status="adapter_failed")
        changed_paths = self._changed_paths(applied)
        manual = list(prepared["manualActions"])
        for authorization in applied.get("remainingAuthorizations", []):
            manual.append(
                {
                    "authorization": str(authorization),
                    "actionId": "remaining-authorization",
                    "path": None,
                    "reason": "adapter_reported_remaining_authorization",
                }
            )
        try:
            verified = self.verify(receipt)
        except FleetError as error:
            return {
                "status": "adapter_verification_failed",
                "planSha256": prepared["planSha256"],
                "selectedActions": safe_ids,
                "changedPaths": changed_paths,
                "manualActions": _deduplicate_manual_actions(manual),
                "adapterReceipt": str(receipt),
                "applyResult": _bounded(applied),
                "verifyResult": None,
                "error": str(error),
            }
        return {
            "status": "verified_with_manual_actions" if manual else "verified",
            "planSha256": prepared["planSha256"],
            "selectedActions": safe_ids,
            "changedPaths": changed_paths,
            "manualActions": _deduplicate_manual_actions(manual),
            "adapterReceipt": str(receipt),
            "applyResult": _bounded(applied),
            "verifyResult": _bounded(verified),
        }

    def _changed_paths(self, applied: dict[str, Any]) -> list[str]:
        values = applied.get("changedPaths", [])
        if not isinstance(values, list):
            raise FleetError("DevFlow apply returned invalid changed paths", status="adapter_failed")
        changed: set[str] = set()
        for value in values:
            if not isinstance(value, str) or not value:
                raise FleetError("DevFlow apply returned invalid changed paths", status="adapter_failed")
            candidate = Path(value).expanduser()
            if not candidate.is_absolute():
                candidate = self.project / candidate
            candidate = Path(os.path.abspath(candidate))
            if not candidate.is_relative_to(self.project):
                raise FleetError(
                    f"DevFlow changed path escapes its project: {candidate}",
                    status="adapter_failed",
                )
            changed.add(str(candidate))
        return sorted(changed)

    def verify(self, receipt: Path) -> dict[str, Any]:
        receipt = self._trusted_receipt(receipt)
        command = self._base("verify") + ["--receipt", str(receipt)]
        verified = _run_adapter_json(command, allowed_codes={0, 2, 3})
        issues = verified.get("issues", [])
        if not isinstance(issues, list) or issues or verified.get("status") not in {
            "verified",
            "verified_incomplete",
        }:
            raise FleetError(
                f"DevFlow receipt verification failed: {verified.get('status')}",
                status="adapter_verification_failed",
            )
        return verified

    def rollback(self, receipt: Path, *, apply: bool) -> dict[str, Any]:
        receipt = self._trusted_receipt(receipt)
        command = self._base("rollback") + ["--receipt", str(receipt)]
        if apply:
            command.append("--apply")
        payload = _run_adapter_json(command, allowed_codes={0, 2})
        if apply and (not payload.get("ok") or payload.get("status") != "rolled_back"):
            raise FleetError(
                f"DevFlow rollback failed: {payload.get('status')}",
                status="rollback_failed",
            )
        return payload

    def _trusted_receipt(self, receipt: Path) -> Path:
        selected = trusted_path(
            receipt,
            label="DevFlow Adapter receipt",
            status="adapter_verification_failed",
        )
        if not selected.is_relative_to(self.project) or not selected.is_file():
            raise FleetError(
                "DevFlow Adapter receipt is outside its project or unavailable",
                status="adapter_verification_failed",
            )
        return selected

    def _base(self, command: str) -> list[str]:
        self._attest()
        return [
            sys.executable,
            str(self.script),
            command,
            "--repo",
            str(self.project),
            "--plugin-root",
            str(self.plugin_root),
            "--codex-home",
            str(self.codex_home),
            "--json",
        ]


def prepare_project_adapters(
    project_actions: list[dict[str, Any]],
    *,
    identities: dict[str, Any],
    codex_home: Path,
) -> list[dict[str, Any]]:
    def prepare(action: dict[str, Any]) -> dict[str, Any]:
        adapter = _adapter_for_action(action, identities=identities, codex_home=codex_home)
        return {"action": action, "adapter": adapter, "prepared": adapter.plan()}

    if not project_actions:
        return []
    with ThreadPoolExecutor(max_workers=min(8, len(project_actions))) as pool:
        prepared = list(pool.map(prepare, project_actions))
    return sorted(
        prepared,
        key=lambda item: (item["action"]["projectId"], item["action"]["selector"]),
    )


def _adapter_for_action(
    action: dict[str, Any], *, identities: dict[str, Any], codex_home: Path
) -> DevFlowAdapter:
    if action.get("adapter") != DevFlowAdapter.name:
        raise FleetError(f"unknown project adapter: {action.get('adapter')}", status="adapter_unavailable")
    selector = action["selector"]
    plugin_name, marketplace = selector.rsplit("@", 1)
    identity = identities["plugins"][selector]
    plugin_root = codex_home / "plugins" / "cache" / marketplace / plugin_name / identity["version"]
    return DevFlowAdapter(
        project=Path(action["projectPath"]),
        plugin_root=plugin_root,
        codex_home=codex_home,
        expected_tree_sha256=identity["treeSha256"],
    )


@contextmanager
def project_lock(state_dir: Path, *, profile: str, project_id: str) -> Iterator[Path]:
    lock_root = trusted_path(
        state_dir,
        label="fleet state directory",
        status="project_locked",
    ) / "locks"
    key = hashlib.sha256(f"{profile}\0{project_id}".encode("utf-8")).hexdigest()
    path = lock_root / f"{key}.lock"
    try:
        lock_root.mkdir(parents=True, exist_ok=True)
        handle = path.open("a+", encoding="utf-8")
    except OSError as error:
        raise FleetError(
            f"project lock is unavailable: {project_id}",
            status="project_locked",
        ) from error
    with handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError) as error:
            raise FleetError(
                f"project lock is already held: {project_id}",
                status="project_locked",
            ) from error
        try:
            yield path
        finally:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                # Closing the descriptor releases the advisory lock; do not
                # hide a completed Adapter result behind an unlock race.
                pass


def _run_adapter_json(command: list[str], *, allowed_codes: set[int]) -> dict[str, Any]:
    env = os.environ.copy()
    try:
        completed = subprocess.run(
            command,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=600,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise FleetError(f"Adapter command failed: {type(error).__name__}", status="adapter_failed") from error
    if completed.returncode not in allowed_codes:
        detail = (completed.stderr or completed.stdout).strip()[:1000]
        raise FleetError(
            f"Adapter command exited {completed.returncode}: {detail}",
            status="adapter_failed",
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise FleetError("Adapter command returned invalid JSON", status="adapter_failed") from error
    if not isinstance(payload, dict):
        raise FleetError("Adapter command returned a non-object", status="adapter_failed")
    return payload


def _deduplicate_manual_actions(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for item in items:
        key = json.dumps(item, sort_keys=True, ensure_ascii=False)
        unique[key] = item
    return [unique[key] for key in sorted(unique)]


def _bounded(value: dict[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")
    if len(encoded) <= 8192:
        return value
    return {
        "truncated": True,
        "byteLength": len(encoded),
        "sha256": "sha256:" + hashlib.sha256(encoded).hexdigest(),
    }
