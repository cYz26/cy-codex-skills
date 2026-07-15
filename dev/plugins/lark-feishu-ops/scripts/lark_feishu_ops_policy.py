#!/usr/bin/env python3
"""Fail-closed action and embedded-guidance policy for Lark Feishu Ops."""

from __future__ import annotations

from typing import Any


RISK_READ = "read"
RISK_WRITE = "write"
RISK_HIGH = "high-risk-write"
RISK_UNKNOWN = "unknown"

DOMAIN_ALIASES = {
    "api": "openapi",
    "bitable": "base",
    "calendar-event": "calendar",
    "chat": "im",
    "contacts": "contact",
    "doc": "docs",
    "document": "docs",
    "docx": "docs",
    "file": "drive",
    "folder": "drive",
    "meeting": "vc",
    "meetings": "vc",
    "message": "im",
    "open-api": "openapi",
    "sheet": "sheets",
    "spreadsheet": "sheets",
    "table": "base",
    "transcript": "minutes",
    "wiki-node": "wiki",
}

# This is an allowlist of routing intent, not a copy of skill content. Runtime
# availability is always taken from `lark-cli skills list --json`.
DOMAIN_GUIDANCE: dict[str, dict[str, list[Any]]] = {
    "application": {"skills": [], "cli_help": [["application", "--help"]]},
    "approval": {"skills": ["lark-approval"], "cli_help": [["approval", "--help"]]},
    "apps": {"skills": ["lark-apps"], "cli_help": [["apps", "--help"]]},
    "attendance": {"skills": ["lark-attendance"], "cli_help": [["attendance", "--help"]]},
    "auth": {"skills": ["lark-shared"], "cli_help": [["auth", "--help"]]},
    "base": {"skills": ["lark-base"], "cli_help": [["base", "--help"]]},
    "calendar": {"skills": ["lark-calendar"], "cli_help": [["calendar", "--help"]]},
    "config": {"skills": ["lark-shared"], "cli_help": [["config", "--help"]]},
    "contact": {"skills": ["lark-contact"], "cli_help": [["contact", "--help"]]},
    "docs": {"skills": ["lark-doc"], "cli_help": [["docs", "--help"]]},
    "drive": {"skills": ["lark-drive"], "cli_help": [["drive", "--help"]]},
    "doctor": {"skills": ["lark-shared"], "cli_help": [["doctor", "--help"]]},
    "event": {"skills": ["lark-event"], "cli_help": [["event", "--help"]]},
    "im": {"skills": ["lark-im"], "cli_help": [["im", "--help"]]},
    "mail": {"skills": ["lark-mail"], "cli_help": [["mail", "--help"]]},
    "markdown": {"skills": ["lark-markdown"], "cli_help": [["markdown", "--help"]]},
    "mindnotes": {"skills": ["lark-doc"], "cli_help": [["mindnotes", "--help"]]},
    "minutes": {"skills": ["lark-minutes"], "cli_help": [["minutes", "--help"]]},
    "note": {"skills": ["lark-note"], "cli_help": [["note", "--help"]]},
    "okr": {"skills": ["lark-okr"], "cli_help": [["okr", "--help"]]},
    "openapi": {
        "skills": ["lark-openapi-explorer"],
        "cli_help": [["schema", "--help"], ["api", "--help"]],
    },
    "profile": {"skills": ["lark-shared"], "cli_help": [["profile", "--help"]]},
    "schema": {
        "skills": ["lark-openapi-explorer"],
        "cli_help": [["schema", "--help"]],
    },
    "sheets": {"skills": ["lark-sheets"], "cli_help": [["sheets", "--help"]]},
    "skill-maker": {"skills": ["lark-skill-maker"], "cli_help": [["skills", "--help"]]},
    "skills": {"skills": [], "cli_help": [["skills", "--help"]]},
    "slides": {"skills": ["lark-slides"], "cli_help": [["slides", "--help"]]},
    "task": {"skills": ["lark-task"], "cli_help": [["task", "--help"]]},
    "update": {"skills": ["lark-shared"], "cli_help": [["update", "--help"]]},
    "vc": {"skills": ["lark-vc"], "cli_help": [["vc", "--help"]]},
    "vc-agent": {"skills": ["lark-vc-agent"], "cli_help": [["vc", "--help"]]},
    "whiteboard": {"skills": ["lark-whiteboard"], "cli_help": [["whiteboard", "--help"]]},
    "wiki": {"skills": ["lark-wiki", "lark-doc"], "cli_help": [["wiki", "--help"]]},
    "whoami": {"skills": ["lark-shared"], "cli_help": [["whoami", "--help"]]},
    "workflow-meeting-summary": {
        "skills": ["lark-workflow-meeting-summary"],
        "cli_help": [["minutes", "--help"], ["vc", "--help"]],
    },
    "workflow-standup-report": {
        "skills": ["lark-workflow-standup-report"],
        "cli_help": [["calendar", "--help"], ["task", "--help"]],
    },
}

KNOWN_EMBEDDED_SKILLS = frozenset(
    skill
    for guidance in DOMAIN_GUIDANCE.values()
    for skill in guidance["skills"]
)

# Direct execution is deliberately small. These operations are bounded reads
# with stable semantics; everything else must be delegated or confirmed.
EXPLICIT_READ_ACTIONS = frozenset(
    {
        "approval.get",
        "approval.list",
        "attendance.get",
        "attendance.list",
        "auth.status",
        "base.get",
        "base.list",
        "base.read",
        "calendar.get",
        "calendar.list",
        "calendar.search",
        "contact.get",
        "contact.search",
        "docs.fetch",
        "docs.get",
        "docs.read",
        "drive.get",
        "drive.list",
        "event.get",
        "event.list",
        "im.get",
        "im.list",
        "im.search",
        "mail.get",
        "mail.list",
        "mail.search",
        "minutes.get",
        "minutes.list",
        "note.get",
        "okr.get",
        "okr.list",
        "sheets.get",
        "sheets.read",
        "slides.get",
        "task.get",
        "task.list",
        "vc.get",
        "vc.list",
        "whiteboard.get",
        "wiki.get",
        "wiki.list",
    }
)

HIGH_RISK_DOMAINS = frozenset(
    {
        "application",
        "apps",
        "auth",
        "config",
        "openapi",
        "profile",
        "skill-maker",
        "skills",
        "update",
    }
)
HIGH_RISK_VERBS = frozenset(
    {
        "api",
        "execute",
        "login",
        "logout",
        "raw",
        "remove-account",
        "schema",
        "switch",
        "update",
    }
)
WRITE_VERBS = frozenset(
    {
        "add",
        "approve",
        "archive",
        "cancel",
        "complete",
        "create",
        "delete",
        "edit",
        "forward",
        "invite",
        "move",
        "publish",
        "reject",
        "remove",
        "reply",
        "restore",
        "send",
        "share",
        "submit",
        "transfer",
        "unload",
        "upload",
        "upsert",
        "write",
    }
)

RISK_ORDER = {
    RISK_READ: 0,
    RISK_WRITE: 1,
    RISK_HIGH: 2,
    RISK_UNKNOWN: 3,
}


def canonical_domain(value: str | None) -> str:
    normalized = str(value or "").strip().lower().replace("_", "-")
    return DOMAIN_ALIASES.get(normalized, normalized)


def action_domain(action: str) -> str:
    return canonical_domain(str(action or "").split(".", 1)[0])


def action_verb(action: str) -> str:
    parts = str(action or "").strip().lower().replace("_", "-").split(".")
    return parts[-1] if len(parts) > 1 else ""


def classify_action(action: str, hints: dict[str, Any] | None = None) -> str:
    normalized = str(action or "").strip().lower().replace("_", "-")
    domain = action_domain(normalized)
    verb = action_verb(normalized)
    if normalized in EXPLICIT_READ_ACTIONS:
        risk = RISK_READ
    elif domain in HIGH_RISK_DOMAINS or verb in HIGH_RISK_VERBS:
        risk = RISK_HIGH
    elif verb in WRITE_VERBS:
        risk = RISK_WRITE
    else:
        risk = RISK_UNKNOWN
    return stricter_risk(risk, risk_hint(hints))


def risk_hint(hints: dict[str, Any] | None) -> str | None:
    if not isinstance(hints, dict):
        return None
    if hints.get("high_risk") is True or hints.get("raw_openapi") is True:
        return RISK_HIGH
    side_effects = hints.get("side_effects")
    declares_side_effects = (
        side_effects is True
        or (isinstance(side_effects, (dict, list, set, tuple)) and bool(side_effects))
        or (
            isinstance(side_effects, str)
            and side_effects.strip().lower() not in {"", "false", "no", "none"}
        )
    )
    if hints.get("write") is True or hints.get("side_effect") is True or declares_side_effects:
        return RISK_WRITE
    value = str(hints.get("risk") or hints.get("risk_class") or "").strip().lower()
    aliases = {
        "high": RISK_HIGH,
        "high-risk": RISK_HIGH,
        "high-risk-write": RISK_HIGH,
        "read": RISK_READ,
        "readonly": RISK_READ,
        "unknown": RISK_UNKNOWN,
        "write": RISK_WRITE,
    }
    return aliases.get(value)


def stricter_risk(classified: str, hinted: str | None) -> str:
    if hinted is None:
        return classified
    # Unknown is not a caller-selectable downgrade. A caller may make a known
    # operation stricter, but can never turn unknown/write into read.
    if hinted == RISK_UNKNOWN:
        return RISK_UNKNOWN
    if classified == RISK_UNKNOWN:
        return RISK_UNKNOWN
    return hinted if RISK_ORDER[hinted] > RISK_ORDER[classified] else classified


def direct_eligible(action: str, hints: dict[str, Any] | None = None) -> bool:
    return classify_action(action, hints) == RISK_READ


def guidance_for_domain(domain: str) -> dict[str, list[Any]]:
    return DOMAIN_GUIDANCE.get(canonical_domain(domain), {"skills": [], "cli_help": []})


def guidance_coverage(embedded_skills: set[str]) -> dict[str, Any]:
    mapped = set(KNOWN_EMBEDDED_SKILLS)
    return {
        "domains": {
            domain: {"skills": list(guidance["skills"]), "available": [
                skill for skill in guidance["skills"] if skill in embedded_skills
            ]}
            for domain, guidance in sorted(DOMAIN_GUIDANCE.items())
        },
        "mapped_skills": sorted(mapped),
        "embedded_skills": sorted(embedded_skills),
        "missing_embedded_skills": sorted(mapped - embedded_skills),
        "unmapped_embedded_skills": sorted(embedded_skills - mapped),
    }
