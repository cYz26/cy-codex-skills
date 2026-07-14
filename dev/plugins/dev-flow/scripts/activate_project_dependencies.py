#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from workflow_methodology import CAPABILITY_IDS
from workflow_project_activation import activate_project_dependencies


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Plan or activate DevFlow, OpenSpec, and triggered Matt skills in one project."
    )
    parser.add_argument("--repo", required=True)
    parser.add_argument("--plugin-root", default=None)
    parser.add_argument("--codex-home", default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report commands and project-local skill actions without writing (default).",
    )
    parser.add_argument(
        "--skip-official-installs",
        action="store_true",
        help="Skip isolated OpenSpec generation; only plan or apply checked-in project skills.",
    )
    parser.add_argument(
        "--refresh-project-skills",
        action="store_true",
        help="Refresh verified generated or checked-in project-local skill copies.",
    )
    parser.add_argument(
        "--migrate-official-skill-layout",
        action="store_true",
        help="Plan or apply migration from legacy .codex/skills to official .agents/skills.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply dependency and project-local skill changes.",
    )
    parser.add_argument(
        "--capability",
        action="append",
        choices=sorted(CAPABILITY_IDS),
        default=[],
        help="Activate and require one static DevFlow capability. Repeat as needed.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.dry_run and args.apply:
        parser.error("--dry-run and --apply are mutually exclusive")

    apply = bool(args.apply)
    report = activate_project_dependencies(
        args.repo,
        dry_run=not apply,
        skip_official_installs=args.skip_official_installs,
        plugin_root=args.plugin_root,
        codex_home=args.codex_home,
        refresh_project_skills=args.refresh_project_skills,
        migrate_official_skill_layout=args.migrate_official_skill_layout,
        apply_skill_layout_migration=apply and args.migrate_official_skill_layout,
        authorizations={"explicit_named_dependency_request"} if apply else set(),
        triggered_capabilities=set(args.capability),
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("OK" if report["ok"] else "FAIL")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
