from __future__ import annotations

import shlex
import subprocess


def capability_payload(command: list[str] | None) -> dict:
    return {
        "ok": bool(command),
        "available": bool(command),
        "extractor": "crawl4ai",
        "mode": "command" if command else "unavailable",
        "command": quoted_command(command),
        "fetches": ["http", "https"],
    }


def quoted_command(command: list[str] | None) -> str | None:
    return " ".join(shlex.quote(part) for part in command) if command else None


def unsupported_payload(url: str) -> dict:
    return {
        "ok": False,
        "reason": "unsupported-url",
        "error": "Only http:// and https:// URLs are supported.",
        "url": url,
    }


def unavailable_payload(url: str, output_format: str) -> dict:
    return {
        "ok": False,
        "available": False,
        "reason": "crawl4ai-unavailable",
        "extractor": "crawl4ai",
        "format": output_format,
        "command": None,
        "url": url,
        "content": "",
        "error": "Crawl4AI command unavailable.",
    }


def successful_payload(
    url: str,
    output_format: str,
    command: list[str],
    result: subprocess.CompletedProcess[str],
) -> dict:
    return {
        "ok": True,
        "available": True,
        "extractor": "crawl4ai",
        "format": output_format,
        "command": command[0],
        "url": url,
        "content": result.stdout,
        "stderr": result.stderr.strip(),
    }


def failed_payload(url: str, output_format: str, command: list[str], error: str) -> dict:
    return {
        "ok": False,
        "available": True,
        "reason": "crawl4ai-fetch-failed",
        "extractor": "crawl4ai",
        "format": output_format,
        "command": command[0] if command else None,
        "url": url,
        "content": "",
        "error": error,
    }
