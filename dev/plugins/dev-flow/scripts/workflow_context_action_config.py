from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path


def ensure_backup(config_path: Path, backups: dict[Path, Path], timestamp: str | None) -> Path:
    config_path = config_path.resolve()
    if config_path in backups:
        return backups[config_path]
    stamp = timestamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = config_path.with_name(f"{config_path.name}.bak-{stamp}")
    if config_path.exists():
        shutil.copy2(config_path, backup)
    else:
        backup.write_text("")
    backups[config_path] = backup
    return backup


def set_plugin_enabled(text: str, plugin_key: str, enabled: bool) -> str:
    lines = text.splitlines()
    header = f'[plugins."{plugin_key}"]'
    enabled_line = f"enabled = {'true' if enabled else 'false'}"
    for index, line in enumerate(lines):
        if line.strip() == header:
            return update_plugin_section(lines, index, enabled_line)
    return append_plugin_section(lines, header, enabled_line)


def update_plugin_section(lines: list[str], index: int, enabled_line: str) -> str:
    end = next_section_index(lines, index + 1)
    for line_index in range(index + 1, end):
        if re.match(r"\s*enabled\s*=", lines[line_index]):
            indent = re.match(r"(\s*)", lines[line_index]).group(1)
            lines[line_index] = f"{indent}{enabled_line}"
            return "\n".join(lines) + "\n"
    lines.insert(index + 1, enabled_line)
    return "\n".join(lines) + "\n"


def append_plugin_section(lines: list[str], header: str, enabled_line: str) -> str:
    if lines and lines[-1].strip():
        lines.append("")
    lines.extend([header, enabled_line])
    return "\n".join(lines) + "\n"


def next_section_index(lines: list[str], start: int) -> int:
    for index in range(start, len(lines)):
        if lines[index].lstrip().startswith("["):
            return index
    return len(lines)


def append_disabled_skill(text: str, skill_path: str) -> str:
    block = ["", "[[skills.config]]", f'path = "{escape_toml_string(skill_path)}"', "enabled = false"]
    stripped = text.rstrip("\n")
    return stripped + "\n" + "\n".join(block) + "\n"


def escape_toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
