from __future__ import annotations

import hashlib
import re
from datetime import datetime


def normalize_event_type(value: str):
    return value.strip().lower().replace("-", "_") or "event"


def hash_text(value: str):
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def redact_command(command: str):
    command = re.sub(r"(?i)(api[_-]?key|token|password|secret)=\S+", r"\1=<redacted>", command)
    command = re.sub(r"(?i)(--(?:api-key|token|password|secret))\s+\S+", r"\1 <redacted>", command)
    return command.strip()[:240]


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")
