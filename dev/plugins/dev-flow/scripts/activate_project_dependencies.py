#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from workflow_project_activation import activate_project_dependencies
from workflow_provider_deactivation import (
    SUPPORTED_PROVIDER_DEACTIVATIONS,
    deactivate_project_provider_skills,
)
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
        help="Skip official installers; only plan or apply selected project-local provider skill links.",
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
    parser.add_argument(
        "--deactivate-provider",
        choices=SUPPORTED_PROVIDER_DEACTIVATIONS,
        help=(
            "Enumerate obsolete project/legacy provider links; removal still requires "
            "--apply and named authorization."
        ),
    )
    parser.add_argument(
        "--authorize-provider-cleanup",
        choices=SUPPORTED_PROVIDER_DEACTIVATIONS,
        help="Name the provider whose verified symlinks may be removed with --apply.",
    )
    parser.add_argument(
        "--provider-cleanup-plan",
        help="Authorize exactly the planDigest emitted by a prior provider cleanup dry-run.",
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
    if args.authorize_provider_cleanup and not args.deactivate_provider:
        parser.error("--authorize-provider-cleanup requires --deactivate-provider")
    if args.provider_cleanup_plan and not args.deactivate_provider:
        parser.error("--provider-cleanup-plan requires --deactivate-provider")
    # Provider cleanup is deliberately isolated from ordinary dependency
    # activation. Even a valid cleanup digest must not install dependencies,
    # refresh links, or persist selection as an unplanned side effect.
    activation_apply = args.apply and args.deactivate_provider is None
    report = activate_project_dependencies(
        args.repo,
        not activation_apply,
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
    provider_deactivation = None
    if args.deactivate_provider:
        cleanup_args = {
            "codex_home": args.codex_home or report["codex_home"],
            "authorized_provider": args.authorize_provider_cleanup,
            "authorized_plan_digest": args.provider_cleanup_plan,
            "selection": report.get("selection"),
        }
        prerequisite_reasons = provider_cleanup_prerequisite_failures(args, report)
        if args.apply and prerequisite_reasons:
            provider_deactivation = deactivate_project_provider_skills(
                args.repo,
                args.deactivate_provider,
                args.plugin_root or report["plugin_root"],
                apply=False,
                **cleanup_args,
            )
            provider_deactivation = block_provider_deactivation(
                provider_deactivation,
                prerequisite_reasons,
                args.provider_cleanup_plan,
            )
        else:
            provider_deactivation = deactivate_project_provider_skills(
                args.repo,
                args.deactivate_provider,
                args.plugin_root or report["plugin_root"],
                apply=args.apply,
                **cleanup_args,
            )
        report["provider_deactivation"] = provider_deactivation
        report.setdefault("side_effects", {})["destructive.cleanup"] = provider_deactivation[
            "sideEffect"
        ]
        report["ok"] = bool(report["ok"] and provider_deactivation["ok"])
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("OK" if report["ok"] else "FAIL")
    return 0 if report["ok"] else 1


def provider_cleanup_prerequisite_failures(
    args: argparse.Namespace,
    report: dict,
) -> list[str]:
    if not args.apply:
        return []
    reasons: list[str] = []
    if not report.get("ok", False):
        reasons.append("activation_failed")
    if report.get("writes_blocked", False):
        reasons.append("activation_writes_blocked")
    selection = report.get("selection", {})
    if (
        selection.get("selectionSource") != "explicit_config"
        or selection.get("explicitMethodologyProfile") in (None, "")
        or selection.get("explicitRoadmapProvider") in (None, "")
    ):
        reasons.append("selection_not_persisted")
    has_selection_overrides = bool(
        args.methodology_profile
        or args.roadmap_provider
        or args.provider_source
    )
    persistence = report.get("provider_persistence", {})
    if has_selection_overrides and not (
        args.persist_provider_selection
        and persistence.get("ok", False)
        and persistence.get("status") in {"applied", "current"}
    ):
        reasons.append("selection_not_persisted")
    return list(dict.fromkeys(reasons))


def block_provider_deactivation(
    report: dict,
    reasons: list[str],
    authorized_plan_digest: str | None,
) -> dict:
    for item in report.get("items", []):
        if item.get("verified"):
            item["status"] = "preserved_activation_prerequisite_failed"
    return {
        **report,
        "ok": False,
        "status": "activation_prerequisite_failed",
        "mode": "blocked",
        "requestedMode": "apply",
        "changed": False,
        "authorizedPlanDigest": authorized_plan_digest,
        "planDigestMatches": bool(
            authorized_plan_digest
            and authorized_plan_digest == report.get("planDigest")
        ),
        "removed": [],
        "preserved": [
            item["path"]
            for item in report.get("items", [])
            if item.get("status", "").startswith("preserved_")
        ],
        "blockingReasons": reasons,
    }


if __name__ == "__main__":
    raise SystemExit(main())
