#!/usr/bin/env python3
"""Run bounded, offline checks against the installed runtime contract."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

# The installed self-test must not mutate its package even when the caller does
# not set PYTHONDONTWRITEBYTECODE.
sys.dont_write_bytecode = True

from lark_feishu_ops_policy import (
    RISK_READ,
    RISK_UNKNOWN,
    classify_action,
    direct_eligible,
)
from lark_feishu_ops_state import cache_allowed


def check_record(observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "ok": observed == expected,
        "observed": observed,
        "expected": expected,
    }


def runtime_contract_report() -> dict[str, Any]:
    auth_cache_enabled, auth_cache_reason = cache_allowed("auth", "enabled")
    checks = {
        "explicit_read_allowed": check_record(
            classify_action("docs.fetch"),
            RISK_READ,
        ),
        "unknown_action_blocked": check_record(
            classify_action("docs.unregistered-operation"),
            RISK_UNKNOWN,
        ),
        "write_action_not_direct": check_record(
            direct_eligible("docs.update"),
            False,
        ),
        "auth_cache_disabled": {
            **check_record(auth_cache_enabled, False),
            "reason": auth_cache_reason,
        },
    }
    return {
        "ok": all(item["ok"] for item in checks.values()),
        "mode": "offline_read_only",
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify fail-closed Lark Feishu Ops runtime invariants offline."
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = runtime_contract_report()
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else ("PASS" if report["ok"] else "FAIL"))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
