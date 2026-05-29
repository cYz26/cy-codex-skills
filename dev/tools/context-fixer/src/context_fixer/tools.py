from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

PROFILE_NAMES = ("quick", "monitor", "trace", "full")


@dataclass(frozen=True)
class ManagedTool:
    key: str
    name: str
    executable_candidates: tuple[str, ...]
    profiles: tuple[str, ...]
    required_profiles: tuple[str, ...] = ()
    artifact_kind: str | None = None
    artifact_name: str | None = None
    stdout_artifact: bool = True
    sensitive: bool = False
    guidance: str = ""
    command_builder: Callable[[str, Path, Path], list[str]] | None = None

    def command(self, executable: str, project: Path, run_dir: Path) -> list[str]:
        if self.command_builder:
            return self.command_builder(executable, project, run_dir)
        return [executable, "--version"]


def managed_tool_registry() -> tuple[ManagedTool, ...]:
    return (
        ManagedTool(
            key="abtop",
            name="abtop",
            executable_candidates=("abtop",),
            profiles=("monitor", "full"),
            artifact_kind="abtop",
            artifact_name="abtop.json",
            guidance="Install abtop to collect live context pressure snapshots.",
            command_builder=lambda exe, _project, _run_dir: [exe, "--once", "--json"],
        ),
        ManagedTool(
            key="ccusage",
            name="ccusage",
            executable_candidates=("ccusage",),
            profiles=("full",),
            artifact_kind="ccusage",
            artifact_name="ccusage.json",
            guidance="Install ccusage to collect Codex usage and cost summaries.",
            command_builder=lambda exe, _project, _run_dir: [exe, "codex", "session", "--json"],
        ),
        ManagedTool(
            key="claude-tap",
            name="claude-tap",
            executable_candidates=("claude-tap",),
            profiles=("trace", "full"),
            artifact_kind="trace",
            stdout_artifact=False,
            sensitive=True,
            guidance="Install claude-tap for request-level trace capture in trace-enabled profiles, or pass an existing trace with --trace.",
            command_builder=lambda exe, _project, _run_dir: [exe, "--version"],
        ),
        ManagedTool(
            key="otel",
            name="Codex OTel exporter",
            executable_candidates=("codex-otel", "otel-cli"),
            profiles=("full",),
            artifact_kind="otel",
            artifact_name="otel.jsonl",
            sensitive=True,
            guidance="Configure a local OTel exporter if Codex observability artifacts are available.",
            command_builder=lambda exe, _project, _run_dir: [exe, "export", "--format", "jsonl"],
        ),
        ManagedTool(
            key="rtk",
            name="RTK",
            executable_candidates=("rtk",),
            profiles=("full",),
            guidance="Install RTK to reduce future shell-output context noise.",
        ),
    )


def tools_for_profile(profile: str) -> tuple[ManagedTool, ...]:
    if profile not in PROFILE_NAMES:
        raise ValueError(f"unknown profile: {profile}")
    return tuple(tool for tool in managed_tool_registry() if profile in tool.profiles)


def tool_status(profile: str | None = None, project: Path | str | None = None) -> dict[str, Any]:
    project_path = Path(project).expanduser().resolve() if project is not None else None
    selected = managed_tool_registry() if profile in (None, "all") else tools_for_profile(profile)
    return {
        tool.key: availability_record(tool, profile, project_path)
        for tool in selected
    }


def availability_record(tool: ManagedTool, profile: str | None = None, project: Path | None = None) -> dict[str, Any]:
    executable, source = find_executable(tool, project)
    return {
        "name": tool.name,
        "status": "available" if executable else "missing",
        "executable": executable,
        "source": source,
        "profiles": list(tool.profiles),
        "required": bool(profile and profile in tool.required_profiles),
        "artifact_kind": tool.artifact_kind,
        "sensitive": tool.sensitive,
        "guidance": tool.guidance,
    }


def find_executable(tool: ManagedTool, project: Path | None = None) -> tuple[str | None, str | None]:
    for candidate in tool.executable_candidates:
        found = shutil.which(candidate)
        if found:
            return found, "path"
    for directory in project_tool_dirs(project):
        for candidate in tool.executable_candidates:
            found = directory / candidate
            if found.exists() and found.is_file():
                return str(found), "project"
    return None, None


def project_tool_dirs(project: Path | None) -> tuple[Path, ...]:
    if project is None:
        return ()
    return (
        project / ".context-fixer" / "tools" / "bin",
        project / ".context-fixer" / "tools" / "node_modules" / ".bin",
        project / ".context-fixer" / "claude-tap-venv" / "bin",
        project / ".venv" / "bin",
    )


class ManagedToolRunner:
    def __init__(
        self,
        project: Path,
        timeout: int = 30,
        run_id: str | None = None,
        supplied_artifacts: dict[str, list[Path]] | None = None,
    ):
        self.project = project.expanduser().resolve()
        self.timeout = timeout
        self.run_id = run_id or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
        self.run_dir = self.project / ".context-fixer" / "runs" / self.run_id
        self.supplied_artifacts = supplied_artifacts or {}

    def run_profile(self, profile: str) -> dict[str, Any]:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        tool_results = {}
        artifacts = {}
        for tool in tools_for_profile(profile):
            result = self.run_tool(tool, profile)
            tool_results[tool.key] = result
            if result.get("artifact"):
                artifacts[tool.key] = {
                    "kind": tool.artifact_kind,
                    "path": result.get("artifact"),
                    "bytes": result.get("artifact_bytes", 0),
                    "sha256": result.get("artifact_sha256"),
                    "sensitive": tool.sensitive,
                }
        return {
            "profile": profile,
            "run_id": self.run_id,
            "run_dir": str(self.run_dir),
            "tools": tool_results,
            "artifacts": artifacts,
        }

    def run_tool(self, tool: ManagedTool, profile: str) -> dict[str, Any]:
        executable, source = find_executable(tool, self.project)
        required = profile in tool.required_profiles
        base = {
            "name": tool.name,
            "required": required,
            "profiles": list(tool.profiles),
            "artifact_kind": tool.artifact_kind,
            "sensitive": tool.sensitive,
        }
        reused = self.reused_artifact(tool)
        if reused:
            result = {
                **base,
                "status": "reused",
                "executable": executable,
                "source": source,
                "artifact": str(reused),
                "artifact_bytes": reused.stat().st_size,
                "artifact_sha256": file_hash(reused),
            }
            write_status(self.run_dir / f"{tool.key}.status.json", result)
            return result
        if not executable:
            return {**base, "status": "missing", "guidance": tool.guidance}
        command = tool.command(executable, self.project, self.run_dir)
        try:
            completed = subprocess.run(command, cwd=str(self.project), capture_output=True, timeout=self.timeout)
        except subprocess.TimeoutExpired as exc:
            return {
                **base,
                "status": "failed",
                "executable": executable,
                "source": source,
                "exit_code": None,
                "stdout_bytes": len(exc.stdout or b""),
                "stderr_bytes": len(exc.stderr or b""),
                "error": "timeout",
            }
        stdout = bytes(completed.stdout or b"")
        stderr = bytes(completed.stderr or b"")
        result = {
            **base,
            "status": "ok" if completed.returncode == 0 else "failed",
            "executable": executable,
            "source": source,
            "exit_code": int(completed.returncode),
            "stdout_bytes": len(stdout),
            "stderr_bytes": len(stderr),
            "stdout_sha256": short_hash(stdout),
            "stderr_sha256": short_hash(stderr),
        }
        if tool.stdout_artifact and tool.artifact_name and stdout:
            artifact = self.run_dir / tool.artifact_name
            artifact.write_bytes(stdout)
            result.update(
                {
                    "artifact": str(artifact),
                    "artifact_bytes": artifact.stat().st_size,
                    "artifact_sha256": file_hash(artifact),
                }
            )
        write_status(self.run_dir / f"{tool.key}.status.json", result)
        return result

    def reused_artifact(self, tool: ManagedTool) -> Path | None:
        if not tool.artifact_kind:
            return None
        for candidate in self.supplied_artifacts.get(tool.artifact_kind, []):
            path = candidate.expanduser().resolve()
            if path.exists() and path.is_file():
                return path
        return None


def write_status(path: Path, result: dict[str, Any]) -> None:
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def short_hash(data: bytes) -> str | None:
    if not data:
        return None
    return hashlib.sha256(data).hexdigest()[:24]


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:24]
