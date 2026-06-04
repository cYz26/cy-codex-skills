#!/usr/bin/env python3
"""Preflight and context audit for the Lark Feishu Ops plugin."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


HOME = Path.home()
SKILL_LOCK = HOME / ".agents" / ".skill-lock.json"
GLOBAL_SKILLS_DIR = HOME / ".agents" / "skills"
PREFERRED_PROJECT_SKILL = "lark-feishu-ops"
UPDATE_CHECK_POLICIES = {"daily", "always", "never"}


def run_command(command: list[str], timeout: int = 30) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        return {
            "command": command,
            "ok": False,
            "exit_code": None,
            "stdout": "",
            "stderr": str(exc),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "ok": False,
            "exit_code": None,
            "stdout": exc.stdout or "",
            "stderr": f"timed out after {timeout}s",
        }

    return {
        "command": command,
        "ok": completed.returncode == 0,
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def parse_json_output(result: dict[str, Any]) -> Any | None:
    stdout = result.get("stdout") or ""
    if not stdout:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def local_date(now: datetime | None = None) -> str:
    current = now or datetime.now().astimezone()
    return current.date().isoformat()


def default_update_cache_path() -> Path:
    cache_home = os.environ.get("XDG_CACHE_HOME")
    root = Path(cache_home).expanduser() if cache_home else HOME / ".cache"
    return root / "lark-feishu-ops" / "update-check.json"


def read_update_check_cache(cache_path: Path | str | None = None) -> dict[str, Any] | None:
    path = Path(cache_path).expanduser() if cache_path is not None else default_update_cache_path()
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def write_update_check_cache(payload: dict[str, Any], cache_path: Path | str | None = None) -> dict[str, Any]:
    path = Path(cache_path).expanduser() if cache_path is not None else default_update_cache_path()
    record = {
        "checked_local_date": local_date(),
        "checked_at": datetime.now().astimezone().isoformat(),
        "action": payload.get("action"),
        "current_version": payload.get("current_version"),
        "latest_version": payload.get("latest_version"),
        "ok": payload.get("ok", True),
        "payload": payload,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        record["cache_path"] = str(path)
        record["write_ok"] = True
    except OSError as exc:
        record["cache_path"] = str(path)
        record["write_ok"] = False
        record["write_error"] = str(exc)
    return record


def current_update_cache(cache_path: Path | str | None = None) -> dict[str, Any] | None:
    record = read_update_check_cache(cache_path)
    if not record:
        return None
    if record.get("checked_local_date") != local_date():
        return None
    payload = record.get("payload")
    if not isinstance(payload, dict):
        payload = {
            "action": record.get("action"),
            "ok": record.get("ok"),
            "current_version": record.get("current_version"),
            "latest_version": record.get("latest_version"),
        }
        record["payload"] = payload
    return record


def update_payload_requires_confirmation(payload: Any) -> bool:
    return isinstance(payload, dict) and payload.get("action") not in (None, "already_up_to_date")


def build_update_action(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "lark_cli_update",
        "requires_confirmation": True,
        "command": ["lark-cli", "update", "--json"],
        "current_version": payload.get("current_version"),
        "latest_version": payload.get("latest_version"),
        "followup_command": [
            "python3",
            "plugins/lark-feishu-ops/scripts/lark_feishu_ops_sync.py",
            "--after-cli-update",
            "--json",
        ],
    }


def load_skill_lock_sources() -> dict[str, str]:
    if not SKILL_LOCK.is_file():
        return {}
    try:
        payload = json.loads(SKILL_LOCK.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    skills = payload.get("skills")
    if not isinstance(skills, dict):
        return {}
    sources: dict[str, str] = {}
    for name, item in skills.items():
        if isinstance(name, str) and isinstance(item, dict):
            source = item.get("source")
            if isinstance(source, str):
                sources[name] = source
    return sources


def is_official_lark_skill(item: dict[str, Any], sources: dict[str, str]) -> bool:
    name = item.get("name")
    path = item.get("path")
    if not isinstance(name, str) or not name.startswith("lark-"):
        return False
    if sources.get(name) == "larksuite/cli":
        return True
    if isinstance(path, str):
        expected_prefix = str(GLOBAL_SKILLS_DIR / "lark-")
        return path.startswith(expected_prefix)
    return False


def normalize_agents(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item).strip().lower() for item in value if str(item).strip()}


def read_skill_frontmatter_name(skill_file: Path) -> str | None:
    try:
        lines = skill_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            return None
        if stripped.startswith("name:"):
            value = stripped.split(":", 1)[1].strip()
            return value.strip("\"'") or None
    return None


def project_skill_record(skill_file: Path) -> dict[str, Any]:
    skill_dir = skill_file.parent
    name = read_skill_frontmatter_name(skill_file) or skill_dir.name
    return {
        "name": name,
        "directory": skill_dir.name,
        "path": str(skill_file),
        "source": "project",
    }


def audit_project_lark_skills(repo: Path | str) -> dict[str, Any]:
    repo_path = Path(repo).expanduser().resolve()
    skills_dir = repo_path / ".codex" / "skills"
    preferred: list[dict[str, Any]] = []
    scattered: list[dict[str, Any]] = []

    if skills_dir.is_dir():
        for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
            record = project_skill_record(skill_file)
            name = str(record["name"])
            directory = str(record["directory"])
            is_lark = name.startswith("lark-") or directory.startswith("lark-")
            if not is_lark:
                continue
            if name == PREFERRED_PROJECT_SKILL or directory == PREFERRED_PROJECT_SKILL:
                preferred.append(record)
            else:
                scattered.append(record)

    actions = [
        {
            "id": f"remove-project-lark-skill-{item['directory']}",
            "type": "remove_project_lark_skill",
            "title": f"Remove project-local scattered Lark skill {item['name']}",
            "skill": item["name"],
            "path": str(Path(str(item["path"])).parent),
            "reason": (
                "Project-local scattered lark-* skills increase main-agent context; "
                "route Feishu/Lark operations through lark-feishu-ops instead."
            ),
            "safety": "advisory",
            "requiresAuthorization": True,
        }
        for item in scattered
    ]

    recommendations: list[str] = []
    if scattered:
        recommendations.append(
            "Remove or disable project-local scattered lark-* skills from the main-agent "
            "context and route Feishu/Lark work through lark-feishu-ops."
        )
        if not preferred:
            recommendations.append(
                "Add or enable lark-feishu-ops as the single project-local Feishu/Lark entry point."
            )
    elif preferred:
        recommendations.append(
            "Project-local lark-feishu-ops route is present; no scattered project Lark skill cleanup is needed."
        )
    else:
        recommendations.append(
            "No project-local Lark skills found; keep Feishu/Lark operations routed through "
            "lark-feishu-ops when needed."
        )

    suggested_configuration = {
        "preferred_entrypoint": PREFERRED_PROJECT_SKILL,
        "main_agent_policy": "Keep scattered official lark-* skills out of the project-local main-agent context.",
        "dispatch_policy": (
            "Use direct main-agent lark-cli for bounded low-risk reads; escalate side effects, "
            "cross-domain work, auth/profile complexity, raw OpenAPI, broad pagination, and "
            "explicit FeishuOps requests to FeishuOps."
        ),
        "subagent_policy": (
            "FeishuOps lazy-loads official lark-* guidance only when the dispatch policy chooses "
            "subagent execution."
        ),
        "project_skill_state": (
            "scattered_present"
            if scattered
            else "preferred_present"
            if preferred
            else "no_project_lark_skills"
        ),
    }

    return {
        "status": "WARN" if scattered else "PASS",
        "repo": str(repo_path),
        "skills_dir": str(skills_dir),
        "project_lark_feishu_ops": preferred,
        "project_scattered_lark_skills": scattered,
        "suggested_configuration": suggested_configuration,
        "recommendations": recommendations,
        "actions": actions,
    }


def check_lark_cli(
    skip_update_check: bool,
    offline: bool,
    update_check_policy: str = "daily",
    force_update_check: bool = False,
    cache_path: Path | str | None = None,
) -> dict[str, Any]:
    if update_check_policy not in UPDATE_CHECK_POLICIES:
        raise ValueError(f"unsupported update_check_policy: {update_check_policy}")

    executable = shutil.which("lark-cli")
    check: dict[str, Any] = {
        "status": "PASS" if executable else "FAIL",
        "path": executable,
        "version": None,
        "version_check": None,
        "doctor": None,
        "auth_status": None,
        "update_check": None,
        "update_action": None,
        "recommendations": [],
    }

    if executable is None:
        check["recommendations"].append(
            "Install lark-cli first. See https://github.com/larksuite/cli for official installation options."
        )
        return check

    version_result = run_command(["lark-cli", "--version"], timeout=15)
    check["version_check"] = compact_result(version_result)
    if version_result["ok"]:
        check["version"] = version_result["stdout"]
    else:
        check["status"] = "FAIL"

    doctor_command = ["lark-cli", "doctor"]
    if offline:
        doctor_command.append("--offline")
    doctor_result = run_command(doctor_command, timeout=30)
    check["doctor"] = compact_result(doctor_result)
    if not doctor_result["ok"]:
        check["status"] = "WARN" if check["status"] == "PASS" else check["status"]
        check["recommendations"].append(
            "Run `lark-cli doctor` and repair local config/auth issues before platform writes."
        )

    auth_result = run_command(["lark-cli", "auth", "status"], timeout=20)
    check["auth_status"] = compact_result(auth_result)
    if not auth_result["ok"]:
        check["status"] = "WARN" if check["status"] == "PASS" else check["status"]
        check["recommendations"].append(
            "Run `lark-cli auth status` and complete login/scope setup before protected operations."
        )

    if skip_update_check or offline or update_check_policy == "never":
        check["update_check"] = {
            "skipped": True,
            "reason": "offline, skip_update_check, or never policy requested",
            "policy": update_check_policy,
        }
        check["recommendations"].append(
            "Keep lark-cli updated; run `lark-cli update --check --json` periodically."
        )
    else:
        cached = None if force_update_check or update_check_policy == "always" else current_update_cache(cache_path)
        if cached is not None:
            update_payload = cached["payload"]
            check["update_check"] = {
                "cached": True,
                "policy": update_check_policy,
                "cache_path": str(Path(cache_path).expanduser() if cache_path else default_update_cache_path()),
                "ok": True,
                "exit_code": 0,
                "payload": update_payload,
                "stderr": "",
            }
        else:
            update_result = run_command(["lark-cli", "update", "--check", "--json"], timeout=45)
            update_payload = parse_json_output(update_result)
            check["update_check"] = {
                "command": update_result["command"],
                "cached": False,
                "policy": update_check_policy,
                "ok": update_result["ok"],
                "exit_code": update_result["exit_code"],
                "payload": update_payload,
                "stderr": update_result["stderr"],
            }
            if update_result["ok"] and isinstance(update_payload, dict):
                check["update_check"]["cache"] = write_update_check_cache(update_payload, cache_path)

            if not update_result["ok"]:
                check["status"] = "WARN" if check["status"] == "PASS" else check["status"]
                check["recommendations"].append(
                    "Could not complete update check; retry `lark-cli update --check --json` later."
                )
                return check

        if update_payload_requires_confirmation(update_payload):
            check["status"] = "WARN" if check["status"] == "PASS" else check["status"]
            check["update_action"] = build_update_action(update_payload)
            check["recommendations"].append(
                "Run `lark-cli update` only after explicit confirmation; it is a high-risk-write command."
            )

    return check


def compact_result(result: dict[str, Any], *, max_output: int = 1200) -> dict[str, Any]:
    stdout = result.get("stdout") or ""
    stderr = result.get("stderr") or ""
    return {
        "command": result.get("command"),
        "ok": result.get("ok"),
        "exit_code": result.get("exit_code"),
        "stdout": stdout[:max_output],
        "stderr": stderr[:max_output],
    }


def list_global_skills() -> dict[str, Any]:
    if shutil.which("npx") is None:
        return {
            "status": "WARN",
            "npx_path": None,
            "raw": None,
            "skills": [],
            "error": "`npx` not found; cannot inspect global skills via skills CLI.",
        }
    result = run_command(["npx", "skills", "ls", "-g", "--json"], timeout=60)
    payload = parse_json_output(result)
    if not result["ok"] or not isinstance(payload, list):
        return {
            "status": "WARN",
            "npx_path": shutil.which("npx"),
            "raw": compact_result(result),
            "skills": [],
            "error": "Could not parse `npx skills ls -g --json`.",
        }
    return {
        "status": "PASS",
        "npx_path": shutil.which("npx"),
        "raw": compact_result(result, max_output=200),
        "skills": payload,
        "error": None,
    }


def audit_global_lark_skills() -> dict[str, Any]:
    listing = list_global_skills()
    sources = load_skill_lock_sources()
    official: list[dict[str, Any]] = []
    codex_effective: list[dict[str, Any]] = []

    for item in listing.get("skills", []):
        if not isinstance(item, dict) or not is_official_lark_skill(item, sources):
            continue
        normalized_agents = normalize_agents(item.get("agents"))
        record = {
            "name": item.get("name"),
            "path": item.get("path"),
            "agents": item.get("agents", []),
            "source": sources.get(str(item.get("name"))),
        }
        official.append(record)
        if "codex" in normalized_agents:
            codex_effective.append(record)

    status = "PASS"
    if listing["status"] != "PASS":
        status = "WARN"
    elif codex_effective:
        status = "WARN"

    return {
        "status": status,
        "official_global_lark_skills": official,
        "codex_effective_official_lark_skills": codex_effective,
        "recommendation": (
            "Unload official larksuite/cli lark-* skills from Codex and route Feishu/Lark "
            "work through the plugin subagent."
            if codex_effective
            else "No official larksuite/cli lark-* skills are globally active for Codex."
        ),
        "listing": {
            "status": listing["status"],
            "npx_path": listing.get("npx_path"),
            "error": listing.get("error"),
        },
    }


def apply_codex_global_unload(targets: list[dict[str, Any]]) -> dict[str, Any]:
    if shutil.which("npx") is None:
        return {
            "status": "FAIL",
            "operations": [],
            "error": "`npx` not found; cannot unload skills.",
        }

    operations: list[dict[str, Any]] = []
    for target in targets:
        name = target.get("name")
        if not isinstance(name, str) or not name:
            continue
        command = ["npx", "skills", "remove", "-g", "-a", "codex", "-s", name, "-y"]
        result = run_command(command, timeout=90)
        operations.append(compact_result(result, max_output=1600))

    after = audit_global_lark_skills()
    still_effective = after.get("codex_effective_official_lark_skills") or []
    status = "PASS" if not still_effective and all(op.get("ok") for op in operations) else "FAIL"
    return {
        "status": status,
        "operations": operations,
        "verification": after,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    lark_cli = check_lark_cli(
        args.skip_update_check,
        args.offline,
        update_check_policy=args.update_check_policy,
        force_update_check=args.force_update_check,
        cache_path=args.update_cache_path,
    )
    global_audit = audit_global_lark_skills()
    project_audit = audit_project_lark_skills(args.repo) if getattr(args, "repo", None) else None

    remediation = None
    if args.apply_codex_global_unload:
        remediation = apply_codex_global_unload(global_audit["codex_effective_official_lark_skills"])
        global_audit = audit_global_lark_skills()

    statuses = [lark_cli["status"], global_audit["status"]]
    if project_audit is not None:
        statuses.append(project_audit["status"])
    if remediation is not None:
        statuses.append(remediation["status"])

    if "FAIL" in statuses:
        overall = "FAIL"
    elif args.strict and any(status != "PASS" for status in statuses):
        overall = "FAIL"
    elif any(status != "PASS" for status in statuses):
        overall = "WARN"
    else:
        overall = "PASS"

    recommendations: list[str] = []
    recommendations.extend(lark_cli.get("recommendations", []))
    if global_audit["codex_effective_official_lark_skills"]:
        recommendations.append(
            "Run this doctor with `--apply-codex-global-unload`, then start a new Codex thread."
        )
    elif args.apply_codex_global_unload:
        recommendations.append("Global official lark-* skills are no longer active for Codex.")
    if project_audit is not None:
        recommendations.extend(project_audit.get("recommendations", []))

    checks = {
        "lark_cli": lark_cli,
        "global_lark_skills": global_audit,
    }
    if project_audit is not None:
        checks["project_lark_skills"] = project_audit

    return {
        "status": overall,
        "checks": checks,
        "remediation": remediation,
        "recommendations": recommendations,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Lark Feishu Ops dependencies and context load.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    parser.add_argument("--strict", action="store_true", help="Fail if any warning remains.")
    parser.add_argument("--repo", help="Repository path to inspect for project-local Lark skills.")
    parser.add_argument("--offline", action="store_true", help="Skip network-sensitive checks.")
    parser.add_argument("--skip-update-check", action="store_true", help="Skip lark-cli update check.")
    parser.add_argument(
        "--update-check-policy",
        choices=sorted(UPDATE_CHECK_POLICIES),
        default="daily",
        help="How often to run `lark-cli update --check --json`.",
    )
    parser.add_argument("--force-update-check", action="store_true", help="Bypass the daily update-check cache.")
    parser.add_argument("--update-cache-path", help=argparse.SUPPRESS)
    parser.add_argument(
        "--apply-codex-global-unload",
        action="store_true",
        help="Remove official larksuite/cli global lark-* skills from Codex only, then verify.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"status: {report['status']}")
        for recommendation in report.get("recommendations", []):
            print(f"- {recommendation}")
    return 0 if report["status"] == "PASS" or (report["status"] == "WARN" and not args.strict) else 1


if __name__ == "__main__":
    raise SystemExit(main())
