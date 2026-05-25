from __future__ import annotations

import re
from typing import Any


SIGNAL_KEYWORDS = {
    "javascript": {"web", "frontend", "node", "react", "next", "vite", "shadcn"},
    "react": {"react", "frontend", "web", "next", "shadcn"},
    "nextjs": {"next", "react", "frontend", "web"},
    "python": {"python", "pytest", "django", "fastapi"},
    "go": {"go", "golang"},
    "rust": {"rust", "cargo"},
    "swift": {"swift", "swiftui", "ios", "macos", "xcode"},
    "ios": {"ios", "swiftui", "xcode"},
    "android": {"android", "gradle", "kotlin"},
    "godot": {"godot"},
}


def relevant_to_project(tool: dict[str, Any], signals: list[str]) -> bool:
    if not signals:
        return False
    haystack = " ".join(str(tool.get(key, "")) for key in ["name", "plugin", "key", "description"]).lower()
    for signal in signals:
        keywords = SIGNAL_KEYWORDS.get(signal, {signal})
        if any(keyword in haystack for keyword in keywords):
            return True
    return False


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
