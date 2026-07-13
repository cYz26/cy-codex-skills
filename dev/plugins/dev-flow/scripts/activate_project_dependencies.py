#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from workflow_project_activation import activate_project_dependencies
from workflow_provider_registry import CAPABILITY_IDS, default_plugin_root, load_provider_registry


def main() -> int:
    parser = argparse.ArgumentParser(description="Activate orchestrator dependencies in one target repo.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--plugin-root", default=None)
    parser.add_argument("--codex-home", default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report commands and link actions without changing the project (default).",
    )
    parser.add_argument(
        "--skip-official-installs",
        action="store_true",
        help="Only install project-local orchestrator/Superpowers skills; do not run GSD/OpenSpec installers.",
    )
    parser.add_argument(
        "--refresh-project-skills",
        action="store_true",
        help="Refresh project-local symlinks that point at an older provider skill source.",
    )
    parser.add_argument(
        "--migrate-official-skill-layout",
        action="store_true",
        help="Plan or apply migration from legacy .codex/skills to official .agents/skills.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply dependency, skill-link, persistence, and requested migration changes.",
    )
    registry = load_provider_registry(default_plugin_root())
    parser.add_argument(
        "--methodology-profile",
        choices=sorted(registry["methodologyProfiles"]),
        help="Temporarily select a methodology profile; persistence requires explicit authorization.",
    )
    parser.add_argument(
        "--roadmap-provider",
        choices=sorted(registry["roadmapProviders"]),
        help="Temporarily select a roadmap provider; persistence requires explicit authorization.",
    )
    parser.add_argument(
        "--provider-source",
        action="append",
        default=[],
        metavar="PROVIDER=SOURCE_ID",
        help="Dry-run source override. Repeat for multiple selected providers.",
    )
    parser.add_argument(
        "--persist-provider-selection",
        action="store_true",
        help="Persist approved profile, roadmap, or source overrides; requires --apply.",
    )
    parser.add_argument(
        "--capability",
        action="append",
        choices=sorted(CAPABILITY_IDS),
        default=[],
        help="Activate and require one routed capability. Repeat for multiple capabilities.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.dry_run and args.apply:
        parser.error("--dry-run and --apply are mutually exclusive")
    report = activate_project_dependencies(
        args.repo,
        not args.apply,
        args.skip_official_installs,
        args.plugin_root,
        args.codex_home,
        args.refresh_project_skills,
        args.migrate_official_skill_layout,
        args.apply,
        args.provider_source,
        args.persist_provider_selection,
        triggered_capabilities=set(args.capability),
        methodology_profile=args.methodology_profile,
        roadmap_provider=args.roadmap_provider,
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("OK" if report["ok"] else "FAIL")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
