from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
from typing import Any, Iterable


SCHEMA_VERSION = "1.0"
PROJECT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
IGNORED_TREE_NAMES = {".git", "__pycache__", ".DS_Store"}
KNOWN_ADAPTERS = {"devflow-v1"}


class FleetError(RuntimeError):
    def __init__(self, message: str, *, status: str = "invalid_request") -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class ProjectCandidate:
    project_id: str
    path: Path


class CommandRunner:
    """Boundary for structured native commands."""

    def __init__(self, *, codex_home: Path, timeout: int = 120) -> None:
        self.codex_home = codex_home
        self.timeout = timeout

    def json(self, args: list[str]) -> dict[str, Any]:
        env = os.environ.copy()
        env["CODEX_HOME"] = str(self.codex_home)
        try:
            completed = subprocess.run(
                args,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=self.timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise FleetError(
                f"command boundary failed for {args[0]}: {type(error).__name__}",
                status="command_failed",
            ) from error
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()[:1000]
            raise FleetError(
                f"command failed ({completed.returncode}): {' '.join(args)}: {detail}",
                status="command_failed",
            )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise FleetError(
                f"command returned invalid JSON: {' '.join(args)}",
                status="unsupported_runtime",
            ) from error
        if not isinstance(payload, dict):
            raise FleetError(
                f"command returned a non-object JSON value: {' '.join(args)}",
                status="unsupported_runtime",
            )
        return payload


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def digest_value(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def trusted_path(path: Path, *, label: str, status: str = "invalid_profile") -> Path:
    """Return a canonical path only when no lexical component is a symlink."""

    lexical = path.expanduser().absolute()
    current = Path(lexical.anchor)
    for part in lexical.parts[1:]:
        current /= part
        if current.is_symlink():
            raise FleetError(f"{label} contains a symbolic link: {current}", status=status)
    return lexical.resolve(strict=False)


def read_trusted_bytes(
    path: Path,
    *,
    label: str,
    status: str,
) -> bytes:
    """Read one regular file without following a substituted final symlink."""

    selected = trusted_path(path, label=label, status=status)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor: int | None = None
    try:
        descriptor = os.open(selected, flags)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise FleetError(f"{label} is not a regular file: {selected}", status=status)
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    except FleetError:
        raise
    except OSError as error:
        raise FleetError(f"{label} is unavailable: {selected}", status=status) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


def tree_digest(root: Path) -> str:
    root = trusted_path(root, label=f"identity tree {root}", status="identity_unavailable")
    if not root.is_dir():
        raise FleetError(f"tree is not a directory: {root}", status="identity_unavailable")
    digest = hashlib.sha256()
    entries: list[Path] = []
    try:
        for path in root.rglob("*"):
            relative = path.relative_to(root)
            if any(part in IGNORED_TREE_NAMES for part in relative.parts):
                continue
            if path.name.endswith(".pyc"):
                continue
            entries.append(path)
    except OSError as error:
        raise FleetError(
            f"identity tree cannot be traversed: {root}",
            status="identity_unavailable",
        ) from error
    for path in sorted(entries, key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        try:
            metadata = path.lstat()
            mode = stat.S_IMODE(metadata.st_mode)
            if stat.S_ISLNK(metadata.st_mode):
                kind = "symlink"
                target_text = os.readlink(path)
                target = Path(target_text)
                resolved_target = (
                    target if target.is_absolute() else path.parent / target
                ).resolve(strict=False)
                if not resolved_target.is_relative_to(root):
                    raise FleetError(
                        f"tree symbolic link escapes its identity root: {path}",
                        status="identity_unavailable",
                    )
                body = target_text.encode("utf-8")
            elif stat.S_ISDIR(metadata.st_mode):
                kind = "directory"
                body = b""
            elif stat.S_ISREG(metadata.st_mode):
                kind = "file"
                body = read_trusted_bytes(
                    path,
                    label=f"identity tree entry {relative}",
                    status="identity_unavailable",
                )
            else:
                raise FleetError(
                    f"unsupported tree entry: {path}",
                    status="identity_unavailable",
                )
        except FleetError:
            raise
        except OSError as error:
            raise FleetError(
                f"identity tree entry became unavailable: {path}",
                status="identity_unavailable",
            ) from error
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(kind.encode("ascii"))
        digest.update(b"\0")
        digest.update(f"{mode:o}".encode("ascii"))
        digest.update(b"\0")
        digest.update(body)
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def parse_projects(values: Iterable[str]) -> list[ProjectCandidate]:
    projects: list[ProjectCandidate] = []
    seen: set[str] = set()
    for value in values:
        project_id, separator, raw_path = value.partition("=")
        if not separator or not PROJECT_ID_PATTERN.fullmatch(project_id):
            raise FleetError(f"invalid project mapping: {value}; expected ID=PATH")
        if project_id in seen:
            raise FleetError(f"duplicate project id: {project_id}")
        path = trusted_path(Path(raw_path), label=f"project path for {project_id}")
        if not path.is_dir():
            raise FleetError(f"project path is not a directory: {path}")
        seen.add(project_id)
        projects.append(ProjectCandidate(project_id=project_id, path=path))
    return sorted(projects, key=lambda item: item.project_id)


def parse_named_values(values: Iterable[str], *, label: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        name, separator, selected = value.partition("=")
        if not separator or not name or not selected:
            raise FleetError(f"invalid {label}: {value}; expected NAME=VALUE")
        if name in result:
            raise FleetError(f"duplicate {label} for marketplace: {name}")
        result[name] = selected
    return result


def inventory(*, codex_home: Path, projects: list[ProjectCandidate]) -> dict[str, Any]:
    observed = runtime_inventory(codex_home=codex_home)
    marketplaces = observed["marketplaces"]
    plugins = observed["plugins"]
    skills = [
        {"name": skill, "plugin": plugin["selector"]}
        for plugin in plugins
        for skill in plugin["skills"]
    ]

    project_rows: list[dict[str, Any]] = []
    for project in projects:
        detected = [
            plugin["selector"]
            for plugin in plugins
            if plugin["projectAdapter"] == "devflow-v1" and _looks_like_devflow_project(project.path)
        ]
        detected_skills = [
            {"name": skill, "plugin": plugin["selector"]}
            for plugin in plugins
            if plugin["selector"] in detected
            for skill in plugin["skills"]
        ]
        project_rows.append(
            {
                "id": project.project_id,
                "path": str(project.path),
                "trusted": False,
                "adopted": False,
                "detectedPlugins": detected,
                "detectedSkills": detected_skills,
            }
        )

    return {
        "schemaVersion": SCHEMA_VERSION,
        "kind": "codex-fleet-inventory",
        "ok": False,
        "status": "candidates",
        "codexHome": str(codex_home),
        "marketplaces": marketplaces,
        "plugins": plugins,
        "skills": skills,
        "projects": project_rows,
        "actions": [],
        "results": [],
        "nextAction": "Review the candidates, then run bootstrap --apply to adopt exactly this inventory.",
    }


def runtime_inventory(*, codex_home: Path) -> dict[str, Any]:
    runner = CommandRunner(codex_home=codex_home)
    marketplaces_payload = runner.json(["codex", "plugin", "marketplace", "list", "--json"])
    plugins_payload = runner.json(["codex", "plugin", "list", "--available", "--json"])
    raw_marketplaces = marketplaces_payload.get("marketplaces")
    raw_installed = plugins_payload.get("installed")
    raw_available = plugins_payload.get("available", [])
    if not isinstance(raw_marketplaces, list) or not isinstance(raw_installed, list):
        raise FleetError("Codex inventory JSON has an unsupported shape", status="unsupported_runtime")
    if not isinstance(raw_available, list):
        raise FleetError("Codex available plugin inventory is not a list", status="unsupported_runtime")

    marketplaces = [_normalize_marketplace(item, codex_home) for item in raw_marketplaces]
    marketplaces = sorted(marketplaces, key=lambda item: item["name"])
    marketplace_names = {item["name"] for item in marketplaces}
    plugins = []
    for item in raw_installed:
        if not isinstance(item, dict) or not item.get("installed") or not item.get("enabled"):
            continue
        normalized = _normalize_plugin(item)
        if normalized["marketplace"] not in marketplace_names:
            raise FleetError(
                f"installed plugin references unknown marketplace: {normalized['selector']}",
                status="unsupported_runtime",
            )
        plugins.append(normalized)
    plugins.sort(key=lambda item: item["selector"])
    _ensure_unique(plugins, "selector", "plugin selector")

    return {
        "schemaVersion": SCHEMA_VERSION,
        "codexHome": str(codex_home),
        "marketplaces": marketplaces,
        "plugins": plugins,
    }


def bootstrap_preview(
    *,
    codex_home: Path,
    projects: list[ProjectCandidate],
    manifest_path: Path,
    lock_path: Path,
    device_path: Path,
    marketplace_git: dict[str, str] | None = None,
    marketplace_refs: dict[str, str] | None = None,
    marketplace_channels: dict[str, str] | None = None,
) -> dict[str, Any]:
    observed = inventory(codex_home=codex_home, projects=projects)
    used_marketplaces = {plugin["marketplace"] for plugin in observed["plugins"]}
    overrides = {
        "git": dict(marketplace_git or {}),
        "ref": dict(marketplace_refs or {}),
        "channel": dict(marketplace_channels or {}),
    }
    for kind, mapping in overrides.items():
        unknown = sorted(set(mapping).difference(used_marketplaces))
        if unknown:
            raise FleetError(
                f"{kind} override references an unmanaged marketplace: {', '.join(unknown)}",
                status="invalid_manifest",
            )
    marketplaces = []
    observed_by_name = {item["name"]: item for item in observed["marketplaces"]}
    for item in observed["marketplaces"]:
        if item["name"] not in used_marketplaces:
            continue
        name = item["name"]
        source_type = "git" if name in overrides["git"] else item["sourceType"]
        source = overrides["git"].get(name, item["source"])
        ref = overrides["ref"].get(name, item.get("ref"))
        channel = overrides["channel"].get(
            name,
            "development" if ref == "main" else (
                "device-local" if source_type == "local" else "stable"
            ),
        )
        if channel not in {"stable", "development", "device-local"}:
            raise FleetError(
                f"unsupported marketplace channel for {name}: {channel}",
                status="invalid_manifest",
            )
        if channel == "stable" and ref == "main":
            raise FleetError(
                f"stable marketplace {name} cannot target main; use a stable ref or development channel",
                status="invalid_manifest",
            )
        if source_type == "git" and not ref:
            raise FleetError(
                f"Git marketplace {name} requires an explicit ref",
                status="invalid_manifest",
            )
        portable_source = f"device://{name}" if source_type == "local" else source
        desired = {
            "name": name,
            "sourceType": source_type,
            "source": portable_source,
            "channel": channel,
        }
        if ref:
            desired["ref"] = ref
        marketplaces.append(desired)

    plugins = [
        {
            "selector": item["selector"],
            "enabled": True,
            "projectAdapter": item["projectAdapter"],
        }
        for item in observed["plugins"]
    ]
    project_rows = [
        {"id": item["id"], "plugins": list(item["detectedPlugins"])}
        for item in observed["projects"]
    ]
    manifest = {
        "schemaVersion": SCHEMA_VERSION,
        "profile": "default",
        "marketplaces": marketplaces,
        "plugins": plugins,
        "projects": project_rows,
    }
    manifest_sha = digest_value(manifest)
    device = {
        "schemaVersion": SCHEMA_VERSION,
        "profile": "default",
        "manifestSha256": manifest_sha,
        "codexHome": str(codex_home),
        "marketplaces": {
            item["name"]: {
                "source": item["source"],
                "root": item["root"],
                "trusted": True,
            }
            for item in observed["marketplaces"]
            if item["name"] in used_marketplaces and item["sourceType"] == "local"
        },
        "projects": {
            item["id"]: {"path": item["path"], "trusted": True}
            for item in observed["projects"]
        },
    }
    desired_by_name = {item["name"]: item for item in marketplaces}
    marketplace_locks = {}
    for name in sorted(used_marketplaces):
        observed_marketplace = observed_by_name[name]
        desired_marketplace = desired_by_name[name]
        if desired_marketplace["sourceType"] != observed_marketplace["sourceType"] or (
            desired_marketplace["sourceType"] == "git"
            and desired_marketplace["source"] != observed_marketplace["source"]
        ):
            raise FleetError(
                f"marketplace source alignment is required before bootstrap can lock {name}",
                status="source_alignment_required",
            )
        marketplace_locks[name] = _marketplace_lock(observed_marketplace, desired_marketplace)
    plugin_locks: dict[str, Any] = {}
    for plugin in observed["plugins"]:
        source = Path(plugin["sourcePath"]).resolve()
        cache = _cache_root(codex_home, plugin)
        source_sha = tree_digest(source)
        cache_sha = tree_digest(cache)
        if source_sha != cache_sha:
            raise FleetError(
                f"installed cache differs from marketplace source: {plugin['selector']}",
                status="identity_mismatch",
            )
        plugin_locks[plugin["selector"]] = {
            "version": plugin["version"],
            "treeSha256": cache_sha,
        }
    lock = {
        "schemaVersion": SCHEMA_VERSION,
        "manifestSha256": manifest_sha,
        "marketplaces": marketplace_locks,
        "plugins": plugin_locks,
    }
    project_markers = [
        {
            "path": str(project.path / ".codex-fleet" / "project.json"),
            "content": {
                "schemaVersion": SCHEMA_VERSION,
                "profile": "default",
                "projectId": project.project_id,
                "adopted": True,
                "managedPlugins": next(
                    row["plugins"] for row in project_rows if row["id"] == project.project_id
                ),
            },
        }
        for project in projects
    ]
    bootstrap_actions = [
        {"kind": "bootstrap-write", "path": str(manifest_path)},
        {"kind": "bootstrap-write", "path": str(lock_path)},
        {"kind": "bootstrap-write", "path": str(device_path)},
    ]
    bootstrap_actions.extend(
        {"kind": "project-adoption-write", "path": item["path"]}
        for item in project_markers
    )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "kind": "codex-fleet-bootstrap",
        "ok": False,
        "status": "preview",
        "apply": False,
        "targets": {
            "manifest": str(manifest_path),
            "lock": str(lock_path),
            "device": str(device_path),
        },
        "proposed": {
            "manifest": manifest,
            "lock": lock,
            "device": device,
            "projectMarkers": project_markers,
        },
        "actions": bootstrap_actions,
        "results": [],
        "nextAction": "Review the proposed bytes, then repeat bootstrap with --apply.",
    }


def apply_bootstrap(report: dict[str, Any]) -> dict[str, Any]:
    proposed = report["proposed"]
    targets = report["targets"]
    desired: list[tuple[Path, bytes, int]] = [
        (Path(targets["manifest"]), canonical_bytes(proposed["manifest"]), 0o644),
        (Path(targets["lock"]), canonical_bytes(proposed["lock"]), 0o644),
        (Path(targets["device"]), canonical_bytes(proposed["device"]), 0o600),
    ]
    desired.extend(
        (Path(item["path"]), canonical_bytes(item["content"]), 0o644)
        for item in proposed["projectMarkers"]
    )
    normalized = [
        trusted_path(path, label=f"bootstrap target {path}", status="target_conflict")
        for path, _, _ in desired
    ]
    if len({str(path) for path in normalized}) != len(normalized):
        raise FleetError("bootstrap target paths overlap", status="target_conflict")

    conflicts: list[str] = []
    unchanged: list[str] = []
    for (path, content, _mode), absolute in zip(desired, normalized, strict=True):
        if path.is_symlink() or absolute.is_symlink():
            conflicts.append(str(absolute))
            continue
        if absolute.exists():
            try:
                existing = read_trusted_bytes(
                    absolute,
                    label=f"bootstrap target {absolute}",
                    status="target_conflict",
                )
            except FleetError:
                conflicts.append(str(absolute))
                continue
            if existing != content:
                conflicts.append(str(absolute))
            else:
                unchanged.append(str(absolute))
    if conflicts:
        raise FleetError(
            "bootstrap targets already contain different data: " + ", ".join(sorted(conflicts)),
            status="target_conflict",
        )

    written: list[str] = []
    for (_path, content, mode), absolute in zip(desired, normalized, strict=True):
        if str(absolute) in unchanged:
            continue
        trusted_path(absolute, label=f"bootstrap target {absolute}", status="target_conflict")
        _atomic_write(absolute, content, mode=mode)
        written.append(str(absolute))

    applied = dict(report)
    applied.update(
        {
            "ok": True,
            "status": "adopted",
            "apply": True,
            "writtenPaths": sorted(written),
            "unchangedPaths": sorted(unchanged),
            "results": [
                {
                    "kind": "bootstrap-write",
                    "path": str(path),
                    "status": "unchanged" if str(path) in unchanged else "written",
                }
                for path in normalized
            ],
            "nextAction": "Run codex-fleet sync to review the first sealed convergence plan.",
        }
    )
    return applied


def _normalize_marketplace(item: Any, codex_home: Path) -> dict[str, Any]:
    if not isinstance(item, dict) or not isinstance(item.get("name"), str):
        raise FleetError("Codex marketplace record has an unsupported shape", status="unsupported_runtime")
    source_record = item.get("marketplaceSource")
    if not isinstance(source_record, dict):
        source_record = {}
    source_type = str(source_record.get("sourceType") or "unknown")
    source = str(source_record.get("source") or item.get("root") or "")
    if not source:
        raise FleetError(f"marketplace source is unavailable: {item['name']}", status="identity_unavailable")
    config = _marketplace_config(codex_home, item["name"])
    selected_source_type = str(config.get("source_type") or source_type)
    selected_source = str(config.get("source") or source)
    if selected_source_type == "local":
        selected_source = str(
            trusted_path(
                Path(selected_source),
                label=f"marketplace source {item['name']}",
                status="identity_unavailable",
            )
        )
    root = trusted_path(
        Path(str(item.get("root") or source)),
        label=f"marketplace root {item['name']}",
        status="identity_unavailable",
    )
    result: dict[str, Any] = {
        "name": item["name"],
        "root": str(root),
        "sourceType": selected_source_type,
        "source": selected_source,
        "managed": False,
    }
    if config.get("ref"):
        result["ref"] = str(config["ref"])
    if config.get("last_revision"):
        result["revision"] = str(config["last_revision"])
    return result


def _marketplace_config(codex_home: Path, name: str) -> dict[str, Any]:
    path = codex_home / "config.toml"
    if not path.is_file():
        return {}
    try:
        import tomllib

        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    marketplaces = payload.get("marketplaces", {})
    value = marketplaces.get(name, {}) if isinstance(marketplaces, dict) else {}
    return value if isinstance(value, dict) else {}


def _normalize_plugin(item: dict[str, Any]) -> dict[str, Any]:
    selector = item.get("pluginId")
    name = item.get("name")
    marketplace = item.get("marketplaceName")
    version = item.get("version")
    source = item.get("source")
    source_path = source.get("path") if isinstance(source, dict) else None
    if not all(isinstance(value, str) and value for value in (selector, name, marketplace, version, source_path)):
        raise FleetError("Codex installed plugin record has an unsupported shape", status="unsupported_runtime")
    if selector != f"{name}@{marketplace}":
        raise FleetError(f"plugin identity is inconsistent: {selector}", status="unsupported_runtime")
    resolved_source = trusted_path(
        Path(source_path),
        label=f"plugin source {selector}",
        status="identity_unavailable",
    )
    return {
        "selector": selector,
        "name": name,
        "marketplace": marketplace,
        "version": version,
        "installed": True,
        "enabled": True,
        "sourcePath": str(resolved_source),
        "skills": _plugin_skills(resolved_source),
        "projectAdapter": "devflow-v1" if name == "dev-flow" else None,
    }


def _plugin_skills(plugin_root: Path) -> list[str]:
    skills_root = plugin_root / "skills"
    if skills_root.is_symlink():
        raise FleetError(
            f"packaged Skills root contains a symbolic link: {skills_root}",
            status="identity_unavailable",
        )
    if not skills_root.exists():
        return []
    try:
        if skills_root.is_symlink() or not skills_root.is_dir():
            raise FleetError(
                f"packaged Skills root is not a trusted directory: {skills_root}",
                status="identity_unavailable",
            )
        entries = list(skills_root.rglob("*"))
        linked = next((entry for entry in entries if entry.is_symlink()), None)
        if linked is not None:
            raise FleetError(
                f"packaged Skill content contains a symbolic link: {linked}",
                status="identity_unavailable",
            )
        names: list[str] = []
        for candidate in skills_root.iterdir():
            if not candidate.is_dir():
                continue
            skill_file = candidate / "SKILL.md"
            if skill_file.is_file():
                names.append(candidate.name)
    except FleetError:
        raise
    except OSError as error:
        raise FleetError(
            f"packaged Skills cannot be inspected: {skills_root}",
            status="identity_unavailable",
        ) from error
    return sorted(names)


def _looks_like_devflow_project(path: Path) -> bool:
    return any(
        candidate.exists()
        for candidate in (
            path / ".planning" / "devflow" / "STATE.md",
            path / ".dev-flow.json",
        )
    )


def _cache_root(codex_home: Path, plugin: dict[str, Any]) -> Path:
    return (
        codex_home
        / "plugins"
        / "cache"
        / plugin["marketplace"]
        / plugin["name"]
        / plugin["version"]
    )


def _marketplace_lock(item: dict[str, Any], desired: dict[str, Any]) -> dict[str, Any]:
    result = {
        "sourceType": desired["sourceType"],
        "source": desired["source"],
    }
    if desired.get("ref"):
        result["ref"] = desired["ref"]
    if desired["sourceType"] == "git":
        revision = item.get("revision")
        if not isinstance(revision, str) or not revision:
            raise FleetError(
                f"Git marketplace revision is unavailable: {item['name']}",
                status="identity_unavailable",
            )
        result["revision"] = revision
    elif item["sourceType"] == "local":
        result["treeSha256"] = tree_digest(Path(item["root"]))
    return result


def _atomic_write(path: Path, content: bytes, *, mode: int) -> None:
    path = trusted_path(path, label=f"write target {path}", status="write_failed")
    temporary: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except OSError as error:
        raise FleetError(f"atomic write failed: {path}", status="write_failed") from error
    finally:
        if temporary is not None:
            try:
                if os.path.lexists(temporary):
                    temporary.unlink()
            except OSError:
                pass


def _ensure_unique(records: Iterable[dict[str, Any]], key: str, label: str) -> None:
    seen: set[str] = set()
    for record in records:
        value = str(record[key])
        if value in seen:
            raise FleetError(f"duplicate {label}: {value}", status="unsupported_runtime")
        seen.add(value)
