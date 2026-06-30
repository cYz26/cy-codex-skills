#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys

from crawl4ai_payloads import capability_payload
from crawl4ai_runtime import configured_command, fetch_url


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch a URL with Crawl4AI.")
    parser.add_argument("--url", help="HTTP(S) URL to fetch")
    parser.add_argument(
        "--format",
        default="markdown",
        choices=["markdown", "html"],
        help="Crawl4AI output format",
    )
    parser.add_argument("--check", action="store_true", help="Only report command availability")
    parser.add_argument("--json", action="store_true", help="Emit a JSON result")
    parser.add_argument("--timeout", type=int, default=180, help="Fetch timeout in seconds")
    args = parser.parse_args()

    command = configured_command()
    if args.check:
        payload = capability_payload(command)
        emit(payload, args.json)
        return 0 if payload["ok"] else 2

    if not args.url:
        parser.error("--url is required unless --check is used")

    payload, code = fetch_url(args.url, args.format, args.timeout, command)
    emit(payload, args.json)
    return code


def emit(payload: dict, emit_json: bool) -> None:
    if emit_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return
    content = payload.get("content", "")
    if payload.get("ok") and content:
        print(content, end="" if content.endswith("\n") else "\n")
        return
    print(payload.get("error", "Crawl4AI fetch failed."), file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
