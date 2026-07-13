from __future__ import annotations

import hashlib
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workflow_paths import rel, repo_path, sanitize_filename
from workflow_mode_routing import read_workflow_mode_config
from workflow_planning_paths import atomic_write_devflow, verification_root
from workflow_roadmap_provider import GsdReadOnlyAdapter, resolve_gsd_uat_artifact
from workflow_state import update_state


MAX_UAT_BYTES = 2 * 1024 * 1024
PASSING_UAT_RESULTS = {"pass", "passed"}


def record_verification(repo: Path, command: str, result: str, notes: str = "") -> dict[str, str]:
    repo = repo_path(repo)
    status = result.lower()
    path = verification_path(repo, command)
    atomic_write_devflow(repo, path, verification_record(command, status, notes))
    update_state(repo, verification_passed=status == "pass", state_updated=True)
    return {"path": rel(repo, path), "result": status}


def record_gsd_verification(
    repo: Path,
    *,
    change: str,
    phase: str,
    command: str | None = None,
    result: str | None = None,
    notes: str = "",
    adapter: GsdReadOnlyAdapter | None = None,
) -> dict[str, Any]:
    """Record evidence only from the canonical GSD UAT artifact.

    ``command`` and ``result`` remain accepted for CLI/API compatibility but
    are deliberately ignored. Neither can turn an incomplete artifact green.
    """

    repo = repo_path(repo)
    config = read_workflow_mode_config(repo)
    bindings = config.get("roadmap_bindings", {})
    binding = bindings.get(change) if isinstance(bindings, dict) else None
    if config.get("roadmap_provider") != "gsd":
        return {"ok": False, "status": "gsd_not_selected", "result": "fail"}
    if not isinstance(binding, dict) or binding.get("status") != "active":
        return {"ok": False, "status": "active_binding_missing", "result": "fail"}
    if str(binding.get("phase_id")) != str(phase):
        return {"ok": False, "status": "binding_phase_mismatch", "result": "fail"}

    evidence = collect_gsd_uat_evidence(repo, phase=phase, adapter=adapter)
    if not evidence.get("ok"):
        return {
            **evidence,
            "change": change,
            "phase": phase,
            "result": "fail",
            "callerInputIgnored": command is not None or result is not None,
        }

    path = verification_path(repo, f"gsd-uat-{change}-{phase}")
    atomic_write_devflow(
        repo,
        path,
        gsd_verification_record(
            change=change,
            phase=phase,
            artifact=str(evidence["uatArtifact"]),
            digest=str(evidence["uatSha256"]),
            test_count=int(evidence["testCount"]),
            notes=notes,
        ),
    )
    update_state(
        repo,
        gsd_verification_passed=True,
        gsd_verification_change=change,
        gsd_verification_phase=phase,
        state_updated=True,
    )
    return {
        "ok": True,
        "status": "recorded",
        "path": rel(repo, path),
        "result": "pass",
        "change": change,
        "phase": phase,
        "uatArtifact": str(evidence["uatArtifact"]),
        "uatSha256": str(evidence["uatSha256"]),
        "testCount": int(evidence["testCount"]),
        "callerInputIgnored": command is not None or result is not None,
    }


def collect_gsd_uat_evidence(
    repo: Path,
    *,
    phase: str,
    adapter: GsdReadOnlyAdapter | None = None,
) -> dict[str, Any]:
    repo = repo_path(repo)
    resolved = resolve_gsd_uat_artifact(repo, phase, adapter=adapter)
    if not resolved.get("ok"):
        return {
            "ok": False,
            "verified": False,
            "status": str(resolved.get("reason") or "gsd_phase_unresolved"),
            "resolution": resolved,
        }
    if not resolved.get("exists"):
        return {
            "ok": False,
            "verified": False,
            "status": "uat_artifact_missing",
            "uatArtifact": resolved.get("relativePath"),
            "resolution": resolved,
        }

    artifact = Path(str(resolved["path"]))
    try:
        raw = _read_regular_file_no_follow(artifact)
    except ValueError as error:
        return {
            "ok": False,
            "verified": False,
            "status": str(error),
            "uatArtifact": resolved.get("relativePath"),
        }
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return {
            "ok": False,
            "verified": False,
            "status": "uat_invalid_utf8",
            "uatArtifact": resolved.get("relativePath"),
        }
    parsed = evaluate_gsd_uat(text, expected_phase=str(resolved["canonicalPhaseId"]))
    if not parsed["ok"]:
        return {
            **parsed,
            "verified": False,
            "uatArtifact": resolved.get("relativePath"),
        }
    return {
        "ok": True,
        "verified": True,
        "status": "uat_verified",
        "uatArtifact": str(resolved["relativePath"]),
        "uatSha256": hashlib.sha256(raw).hexdigest(),
        "testCount": parsed["testCount"],
        "phase": resolved["canonicalPhaseId"],
    }


def evaluate_gsd_uat(text: str, *, expected_phase: str) -> dict[str, Any]:
    text = text.replace("\r\n", "\n")
    frontmatter, body, error = _parse_safe_frontmatter(text)
    if error:
        return {"ok": False, "status": error}
    if str(frontmatter.get("status", "")).casefold() != "complete":
        return {"ok": False, "status": "uat_status_not_complete"}
    if str(frontmatter.get("phase", "")) != expected_phase:
        return {"ok": False, "status": "uat_phase_mismatch"}

    semantic, error = _strip_nonsemantic_markdown(body)
    if error:
        return {"ok": False, "status": error}
    tests, error = _parse_uat_tests(semantic)
    if error:
        return {"ok": False, "status": error}
    if any(item not in PASSING_UAT_RESULTS for item in tests):
        return {"ok": False, "status": "uat_tests_not_passed", "results": tests}

    summary, error = _parse_uat_summary(semantic)
    if error:
        return {"ok": False, "status": error}
    blockers = sum(summary.get(key, 0) for key in ("issues", "pending", "skipped", "blocked"))
    if blockers or summary["total"] != len(tests) or summary["passed"] != len(tests):
        return {"ok": False, "status": "uat_summary_not_complete", "summary": summary}

    gaps, error = _markdown_section(semantic, "Gaps", required=False)
    if error:
        return {"ok": False, "status": error}
    normalized_gaps = re.sub(r"\s+", " ", gaps or "").strip().casefold()
    if normalized_gaps not in {"", "none", "none.", "no gaps", "no gaps.", "[]"}:
        return {"ok": False, "status": "uat_unresolved_gaps"}
    return {"ok": True, "status": "uat_verified", "testCount": len(tests), "summary": summary}


def gsd_verification_status(
    repo: Path,
    *,
    change: str,
    phase: str,
    adapter: GsdReadOnlyAdapter | None = None,
) -> dict[str, Any]:
    """Confirm recorded evidence still hashes to the current canonical UAT."""

    repo = repo_path(repo)
    current = collect_gsd_uat_evidence(repo, phase=phase, adapter=adapter)
    if not current.get("ok"):
        return {**current, "verified": False, "change": change, "phase": phase}
    root = verification_root(repo)
    if not root.is_dir() or root.is_symlink():
        return {
            "ok": False,
            "verified": False,
            "status": "gsd_evidence_missing",
            "change": change,
            "phase": phase,
        }
    for path in sorted(root.glob("*.md"), reverse=True):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            raw = _read_regular_file_no_follow(path)
            evidence_text = raw.decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            continue
        frontmatter, _, error = _parse_safe_frontmatter(evidence_text.replace("\r\n", "\n"))
        if error:
            continue
        if (
            frontmatter.get("evidence_type") == "gsd_uat"
            and frontmatter.get("change") == change
            and frontmatter.get("phase") == phase
            and frontmatter.get("uat_artifact") == current["uatArtifact"]
            and frontmatter.get("uat_sha256") == current["uatSha256"]
            and frontmatter.get("result") == "pass"
        ):
            return {
                **current,
                "ok": True,
                "verified": True,
                "status": "verified",
                "change": change,
                "phase": phase,
                "evidencePath": rel(repo, path),
            }
    return {
        **current,
        "ok": False,
        "verified": False,
        "status": "gsd_evidence_missing_or_drifted",
        "change": change,
        "phase": phase,
    }


def gsd_verification_record(
    *,
    change: str,
    phase: str,
    artifact: str,
    digest: str,
    test_count: int,
    notes: str,
) -> str:
    fields = (change, phase, artifact, digest)
    if any("\n" in value or "\r" in value or ": " in value for value in fields):
        raise ValueError("GSD evidence metadata contains unsupported characters")
    lines = [
        "---",
        "evidence_type: gsd_uat",
        f"change: {change}",
        f"phase: {phase}",
        f"uat_artifact: {artifact}",
        f"uat_sha256: {digest}",
        "result: pass",
        "---",
        "# GSD UAT Verification Record",
        "",
        f"- Canonical UAT: `{artifact}`",
        f"- SHA-256: `{digest}`",
        f"- Passing tests: `{test_count}`",
        f"- Recorded: {datetime.now(timezone.utc).isoformat()}",
    ]
    if notes.strip():
        lines.extend(["", "## Notes", "", notes.strip()])
    return "\n".join(lines) + "\n"


def _read_regular_file_no_follow(path: Path) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError as error:
        raise ValueError("uat_artifact_missing") from error
    except OSError as error:
        raise ValueError("uat_artifact_unreadable") from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("uat_artifact_not_regular")
        if metadata.st_size > MAX_UAT_BYTES:
            raise ValueError("uat_artifact_too_large")
        chunks: list[bytes] = []
        size = 0
        while True:
            chunk = os.read(descriptor, min(65536, MAX_UAT_BYTES + 1 - size))
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_UAT_BYTES:
                raise ValueError("uat_artifact_too_large")
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _parse_safe_frontmatter(text: str) -> tuple[dict[str, str], str, str | None]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return {}, text, "uat_frontmatter_missing"
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}, text, "uat_frontmatter_malformed"
    fields: dict[str, str] = {}
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith((" ", "\t")) or ":" not in raw:
            # Nested/list values are irrelevant to the trusted scalar subset.
            continue
        key, value = raw.split(":", 1)
        key = key.strip()
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key) or key in fields:
            return {}, text, "uat_frontmatter_malformed"
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        fields[key] = value
    return fields, "\n".join(lines[end + 1 :]), None


def _strip_nonsemantic_markdown(text: str) -> tuple[str, str | None]:
    # Remove HTML comments first. An unclosed comment fails closed.
    without_comments: list[str] = []
    cursor = 0
    while cursor < len(text):
        start = text.find("<!--", cursor)
        if start < 0:
            without_comments.append(text[cursor:])
            break
        without_comments.append(text[cursor:start])
        end = text.find("-->", start + 4)
        if end < 0:
            return "", "uat_markdown_malformed"
        cursor = end + 3
    uncommented = "".join(without_comments)

    output: list[str] = []
    fence_char: str | None = None
    fence_length = 0
    for line in uncommented.splitlines():
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            marker = match.group(1)
            if fence_char is None:
                fence_char = marker[0]
                fence_length = len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_length:
                fence_char = None
                fence_length = 0
            continue
        if fence_char is None and not re.match(r"^\s*>", line):
            output.append(line)
    if fence_char is not None:
        return "", "uat_markdown_malformed"
    return "\n".join(output), None


def _markdown_section(text: str, heading: str, *, required: bool = True) -> tuple[str | None, str | None]:
    matches = list(re.finditer(rf"(?m)^##\s+{re.escape(heading)}\s*$", text))
    if not matches:
        return (None, f"uat_{heading.casefold()}_missing") if required else (None, None)
    if len(matches) != 1:
        return None, "uat_markdown_ambiguous"
    start = matches[0].end()
    next_heading = re.search(r"(?m)^##\s+", text[start:])
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end].strip(), None


def _parse_uat_tests(text: str) -> tuple[list[str], str | None]:
    section, error = _markdown_section(text, "Tests")
    if error or section is None:
        return [], error or "uat_tests_missing"
    headings = list(re.finditer(r"(?m)^###\s+(\d+)\.\s+.+$", section))
    if not headings:
        return [], "uat_tests_missing"
    results: list[str] = []
    for index, heading in enumerate(headings):
        start = heading.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(section)
        block = section[start:end]
        matches = re.findall(r"(?mi)^result:[ \t]*\[?([A-Za-z_-]+)\]?[ \t]*$", block)
        if len(matches) != 1:
            return [], "uat_tests_malformed"
        results.append(matches[0].casefold())
    return results, None


def _parse_uat_summary(text: str) -> tuple[dict[str, int], str | None]:
    section, error = _markdown_section(text, "Summary")
    if error or section is None:
        return {}, error or "uat_summary_missing"
    summary: dict[str, int] = {}
    for key, raw_value in re.findall(
        r"(?mi)^(total|passed|issues|pending|skipped|blocked):[ \t]*(\d+)[ \t]*$",
        section,
    ):
        normalized = key.casefold()
        if normalized in summary:
            return {}, "uat_summary_malformed"
        summary[normalized] = int(raw_value)
    if not {"total", "passed", "issues", "pending"}.issubset(summary):
        return {}, "uat_summary_malformed"
    return summary, None


def verification_path(repo: Path, command: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return verification_root(repo) / f"{timestamp}-{sanitize_filename(command)}.md"


def verification_record(command: str, status: str, notes: str) -> str:
    lines = [
        "# Verification Record",
        "",
        f"- Command: `{command}`",
        f"- Result: `{status}`",
        f"- Recorded: {datetime.now(timezone.utc).isoformat()}",
    ]
    if notes:
        lines.extend(["", "## Notes", "", notes])
    return "\n".join(lines) + "\n"
