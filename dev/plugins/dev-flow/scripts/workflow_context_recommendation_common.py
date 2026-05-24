from __future__ import annotations

from typing import Any


def recommendation(kind: str, action: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "actionId": action["id"],
        "title": action["title"],
        "reason": reason,
    }
