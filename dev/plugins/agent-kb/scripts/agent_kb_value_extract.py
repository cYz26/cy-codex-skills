from __future__ import annotations

import json
from typing import Any


def first_dict(*values: Any):
    for value in values:
        parsed = parse_dict_value(value)
        if parsed is not None:
            return parsed
    return {}


def parse_dict_value(value: Any):
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def first_text(*values: Any):
    for value in values:
        if isinstance(value, str) and value:
            return value
    return ""


def first_int(*values: Any):
    for value in values:
        parsed = parse_int_value(value)
        if parsed is not None:
            return parsed
    return None


def parse_int_value(value: Any):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    try:
        return int(value)
    except ValueError:
        return None
