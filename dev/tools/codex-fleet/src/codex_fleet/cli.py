from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

from .core import (
    FleetError,
    SCHEMA_VERSION,
    apply_bootstrap,
    bootstrap_preview,
    inventory,
    parse_named_values,
    parse_projects,
)
from .sync import plan_sync
from .executor import apply_sync
from .lifecycle import rollback_fleet_receipt, verify_fleet_receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex-fleet",
        description="Plan, apply, verify, or roll back declarative Codex plugin fleet synchronization.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory_parser = subparsers.add_parser(
        "inventory", help="List candidate marketplaces, plugins, and explicitly named projects."
    )
    _add_inventory_arguments(inventory_parser)

    bootstrap_parser = subparsers.add_parser(
        "bootstrap", help="Preview or explicitly write the first managed fleet profile."
    )
    _add_inventory_arguments(bootstrap_parser)
    bootstrap_parser.add_argument("--apply", action="store_true", help="Write the exact proposed profile.")
    bootstrap_parser.add_argument("--marketplace-git", action="append", default=[], metavar="NAME=URL")
    bootstrap_parser.add_argument("--marketplace-ref", action="append", default=[], metavar="NAME=REF")
    bootstrap_parser.add_argument(
        "--marketplace-channel", action="append", default=[], metavar="NAME=CHANNEL"
    )

    sync_parser = subparsers.add_parser("sync", help="Plan or apply managed fleet convergence.")
    _add_paths(sync_parser)
    sync_parser.add_argument("--apply", action="store_true")
    sync_parser.add_argument("--advance-lock", action="store_true")
    sync_parser.add_argument("--state-dir", default=_default_state_path())
    sync_parser.add_argument("--json", action="store_true")

    verify_parser = subparsers.add_parser("verify", help="Freshly verify a fleet receipt.")
    verify_parser.add_argument("--receipt", required=True)
    verify_parser.add_argument("--json", action="store_true")

    rollback_parser = subparsers.add_parser("rollback", help="Plan or apply receipt-bound rollback.")
    rollback_parser.add_argument("--receipt", required=True)
    rollback_parser.add_argument("--apply", action="store_true")
    rollback_parser.add_argument("--json", action="store_true")
    return parser


def _add_inventory_arguments(parser: argparse.ArgumentParser) -> None:
    _add_paths(parser)
    parser.add_argument("--project", action="append", default=[], metavar="ID=PATH")
    parser.add_argument("--json", action="store_true")


def _add_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--manifest", default="codex-fleet.json")
    parser.add_argument("--lock", default="codex-fleet.lock.json")
    parser.add_argument("--device", default=_default_device_path())
    parser.add_argument("--codex-home", default=str(Path.home() / ".codex"))


def _default_device_path() -> str:
    root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return str(root / "codex-fleet" / "default.device.json")


def _default_state_path() -> str:
    root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return str(root / "codex-fleet")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "inventory":
            report = inventory(
                codex_home=Path(args.codex_home).expanduser().resolve(),
                projects=parse_projects(args.project),
            )
        elif args.command == "bootstrap":
            report = bootstrap_preview(
                codex_home=Path(args.codex_home).expanduser().resolve(),
                projects=parse_projects(args.project),
                manifest_path=Path(args.manifest).expanduser().absolute(),
                lock_path=Path(args.lock).expanduser().absolute(),
                device_path=Path(args.device).expanduser().absolute(),
                marketplace_git=parse_named_values(args.marketplace_git, label="marketplace Git source"),
                marketplace_refs=parse_named_values(args.marketplace_ref, label="marketplace ref"),
                marketplace_channels=parse_named_values(
                    args.marketplace_channel, label="marketplace channel"
                ),
            )
            if args.apply:
                report = apply_bootstrap(report)
        elif args.command == "sync":
            report = plan_sync(
                manifest_path=Path(args.manifest).expanduser().absolute(),
                lock_path=Path(args.lock).expanduser().absolute(),
                device_path=Path(args.device).expanduser().absolute(),
                codex_home=Path(args.codex_home).expanduser().resolve(),
                advance_lock=bool(args.advance_lock),
            )
            if args.apply:
                report = apply_sync(report, state_dir=Path(args.state_dir))
        elif args.command == "verify":
            report = verify_fleet_receipt(Path(args.receipt))
        elif args.command == "rollback":
            report = rollback_fleet_receipt(Path(args.receipt), apply=bool(args.apply))
        else:
            raise FleetError(f"{args.command} is not implemented yet", status="not_implemented")
    except FleetError as error:
        report = {
            "schemaVersion": SCHEMA_VERSION,
            "kind": f"codex-fleet-{args.command}",
            "ok": False,
            "status": error.status,
            "error": str(error),
            "nextAction": "Correct the reported input or runtime boundary and retry.",
        }
    exit_code = _exit_code(report)
    report.setdefault("exitCode", exit_code)
    report.setdefault("actions", [])
    report.setdefault("results", [])
    _render(report, json_output=bool(getattr(args, "json", False)))
    return exit_code


def _render(report: dict[str, Any], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
        return
    print(f"{report['kind']}: {report['status']}")
    if report.get("error"):
        print(f"error: {report['error']}")
    for blocker in report.get("blockers", []):
        print(
            "blocker: "
            f"{blocker.get('code', 'unknown')} "
            f"{blocker.get('subject', 'unknown')} - {blocker.get('detail', '')}"
        )
    if report.get("manualActions"):
        print(f"manual actions: {len(report['manualActions'])}")
    if report.get("actions"):
        print(f"planned actions: {len(report['actions'])}")
    next_action = report.get("nextAction")
    if next_action:
        print(next_action)


def _exit_code(report: dict[str, Any]) -> int:
    if report.get("status") in {
        "candidates",
        "preview",
        "manual_required",
        "applied_with_manual_actions",
        "verified_with_manual_actions",
        "rollback_preview",
        "rollback_incomplete",
    }:
        return 2
    if report.get("ok"):
        return 0
    return 3


if __name__ == "__main__":
    sys.exit(main())
