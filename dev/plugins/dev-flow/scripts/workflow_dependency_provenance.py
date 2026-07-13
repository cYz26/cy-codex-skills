from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

from workflow_constants import resolve_plugin_root


def default_plugin_root() -> Path:
    return resolve_plugin_root(__file__)


def dependency_provenance_source_path(plugin_root: Path | None = None) -> Path:
    root = Path(plugin_root) if plugin_root is not None else default_plugin_root()
    source = root / "docs" / "dependency-provenance.json"
    if source.exists():
        return source
    return default_plugin_root() / "docs" / "dependency-provenance.json"


def load_dependency_provenance(plugin_root: Path | None = None) -> dict[str, Any]:
    source = dependency_provenance_source_path(plugin_root)
    return json.loads(source.read_text())


def dependency_provenance_records(plugin_root: Path | None = None) -> list[dict[str, Any]]:
    data = load_dependency_provenance(plugin_root)
    return list(data.get("dependencies", []))


def dependency_provenance_record(name: str, plugin_root: Path | None = None) -> dict[str, Any]:
    for record in dependency_provenance_records(plugin_root):
        if record.get("name") == name:
            return record
    raise KeyError(f"unknown dependency provenance record: {name}")


def dependency_install_command(name: str, plugin_root: Path | None = None) -> list[str]:
    return list(dependency_provenance_record(name, plugin_root).get("installCommand", []))


def dependency_update_command(name: str, plugin_root: Path | None = None) -> list[str]:
    record = dependency_provenance_record(name, plugin_root)
    return list(record.get("updateCommand") or record.get("installCommand") or [])


def dependency_provenance_fields(
    name: str,
    plugin_root: Path | None = None,
    *,
    command_name: str = "installCommand",
) -> dict[str, Any]:
    record = dependency_provenance_record(name, plugin_root)
    command = record.get(command_name) or record.get("installCommand") or []
    return {
        "expectedVersion": record.get("expectedVersion"),
        "installCommand": list(record.get("installCommand", [])),
        "recommendedCommand": list(command),
        "source": record.get("source"),
        "lastVerified": dependency_provenance_last_verified(plugin_root, record),
        "provenanceSource": str(dependency_provenance_source_path(plugin_root)),
    }


def dependency_provenance_last_verified(
    plugin_root: Path | None = None,
    record: dict[str, Any] | None = None,
) -> str | None:
    if record and record.get("lastVerified"):
        return str(record["lastVerified"])
    data = load_dependency_provenance(plugin_root)
    value = data.get("lastVerified")
    return str(value) if value else None


def dependency_provenance_report(
    plugin_root: Path,
    repo: Path | None = None,
    *,
    catalog_only_names: set[str] | None = None,
) -> dict[str, Any]:
    data = load_dependency_provenance(plugin_root)
    source = dependency_provenance_source_path(plugin_root)
    catalog_only = set(catalog_only_names or ())
    dependencies = [
        (
            catalog_only_dependency(record, source, data.get("lastVerified"))
            if record.get("name") in catalog_only
            else evaluate_dependency(record, source, data.get("lastVerified"), repo)
        )
        for record in data["dependencies"]
    ]
    return {
        "provenance": {
            "sourcePath": str(source),
            "schemaVersion": data.get("schemaVersion"),
            "lastVerified": data.get("lastVerified"),
        },
        "dependencies": dependencies,
        "checks": [dependency_check_item(item) for item in dependencies],
    }


def catalog_only_dependency(
    record: dict[str, Any],
    source_path: Path,
    default_last_verified: str | None,
) -> dict[str, Any]:
    return {
        "name": record["name"],
        "purpose": record.get("purpose"),
        "required": False,
        "status": "not_selected",
        "expectedVersion": record.get("expectedVersion"),
        "installedVersion": None,
        "binaryPath": None,
        "installCommand": list(record.get("installCommand", [])),
        "recommendedCommand": list(record.get("updateCommand") or record.get("installCommand") or []),
        "smokeCommand": [],
        "smokeResult": {
            "ok": True,
            "returncode": None,
            "summary": "not selected; runtime was not inspected",
        },
        "source": record.get("source"),
        "failureMode": record.get("failureMode"),
        "fallbackOrBlocker": record.get("fallbackOrBlocker"),
        "lastVerified": record.get("lastVerified") or default_last_verified,
        "provenanceSource": str(source_path),
    }


def evaluate_dependency(
    record: dict[str, Any],
    source_path: Path,
    default_last_verified: str | None,
    repo: Path | None,
) -> dict[str, Any]:
    if is_policy_only_record(record):
        return policy_only_dependency(record, source_path, default_last_verified)
    binary_path = resolve_binary_path(record, repo)
    installed_version = installed_dependency_version(record, repo)
    smoke_command = resolve_command(record.get("smokeCommand", []), repo, binary_path)
    smoke_result = smoke_dependency(smoke_command, binary_path)
    status = dependency_status(record, binary_path, installed_version, smoke_result, repo)
    return {
        "name": record["name"],
        "purpose": record.get("purpose"),
        "required": bool(record.get("required", True)),
        "status": status,
        "expectedVersion": record.get("expectedVersion"),
        "installedVersion": installed_version,
        "binaryPath": str(binary_path) if binary_path else None,
        "installCommand": list(record.get("installCommand", [])),
        "recommendedCommand": list(record.get("updateCommand") or record.get("installCommand") or []),
        "smokeCommand": smoke_command,
        "smokeResult": smoke_result,
        "source": record.get("source"),
        "failureMode": record.get("failureMode"),
        "fallbackOrBlocker": record.get("fallbackOrBlocker"),
        "lastVerified": record.get("lastVerified") or default_last_verified,
        "provenanceSource": str(source_path),
    }


def is_policy_only_record(record: dict[str, Any]) -> bool:
    kind = str(record.get("kind") or "")
    return kind in {"codex-plugin", "codex-plugin-dev-tool"} and not (
        record.get("binary") or record.get("binaryPath")
    )


def policy_only_dependency(
    record: dict[str, Any],
    source_path: Path,
    default_last_verified: str | None,
) -> dict[str, Any]:
    output = {
        "name": record["name"],
        "kind": record.get("kind"),
        "purpose": record.get("purpose"),
        "required": bool(record.get("required", True)),
        "status": "policy_recorded",
        "expectedVersion": record.get("expectedVersion"),
        "installedVersion": None,
        "binaryPath": None,
        "installCommand": list(record.get("installCommand", [])),
        "recommendedCommand": list(record.get("updateCommand") or record.get("installCommand") or []),
        "smokeCommand": [],
        "smokeResult": {"ok": True, "returncode": None, "summary": "policy-only dependency"},
        "source": record.get("source"),
        "failureMode": record.get("failureMode"),
        "fallbackOrBlocker": record.get("fallbackOrBlocker"),
        "lastVerified": record.get("lastVerified") or default_last_verified,
        "provenanceSource": str(source_path),
    }
    for key in [
        "minimumCompatibleVersion",
        "recommendedVersion",
        "strictProfileRequires",
        "compatibilityPolicy",
        "sources",
        "requiredSkills",
        "strictRecommendedSkills",
        "hookPolicy",
        "requiredHooksWhenVersionAtLeast",
    ]:
        if key in record:
            output[key] = record[key]
    return output


def resolve_binary_path(record: dict[str, Any], repo: Path | None) -> Path | None:
    if record.get("binary"):
        resolved = shutil.which(str(record["binary"]))
        return Path(resolved) if resolved else None
    template = record.get("binaryPath")
    if template:
        if repo is None and "{repo}" in template:
            return None
        return Path(resolve_template(str(template), repo, None))
    return None


def installed_dependency_version(record: dict[str, Any], repo: Path | None) -> str | None:
    version_file = record.get("versionFile")
    if version_file:
        if repo is None and "{repo}" in version_file:
            return None
        path = Path(resolve_template(str(version_file), repo, None))
        if path.exists():
            value = path.read_text().strip()
            return value or None
        return None
    version_command = resolve_command(record.get("versionCommand", []), repo, None)
    if not version_command:
        return None
    result = run_read_only_command(version_command)
    if not result["ok"]:
        return None
    return parse_version(result["stdout"])


def resolve_command(command: list[str], repo: Path | None, binary_path: Path | None) -> list[str]:
    return [resolve_template(str(part), repo, binary_path) for part in command]


def resolve_template(value: str, repo: Path | None, binary_path: Path | None) -> str:
    result = value
    if repo is not None:
        result = result.replace("{repo}", str(repo))
    if binary_path is not None:
        result = result.replace("{binaryPath}", str(binary_path))
    return result


def smoke_dependency(command: list[str], binary_path: Path | None) -> dict[str, Any]:
    if binary_path is None:
        return {"ok": False, "returncode": None, "summary": "missing binary"}
    if not binary_path.exists():
        return {"ok": False, "returncode": None, "summary": f"missing binary: {binary_path}"}
    if not command:
        return {"ok": False, "returncode": None, "summary": "missing smoke command"}
    result = run_read_only_command(command)
    return {
        "ok": result["ok"],
        "returncode": result["returncode"],
        "summary": short_output(result),
    }


def run_read_only_command(command: list[str], timeout: int = 120) -> dict[str, Any]:
    try:
        result = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
    except FileNotFoundError:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": f"missing executable: {command[0]}"}
    except PermissionError as exc:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": str(exc)}
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "returncode": None,
            "stdout": exc.stdout or "",
            "stderr": f"timeout after {timeout}s",
        }
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def parse_version(output: str) -> str | None:
    text = output.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return text.splitlines()[-1].strip() or None
    if isinstance(parsed, str):
        return parsed
    if isinstance(parsed, dict):
        value = parsed.get("version")
        return str(value) if value else None
    return None


def short_output(result: dict[str, Any], limit: int = 600) -> str:
    text = (result.get("stdout") or "") + (result.get("stderr") or "")
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "...(truncated)"


def dependency_status(
    record: dict[str, Any],
    binary_path: Path | None,
    installed_version: str | None,
    smoke_result: dict[str, Any],
    repo: Path | None,
) -> str:
    if repo is None and "{repo}" in str(record.get("binaryPath", "")):
        return "not_applicable"
    if binary_path is None or not binary_path.exists():
        return "missing"
    if not smoke_result.get("ok"):
        return "smoke_failed"
    expected = record.get("expectedVersion")
    if expected and installed_version != expected:
        return "dependency_drift"
    return "verified"


def dependency_check_item(dependency: dict[str, Any]) -> dict[str, Any]:
    status = dependency["status"]
    ok = status in {"verified", "not_applicable", "not_selected", "policy_recorded"}
    required = bool(dependency.get("required")) and status != "not_applicable"
    detail = (
        f"{status}: expected {dependency.get('expectedVersion') or 'unknown'}, "
        f"installed {dependency.get('installedVersion') or 'unknown'}, "
        f"binary {dependency.get('binaryPath') or 'missing'}"
    )
    return {
        "name": f"external dependency: {dependency['name']}",
        "ok": ok,
        "required": required,
        "detail": detail,
        "status": status,
    }
