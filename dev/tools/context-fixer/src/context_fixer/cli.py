from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analyzer import analyze_context
from .onboarding import apply_first_run_dependency_guidance, render_trace_required_guidance
from .render import render_html, render_text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Context Fixer: diagnose Codex context usage and AI project configuration.")
    parser.add_argument("--repo", default=".", help="Project repository to audit.")
    parser.add_argument("--cwd", default=None, help="Working directory to use for AGENTS.md discovery. Defaults to --repo.")
    parser.add_argument("--codex-home", default=str(Path.home() / ".codex"), help="Codex home directory.")
    parser.add_argument("--session", action="append", default=[], help="Session JSONL file. Repeat to analyze multiple sessions.")
    parser.add_argument("--trace", action="append", default=[], help="Request trace JSONL file. Repeat to analyze multiple traces.")
    parser.add_argument("--session-only", action="store_true", help="Explicitly analyze session logs without request trace evidence.")
    parser.add_argument("--latest-sessions", type=int, default=5, help="Number of recent matching sessions to inspect when --session is omitted.")
    parser.add_argument("--json", action="store_true", help="Print the raw JSON report.")
    parser.add_argument("--html", metavar="PATH", help="Write a static HTML report to PATH.")
    parser.add_argument(
        "--fail-on-severity",
        choices=["low", "medium", "high", "critical"],
        default=None,
        help="Exit non-zero when diagnosis severity is at or above this threshold.",
    )
    args = parser.parse_args(argv)

    if not args.trace and not args.session_only:
        print(render_trace_required_guidance(Path(args.repo)))
        return 3

    report = analyze_context(
        repo=Path(args.repo),
        cwd=Path(args.cwd) if args.cwd else None,
        codex_home=Path(args.codex_home),
        sessions=[Path(item) for item in args.session] if args.session else None,
        traces=[Path(item) for item in args.trace] if args.trace else None,
        latest_sessions=args.latest_sessions,
    )
    apply_first_run_dependency_guidance(report, Path(args.repo), trace_supplied=bool(args.trace))
    if args.html:
        html_path = Path(args.html).expanduser().resolve()
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(render_html(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    elif args.html:
        print(f"Wrote HTML report to {html_path}")
    else:
        print(render_text(report))
    if not report["ok"]:
        return 1
    if args.fail_on_severity:
        order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        if order[report["diagnosis"]["severity"]] >= order[args.fail_on_severity]:
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
