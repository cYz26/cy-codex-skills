from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from workflow_context_config import read_config
from workflow_dependency_catalog import STRICT_RECOMMENDED_SUPERPOWERS_SKILLS


SUPERPOWERS_MINIMUM_COMPATIBLE = "5.1.3"
SUPERPOWERS_RECOMMENDED = "6.0.3"
SUPERPOWERS_STRICT_REQUIRES = "6.0.3"


def add_skill_checks(
    checks: list[dict[str, Any]],
    codex_home: Path,
    plugin: str,
    skills: list[str],
    required: bool,
) -> None:
    for skill in skills:
        add_skill_check(checks, codex_home, plugin, skill, required)


def check_plugin_activation(
    checks: list[dict[str, Any]],
    config: dict[str, Any],
    plugin: str,
    label: str,
    required: bool,
) -> None:
    enabled = plugin_enabled(config, plugin)
    detail = "enabled" if enabled else "missing/disabled"
    add_check(checks, f"{label}: {plugin}", enabled, required, detail)


def check_global_plugin_inactive(
    checks: list[dict[str, Any]],
    config: dict[str, Any],
    plugin: str,
    required: bool = True,
) -> None:
    enabled = plugin_enabled(config, plugin)
    detail = "globally enabled" if enabled else "not globally enabled"
    add_check(checks, f"global plugin inactive: {plugin}", not enabled, required, detail)


def check_plugin_installed(
    checks: list[dict[str, Any]],
    codex_home: Path,
    plugin: str,
    label: str,
    required: bool,
) -> None:
    installed = plugin_installed(codex_home, plugin)
    detail = "installed" if installed else "missing"
    add_check(checks, f"{label}: {plugin}", installed, required, detail)


def plugin_enabled(config: dict[str, Any], plugin: str) -> bool:
    plugins = config.get("plugins", {})
    for name, settings in plugins.items():
        if name.startswith(f"{plugin}@") and settings.get("enabled") is True:
            return True
    return False


def plugin_installed(codex_home: Path, plugin: str) -> bool:
    return bool(find_plugin_roots(codex_home, plugin))


def add_skill_check(
    checks: list[dict[str, Any]],
    codex_home: Path,
    plugin: str,
    skill: str,
    required: bool,
) -> None:
    path = find_skill(codex_home, plugin, skill)
    detail = str(path) if path else "missing"
    add_check(checks, f"external skill available: {plugin}:{skill}", path is not None, required, detail)


def find_skill(codex_home: Path, plugin: str, skill: str) -> Path | None:
    for root in find_plugin_roots(codex_home, plugin):
        path = root / "skills" / skill / "SKILL.md"
        if path.exists():
            return path
    cache = codex_home / "plugins" / "cache"
    if cache.exists():
        for path in cache.rglob(f"skills/{skill}/SKILL.md"):
            if plugin in path.parts:
                return path
    return None


def superpowers_governance_report(codex_home: Path, strict: bool = False) -> dict[str, Any]:
    roots = find_plugin_roots(codex_home, "superpowers")
    if not roots:
        return {
            "status": "superpowers_missing",
            "version": None,
            "sourceChannel": None,
            "compatibility": "missing",
            "requiredSkills": {},
            "strictRecommendedSkills": {},
            "sessionStartHookPresent": False,
            "sessionStartHookTrusted": False,
            "nextAction": "Install and enable Superpowers before strict DevFlow execution.",
        }
    root = select_plugin_root(roots)
    manifest = read_json(root / ".codex-plugin" / "plugin.json")
    version = str(manifest.get("version") or "unknown")
    source_channel = source_channel_for_root(codex_home, root)
    required_skills = {
        skill: find_skill(codex_home, "superpowers", skill) is not None
        for skill in [
            "using-superpowers",
            "brainstorming",
            "writing-plans",
            "test-driven-development",
            "verification-before-completion",
        ]
    }
    strict_skills = {
        skill: find_skill(codex_home, "superpowers", skill) is not None
        for skill in STRICT_RECOMMENDED_SUPERPOWERS_SKILLS
    }
    session_start_present = session_start_hook_present(root, manifest)
    session_start_trusted = session_start_hook_trusted(codex_home, root)
    status = superpowers_status(version, required_skills, session_start_present, session_start_trusted)
    return {
        "status": status,
        "version": version,
        "sourceChannel": source_channel,
        "pluginRoot": str(root),
        "compatibility": superpowers_compatibility(version),
        "minimumCompatibleVersion": SUPERPOWERS_MINIMUM_COMPATIBLE,
        "recommendedVersion": SUPERPOWERS_RECOMMENDED,
        "strictProfileRequires": SUPERPOWERS_STRICT_REQUIRES,
        "requiredSkills": required_skills,
        "strictRecommendedSkills": strict_skills,
        "sessionStartHookPresent": session_start_present,
        "sessionStartHookTrusted": session_start_trusted,
        "strict": strict,
        "nextAction": superpowers_next_action(status),
    }


def add_superpowers_governance_checks(
    checks: list[dict[str, Any]],
    codex_home: Path,
    strict: bool,
) -> dict[str, Any]:
    report = superpowers_governance_report(codex_home, strict)
    status = report["status"]
    ok_statuses = {"superpowers_ok", "superpowers_latest_ready"}
    required = strict and status not in {"superpowers_upgrade_recommended"}
    add_check(
        checks,
        "superpowers dependency status",
        status in ok_statuses,
        required,
        report["nextAction"],
        status=status,
        version=report.get("version"),
        sourceChannel=report.get("sourceChannel"),
        compatibility=report.get("compatibility"),
    )
    add_check(
        checks,
        "superpowers latest ready",
        compare_versions(str(report.get("version") or "0"), SUPERPOWERS_RECOMMENDED) >= 0
        and all(report.get("requiredSkills", {}).values()),
        strict,
        f"version {report.get('version') or 'unknown'}, recommended {SUPERPOWERS_RECOMMENDED}",
        status=status,
    )
    if compare_versions(str(report.get("version") or "0"), "6.0.0") >= 0:
        add_check(
            checks,
            "superpowers session-start hook present",
            bool(report.get("sessionStartHookPresent")),
            strict,
            "SessionStart hook present" if report.get("sessionStartHookPresent") else "missing SessionStart hook",
            status=status,
        )
        add_check(
            checks,
            "superpowers session-start hook trusted",
            bool(report.get("sessionStartHookTrusted")),
            strict,
            "trusted" if report.get("sessionStartHookTrusted") else "review and trust with /hooks",
            status=status,
        )
    return report


def find_plugin_roots(codex_home: Path, plugin: str) -> list[Path]:
    cache = codex_home / "plugins" / "cache"
    if not cache.exists():
        return []
    roots: list[Path] = []
    for manifest in cache.rglob(".codex-plugin/plugin.json"):
        root = manifest.parents[1]
        try:
            data = read_json(manifest)
        except json.JSONDecodeError:
            continue
        if data.get("name") == plugin or plugin in root.parts:
            roots.append(root)
    for skills_dir in cache.rglob("skills"):
        root = skills_dir.parent
        if plugin in root.parts and root not in roots:
            roots.append(root)
    return sorted(roots, key=lambda path: str(path))


def select_plugin_root(roots: list[Path]) -> Path:
    return sorted(roots, key=lambda path: (manifest_version(path), str(path)), reverse=True)[0]


def manifest_version(root: Path) -> tuple[int, int, int]:
    try:
        version = str(read_json(root / ".codex-plugin" / "plugin.json").get("version") or "0")
    except (OSError, json.JSONDecodeError):
        version = "0"
    return version_tuple(version)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def source_channel_for_root(codex_home: Path, root: Path) -> str | None:
    cache = codex_home / "plugins" / "cache"
    try:
        relative = root.relative_to(cache)
    except ValueError:
        return None
    return relative.parts[0] if relative.parts else None


def session_start_hook_present(root: Path, manifest: dict[str, Any]) -> bool:
    for _, path in session_start_hook_candidates(root, manifest):
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        hooks = data.get("hooks", {})
        if "SessionStart" in hooks:
            return True
    return False


def session_start_hook_trusted(codex_home: Path, root: Path) -> bool:
    if session_start_hook_trusted_in_legacy_files(codex_home, root):
        return True
    return session_start_hook_trusted_in_config(codex_home, root)


def session_start_hook_trusted_in_legacy_files(codex_home: Path, root: Path) -> bool:
    trust_files = [
        codex_home / "hooks" / "trusted.json",
        codex_home / "hooks" / "trust.json",
        codex_home / "hooks-trust.json",
    ]
    root_text = str(root)
    for path in trust_files:
        if not path.exists():
            continue
        text = path.read_text()
        if root_text in text and "SessionStart" in text:
            return True
    return False


def session_start_hook_trusted_in_config(codex_home: Path, root: Path) -> bool:
    config = read_config(codex_home / "config.toml")
    hook_state = config.get("hooks", {}).get("state", {})
    if not isinstance(hook_state, dict):
        return False
    trusted_keys = session_start_hook_state_keys(codex_home, root)
    for key in trusted_keys:
        entry = hook_state.get(key)
        if isinstance(entry, dict) and is_trusted_hash(entry.get("trusted_hash")):
            return True
    return False


def session_start_hook_state_keys(codex_home: Path, root: Path) -> set[str]:
    manifest = read_json(root / ".codex-plugin" / "plugin.json")
    source_channel = source_channel_for_root(codex_home, root)
    if not source_channel:
        return set()
    plugin_id = f"superpowers@{source_channel}"
    keys: set[str] = set()
    for relative, path in session_start_hook_candidates(root, manifest):
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        groups = data.get("hooks", {}).get("SessionStart", [])
        if not isinstance(groups, list):
            continue
        for group_index, group in enumerate(groups):
            hooks = group.get("hooks", []) if isinstance(group, dict) else []
            if not isinstance(hooks, list):
                continue
            for hook_index, hook in enumerate(hooks):
                if isinstance(hook, dict) and hook.get("type", "command") == "command":
                    keys.add(f"{plugin_id}:{relative}:session_start:{group_index}:{hook_index}")
    return keys


def session_start_hook_candidates(root: Path, manifest: dict[str, Any]) -> list[tuple[str, Path]]:
    candidates: list[tuple[str, Path]] = []
    hooks_value = manifest.get("hooks")
    if isinstance(hooks_value, str):
        candidates.append((normalize_hook_relative_path(hooks_value), root / hooks_value))
    candidates.extend(
        [
            ("hooks/hooks-codex.json", root / "hooks" / "hooks-codex.json"),
            ("hooks.json", root / "hooks.json"),
        ]
    )
    deduped: list[tuple[str, Path]] = []
    seen: set[Path] = set()
    for relative, path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append((relative, path))
    return deduped


def normalize_hook_relative_path(value: str) -> str:
    return Path(value).as_posix().removeprefix("./")


def is_trusted_hash(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("sha256:") and len(value) > len("sha256:")


def superpowers_status(
    version: str,
    required_skills: dict[str, bool],
    session_start_present: bool,
    session_start_trusted: bool,
) -> str:
    if not all(required_skills.values()):
        return "superpowers_unsupported"
    if compare_versions(version, SUPERPOWERS_MINIMUM_COMPATIBLE) < 0:
        return "superpowers_unsupported"
    if compare_versions(version, SUPERPOWERS_RECOMMENDED) < 0:
        return "superpowers_upgrade_recommended"
    if compare_versions(version, "6.0.0") >= 0 and not session_start_present:
        return "superpowers_hook_missing"
    if compare_versions(version, "6.0.0") >= 0 and not session_start_trusted:
        return "superpowers_hook_untrusted"
    return "superpowers_ok"


def superpowers_compatibility(version: str) -> str:
    if compare_versions(version, SUPERPOWERS_MINIMUM_COMPATIBLE) < 0:
        return "unsupported"
    if compare_versions(version, SUPERPOWERS_RECOMMENDED) < 0:
        return "fallback"
    return "recommended"


def superpowers_next_action(status: str) -> str:
    return {
        "superpowers_missing": "Install and enable Superpowers before strict DevFlow execution.",
        "superpowers_unsupported": "Install Superpowers 5.1.3 or newer; recommended target is 6.0.3.",
        "superpowers_upgrade_recommended": (
            "Upgrade Superpowers to 6.0.3 through an explicit marketplace or pinned-source action."
        ),
        "superpowers_hook_missing": "Install a Superpowers v6 package with a Codex SessionStart hook.",
        "superpowers_hook_untrusted": "Review and trust the Superpowers SessionStart hook with /hooks.",
        "superpowers_ok": "Superpowers dependency is ready.",
    }.get(status, "Review Superpowers dependency status.")


def compare_versions(left: str, right: str) -> int:
    left_tuple = version_tuple(left)
    right_tuple = version_tuple(right)
    if left_tuple < right_tuple:
        return -1
    if left_tuple > right_tuple:
        return 1
    return 0


def version_tuple(value: str) -> tuple[int, int, int]:
    parts: list[int] = []
    for part in value.strip().lstrip("v").split("."):
        digits = "".join(char for char in part if char.isdigit())
        parts.append(int(digits or 0))
        if len(parts) == 3:
            break
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])  # type: ignore[return-value]


def add_check(
    checks: list[dict[str, Any]],
    name: str,
    ok: bool,
    required: bool,
    detail: str = "",
    **extra: Any,
) -> None:
    payload = {"name": name, "ok": bool(ok), "required": bool(required), "detail": detail}
    payload.update(extra)
    checks.append(payload)
