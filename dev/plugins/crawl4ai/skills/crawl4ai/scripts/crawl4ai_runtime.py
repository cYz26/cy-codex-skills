from __future__ import annotations

import subprocess

from crawl4ai_commands import configured_command
from crawl4ai_payloads import failed_payload, successful_payload, unavailable_payload, unsupported_payload


def fetch_url(url: str, output_format: str, timeout: int, command: list[str] | None = None) -> tuple[dict, int]:
    resolved = command if command is not None else configured_command()
    if not url.startswith(("http://", "https://")):
        return unsupported_payload(url), 2
    if not resolved:
        return unavailable_payload(url, output_format), 2
    return run_crawl4ai(url, output_format, resolved, timeout)


def run_crawl4ai(url: str, output_format: str, command: list[str], timeout: int) -> tuple[dict, int]:
    try:
        result = subprocess.run(
            [*command, url, "-o", output_format],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    except Exception as exc:  # pragma: no cover - depends on local command execution
        return failed_payload(url, output_format, command, str(exc)), 1
    if result.returncode != 0:
        return failed_payload(url, output_format, command, output_error(result)), result.returncode or 1
    if not result.stdout.strip():
        return failed_payload(url, output_format, command, "Crawl4AI returned empty output."), 1
    return successful_payload(url, output_format, command, result), 0


def output_error(result: subprocess.CompletedProcess[str]) -> str:
    return (result.stderr or result.stdout).strip()
