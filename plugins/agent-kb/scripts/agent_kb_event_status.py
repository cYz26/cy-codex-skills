from __future__ import annotations

from typing import Any

from agent_kb_value_extract import first_text

PASS_STATUSES = {"success", "ok", "passed", "pass"}
FAIL_STATUSES = {"error", "failed", "fail"}
TEST_COMMANDS = ("pytest", "unittest", "npm test", "pnpm test", "yarn test", "cargo test")
LINT_COMMANDS = ("lint", "ruff", "eslint", "mypy", "tsc")
BUILD_COMMANDS = ("build", "webpack", "vite build", "cargo build")


def status_for(exit_code: int | None, tool_response: dict[str, Any], payload: dict[str, Any]):
    explicit = first_text(tool_response.get("status"), payload.get("status"))
    if explicit:
        return normalized_status(explicit)
    if exit_code is None:
        return "unknown"
    return "pass" if exit_code == 0 else "fail"


def normalized_status(value: str):
    lowered = value.lower()
    if lowered in PASS_STATUSES:
        return "pass"
    if lowered in FAIL_STATUSES:
        return "fail"
    return lowered


def command_category(command: str):
    lowered = command.lower()
    stripped = lowered.strip()
    if contains_any(lowered, TEST_COMMANDS):
        return "test"
    if contains_any(lowered, LINT_COMMANDS):
        return "lint"
    if contains_any(lowered, BUILD_COMMANDS):
        return "build"
    return "git" if stripped.startswith("git ") else "command"


def contains_any(value: str, tokens: tuple[str, ...]):
    return any(token in value for token in tokens)
