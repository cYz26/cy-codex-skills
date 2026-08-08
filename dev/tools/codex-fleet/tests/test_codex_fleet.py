from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
import fcntl
import hashlib
from pathlib import Path


TOOL_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = TOOL_ROOT / "src"
REPO_ROOT = TOOL_ROOT.parents[2]


class CodexFleetCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name).resolve()
        self.codex_home = self.root / "codex-home"
        self.codex_home.mkdir()
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.command_log = self.root / "codex-commands.jsonl"
        self.adapter_log = self.root / "adapter-commands.jsonl"
        self.runtime_state = self.root / "codex-state.json"
        self.marketplace_root = self.root / "marketplaces" / "cy-codex-skills"
        self.devflow_source = self.marketplace_root / "plugins" / "dev-flow"
        self.stateless_source = self.marketplace_root / "plugins" / "stateless-tools"
        self._make_plugin(self.devflow_source, "dev-flow", "1.2.3", adapter=True)
        self._make_plugin(self.stateless_source, "stateless-tools", "2.0.0")
        self._make_catalog()
        self._make_cache("dev-flow", "1.2.3", self.devflow_source)
        self._make_cache("stateless-tools", "2.0.0", self.stateless_source)
        self.project = self.root / "projects" / "game-one"
        (self.project / ".planning" / "devflow").mkdir(parents=True)
        (self.project / ".planning" / "devflow" / "STATE.md").write_text(
            "---\nworkflow_version: 0.3.0\n---\n",
            encoding="utf-8",
        )
        self._write_runtime_state()
        self._write_fake_codex()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _make_plugin(
        self,
        root: Path,
        name: str,
        version: str,
        *,
        adapter: bool = False,
    ) -> None:
        manifest = root / ".codex-plugin" / "plugin.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(
            json.dumps({"name": name, "version": version}, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (root / "skills" / f"{name}-skill").mkdir(parents=True)
        (root / "skills" / f"{name}-skill" / "SKILL.md").write_text(
            f"---\nname: {name}-skill\ndescription: fixture\n---\n",
            encoding="utf-8",
        )
        if adapter:
            script = root / "scripts" / "plugin_project_migration.py"
            script.parent.mkdir(parents=True)
            script.write_text(
                """from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path

parser = argparse.ArgumentParser()
sub = parser.add_subparsers(dest="command", required=True)
for name in ("plan", "apply", "verify", "rollback"):
    item = sub.add_parser(name)
    item.add_argument("--repo", required=True)
    item.add_argument("--plugin-root", required=True)
    item.add_argument("--codex-home")
    item.add_argument("--json", action="store_true")
    if name == "apply":
        item.add_argument("--expect-plan", required=True)
        item.add_argument("--allow", action="append", default=[])
        item.add_argument("--action", action="append", default=[])
    if name in ("verify", "rollback"):
        item.add_argument("--receipt", required=True)
    if name == "rollback":
        item.add_argument("--apply", action="store_true", dest="rollback_apply")
args = parser.parse_args()
with Path(os.environ["FAKE_ADAPTER_LOG"]).open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(__import__("sys").argv[1:]) + "\\n")
repo = Path(args.repo).resolve()

def make_plan():
    plan = {
        "schemaVersion": "1.0",
        "kind": "devflow-project-refresh-plan",
        "ok": True,
        "status": "migration_pending",
        "repo": str(repo),
        "actions": [
            {"id": "refresh-managed-skills", "authorization": "project-refresh-apply", "path": ".agents/skills"},
            {"id": "migrate-workflow-config", "authorization": "workflow-config-migration", "path": ".dev-flow.json"},
        ],
        "requiredAuthorizations": ["project-refresh-apply", "workflow-config-migration"],
        "manualActions": [],
        "preservedPaths": ["AGENTS.md"],
    }
    encoded = json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()
    plan["planSha256"] = "sha256:" + hashlib.sha256(encoded).hexdigest()
    return plan

if args.command == "plan":
    print(json.dumps(make_plan()))
    raise SystemExit(2)
if args.command == "apply":
    plan = make_plan()
    if args.expect_plan != plan["planSha256"]:
        print(json.dumps({"ok": False, "status": "plan_stale"}))
        raise SystemExit(3)
    if args.allow != ["project-refresh-apply"] or args.action != ["refresh-managed-skills"]:
        print(json.dumps({"ok": False, "status": "authorization_required", "allow": args.allow, "actions": args.action}))
        raise SystemExit(3)
    changed = repo / ".fake-devflow-refreshed"
    changed.write_text("refreshed\\n")
    receipt = repo / ".planning" / "devflow" / "fake-apply-receipt.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps({"kind": "fake-devflow-receipt", "repo": str(repo), "changed": str(changed)}) + "\\n")
    if os.environ.get("FAKE_ADAPTER_CORRUPT_AFTER_APPLY") == "1":
        changed.write_text("corrupt after apply\\n")
    print(json.dumps({
        "ok": True,
        "status": "applied_incomplete",
        "receiptPath": str(receipt),
        "changedPaths": [str(changed)],
        "remainingAuthorizations": ["workflow-config-migration"],
        "manualActions": [],
    }))
    raise SystemExit(2)
if args.command == "verify":
    receipt = json.loads(Path(args.receipt).read_text())
    changed = Path(receipt["changed"])
    ok = receipt.get("repo") == str(repo) and changed.read_text() == "refreshed\\n"
    print(json.dumps({
        "ok": False if ok else False,
        "status": "verified_incomplete" if ok else "verification_failed",
        "issues": [] if ok else ["changed_state_drift"],
        "completionIssues": ["workflow-config-migration_pending"] if ok else [],
        "receiptPath": str(Path(args.receipt).resolve()),
    }))
    raise SystemExit(2 if ok else 3)
if args.command == "rollback":
    receipt = json.loads(Path(args.receipt).read_text())
    changed = Path(receipt["changed"])
    if not args.rollback_apply:
        print(json.dumps({"ok": False, "status": "authorization_required", "changedPaths": []}))
        raise SystemExit(2)
    if os.environ.get("FAKE_ADAPTER_FAIL_ROLLBACK_REPO") == str(repo):
        print(json.dumps({"ok": False, "status": "rollback_failed", "changedPaths": []}))
        raise SystemExit(3)
    if changed.exists():
        changed.unlink()
    print(json.dumps({"ok": True, "status": "rolled_back", "changedPaths": [str(changed)]}))
    raise SystemExit(0)
""",
                encoding="utf-8",
            )

    def _make_catalog(self) -> None:
        catalog = self.marketplace_root / ".agents" / "plugins" / "marketplace.json"
        catalog.parent.mkdir(parents=True)
        catalog.write_text(
            json.dumps(
                {
                    "name": "cy-codex-skills",
                    "plugins": [
                        {"name": "dev-flow", "source": {"path": "./plugins/dev-flow"}},
                        {
                            "name": "stateless-tools",
                            "source": {"path": "./plugins/stateless-tools"},
                        },
                    ],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def _make_cache(self, name: str, version: str, source: Path) -> None:
        target = self.codex_home / "plugins" / "cache" / "cy-codex-skills" / name / version
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)

    def _write_runtime_state(self) -> None:
        self.runtime_state.write_text(
            json.dumps(
                {
                    "marketplaces": {
                        "marketplaces": [
                            {
                                "name": "cy-codex-skills",
                                "root": str(self.marketplace_root),
                                "marketplaceSource": {
                                    "sourceType": "local",
                                    "source": str(self.marketplace_root),
                                },
                            }
                        ]
                    },
                    "plugins": {
                        "installed": [
                            {
                                "pluginId": "dev-flow@cy-codex-skills",
                                "name": "dev-flow",
                                "marketplaceName": "cy-codex-skills",
                                "version": "1.2.3",
                                "installed": True,
                                "enabled": True,
                                "source": {"source": "local", "path": str(self.devflow_source)},
                                "marketplaceSource": {
                                    "sourceType": "local",
                                    "source": str(self.marketplace_root),
                                },
                            },
                            {
                                "pluginId": "stateless-tools@cy-codex-skills",
                                "name": "stateless-tools",
                                "marketplaceName": "cy-codex-skills",
                                "version": "2.0.0",
                                "installed": True,
                                "enabled": True,
                                "source": {"source": "local", "path": str(self.stateless_source)},
                                "marketplaceSource": {
                                    "sourceType": "local",
                                    "source": str(self.marketplace_root),
                                },
                            },
                            {
                                "pluginId": "disabled@cy-codex-skills",
                                "name": "disabled",
                                "marketplaceName": "cy-codex-skills",
                                "version": "9.0.0",
                                "installed": True,
                                "enabled": False,
                            },
                        ],
                        "available": [],
                    },
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def _write_fake_codex(self) -> None:
        executable = self.bin_dir / "codex"
        executable.write_text(
            """#!/usr/bin/env python3
import json
import os
import re
import shutil
import sys
from pathlib import Path

state_path = Path(os.environ["FAKE_CODEX_STATE"])
state = json.loads(state_path.read_text())
with Path(os.environ["FAKE_CODEX_LOG"]).open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(sys.argv[1:]) + "\\n")
args = sys.argv[1:]

def save_state():
    state_path.write_text(json.dumps(state, sort_keys=True) + "\\n")

def mutate_bound_file_if_requested():
    expected = os.environ.get("FAKE_CODEX_MUTATE_AFTER")
    if expected and " ".join(args) == expected:
        selected = Path(os.environ["FAKE_CODEX_MUTATE_PATH"])
        symlink_target = os.environ.get("FAKE_CODEX_REPLACE_WITH_SYMLINK_TARGET")
        if symlink_target:
            selected.unlink()
            selected.symlink_to(symlink_target)
        else:
            selected.write_text(os.environ.get("FAKE_CODEX_MUTATE_CONTENT", "{}\\n"))

def mutate_unrelated_runtime_if_requested(selector):
    if os.environ.get("FAKE_CODEX_MUTATE_UNRELATED_AFTER") != selector:
        return
    unrelated = next(
        item
        for item in state["plugins"]["installed"]
        if item.get("pluginId") == os.environ["FAKE_CODEX_UNRELATED_SELECTOR"]
    )
    unrelated["version"] = os.environ.get("FAKE_CODEX_UNRELATED_VERSION", "99.0.0")
    save_state()

if args == ["plugin", "marketplace", "list", "--json"]:
    print(json.dumps(state["marketplaces"]))
    raise SystemExit(0)
if args == ["plugin", "list", "--available", "--json"]:
    print(json.dumps(state["plugins"]))
    remove_path = os.environ.get("FAKE_CODEX_REMOVE_ON_PLUGIN_LIST")
    if remove_path:
        Path(remove_path).unlink(missing_ok=True)
    raise SystemExit(0)
if len(args) == 5 and args[:3] == ["plugin", "marketplace", "upgrade"] and args[4] == "--json":
    update = json.loads(Path(os.environ["FAKE_CODEX_UPGRADE_STATE"]).read_text())
    for plugin in state["plugins"]["installed"]:
        selected = update.get("plugins", {}).get(plugin.get("name"))
        source = plugin.get("source", {}).get("path")
        if not selected or not source:
            continue
        manifest = Path(source) / ".codex-plugin" / "plugin.json"
        payload = json.loads(manifest.read_text())
        payload["version"] = selected["version"]
        manifest.write_text(json.dumps(payload, sort_keys=True) + "\\n")
        (Path(source) / "upgrade.txt").write_text(selected.get("content", selected["version"]) + "\\n")
    config = Path(os.environ["CODEX_HOME"]) / "config.toml"
    text = config.read_text()
    text = re.sub(r'last_revision = "[^"]+"', f'last_revision = "{update["revision"]}"', text)
    config.write_text(text)
    mutate_bound_file_if_requested()
    print(json.dumps({"ok": True, "marketplace": args[3], "revision": update["revision"]}))
    raise SystemExit(0)
if len(args) == 4 and args[:2] == ["plugin", "add"] and args[3] == "--json":
    selector = args[2]
    plugin = next(item for item in state["plugins"]["installed"] if item.get("pluginId") == selector)
    source = Path(plugin["source"]["path"])
    payload = json.loads((source / ".codex-plugin" / "plugin.json").read_text())
    plugin["version"] = payload["version"]
    target = Path(os.environ["CODEX_HOME"]) / "plugins" / "cache" / plugin["marketplaceName"] / plugin["name"] / plugin["version"]
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)
    if os.environ.get("FAKE_CODEX_CORRUPT_CACHE_SELECTOR") == selector:
        (target / "corrupt.txt").write_text("corrupt\\n")
    save_state()
    mutate_unrelated_runtime_if_requested(selector)
    mutate_bound_file_if_requested()
    print(json.dumps({"ok": True, "pluginId": selector, "version": plugin["version"]}))
    raise SystemExit(0)
print(json.dumps({"error": "unexpected fake codex command", "args": args}))
raise SystemExit(9)
""",
            encoding="utf-8",
        )
        executable.chmod(0o755)

    def run_cli(
        self,
        *args: str,
        extra_env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(
            {
                "PYTHONPATH": str(SOURCE_ROOT),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PATH": f"{self.bin_dir}{os.pathsep}{env.get('PATH', '')}",
                "FAKE_CODEX_STATE": str(self.runtime_state),
                "FAKE_CODEX_LOG": str(self.command_log),
                "FAKE_ADAPTER_LOG": str(self.adapter_log),
            }
        )
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, "-m", "codex_fleet", *args],
            cwd=self.root,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def read_commands(self) -> list[list[str]]:
        if not self.command_log.exists():
            return []
        return [json.loads(line) for line in self.command_log.read_text().splitlines()]

    def read_adapter_commands(self) -> list[list[str]]:
        if not self.adapter_log.exists():
            return []
        return [json.loads(line) for line in self.adapter_log.read_text().splitlines()]

    def profile_paths(self) -> tuple[Path, Path, Path]:
        return (
            self.root / "profile" / "codex-fleet.json",
            self.root / "profile" / "codex-fleet.lock.json",
            self.root / "device.json",
        )

    def bootstrap_profile(self, *projects: tuple[str, Path]) -> tuple[Path, Path, Path]:
        manifest, lock, device = self.profile_paths()
        args = [
            "bootstrap",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
        ]
        for project_id, path in projects:
            args.extend(["--project", f"{project_id}={path}"])
        args.extend(["--apply", "--json"])
        result = self.run_cli(*args)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        if self.command_log.exists():
            self.command_log.unlink()
        return manifest, lock, device

    def make_second_project(self) -> Path:
        project = self.root / "projects" / "game-two"
        (project / ".planning" / "devflow").mkdir(parents=True)
        (project / ".planning" / "devflow" / "STATE.md").write_text(
            "---\nworkflow_version: 0.3.0\n---\n",
            encoding="utf-8",
        )
        return project

    def make_git_marketplace(self) -> None:
        source = "git@github.com:cYz26/cy-codex-skills.git"
        state = json.loads(self.runtime_state.read_text())
        marketplace = state["marketplaces"]["marketplaces"][0]
        marketplace["marketplaceSource"] = {"sourceType": "git", "source": source}
        for plugin in state["plugins"]["installed"]:
            if plugin.get("marketplaceName") == "cy-codex-skills":
                plugin["marketplaceSource"] = {"sourceType": "git", "source": source}
        self.runtime_state.write_text(json.dumps(state, sort_keys=True) + "\n", encoding="utf-8")
        (self.codex_home / "config.toml").write_text(
            """[marketplaces.cy-codex-skills]
source_type = "git"
source = "git@github.com:cYz26/cy-codex-skills.git"
ref = "v1.2.3"
last_revision = "1111111111111111111111111111111111111111"
""",
            encoding="utf-8",
        )

    def test_inventory_lists_candidates_without_adopting_or_writing(self) -> None:
        manifest = self.root / "profile" / "codex-fleet.json"
        lock = self.root / "profile" / "codex-fleet.lock.json"
        device = self.root / "device.json"

        result = self.run_cli(
            "inventory",
            "--codex-home",
            str(self.codex_home),
            "--project",
            f"game-one={self.project}",
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--json",
        )

        self.assertEqual(result.returncode, 2, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["schemaVersion"], "1.0")
        self.assertEqual(report["kind"], "codex-fleet-inventory")
        self.assertEqual(report["status"], "candidates")
        self.assertEqual(report["exitCode"], 2)
        self.assertEqual(report["actions"], [])
        self.assertEqual(report["results"], [])
        self.assertFalse(report["ok"])
        self.assertEqual(
            [item["name"] for item in report["marketplaces"]],
            ["cy-codex-skills"],
        )
        self.assertEqual(
            [item["selector"] for item in report["plugins"]],
            ["dev-flow@cy-codex-skills", "stateless-tools@cy-codex-skills"],
        )
        self.assertEqual(report["plugins"][0]["projectAdapter"], "devflow-v1")
        self.assertIsNone(report["plugins"][1]["projectAdapter"])
        self.assertEqual(
            report["skills"],
            [
                {
                    "name": "dev-flow-skill",
                    "plugin": "dev-flow@cy-codex-skills",
                },
                {
                    "name": "stateless-tools-skill",
                    "plugin": "stateless-tools@cy-codex-skills",
                },
            ],
        )
        self.assertEqual(
            report["projects"],
            [
                {
                    "adopted": False,
                    "detectedPlugins": ["dev-flow@cy-codex-skills"],
                    "detectedSkills": [
                        {
                            "name": "dev-flow-skill",
                            "plugin": "dev-flow@cy-codex-skills",
                        }
                    ],
                    "id": "game-one",
                    "path": str(self.project.resolve()),
                    "trusted": False,
                }
            ],
        )
        self.assertEqual(
            self.read_commands(),
            [
                ["plugin", "marketplace", "list", "--json"],
                ["plugin", "list", "--available", "--json"],
            ],
        )
        self.assertFalse(manifest.exists())
        self.assertFalse(lock.exists())
        self.assertFalse(device.exists())
        self.assertFalse((self.project / ".codex-fleet" / "project.json").exists())

    def test_inventory_rejects_symlinked_packaged_skill_content(self) -> None:
        skill = self.devflow_source / "skills" / "dev-flow-skill" / "SKILL.md"
        outside = self.root / "outside-skill.md"
        outside.write_text("---\nname: escaped\ndescription: outside\n---\n", encoding="utf-8")
        skill.unlink()
        skill.symlink_to(outside)

        result = self.run_cli(
            "inventory",
            "--codex-home",
            str(self.codex_home),
            "--json",
        )

        self.assertEqual(result.returncode, 3, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "identity_unavailable")
        self.assertIn("symbolic link", report["error"])

    def test_sync_reports_non_object_marketplace_metadata_as_structured_failure(self) -> None:
        catalog = self.marketplace_root / ".agents" / "plugins" / "marketplace.json"
        plugin_manifest = self.devflow_source / ".codex-plugin" / "plugin.json"
        cache_manifest = (
            self.codex_home
            / "plugins"
            / "cache"
            / "cy-codex-skills"
            / "dev-flow"
            / "1.2.3"
            / ".codex-plugin"
            / "plugin.json"
        )
        original_catalog = catalog.read_bytes()
        original_manifest = plugin_manifest.read_bytes()

        cases = {
            "catalog": "JSON object",
            "catalog-plugins": "plugins must be a JSON array",
            "catalog-record": "plugin record must be a JSON object",
            "plugin-manifest": "JSON object",
        }
        for label, expected_detail in cases.items():
            with self.subTest(label=label):
                catalog.write_bytes(original_catalog)
                plugin_manifest.write_bytes(original_manifest)
                cache_manifest.write_bytes(original_manifest)
                for path in self.profile_paths():
                    if path.exists():
                        path.unlink()
                if label == "catalog":
                    catalog.write_text("[]\n", encoding="utf-8")
                elif label == "catalog-plugins":
                    catalog.write_text('{"plugins": {}}\n', encoding="utf-8")
                elif label == "catalog-record":
                    catalog.write_text('{"plugins": [null]}\n', encoding="utf-8")
                else:
                    plugin_manifest.write_text("[]\n", encoding="utf-8")
                    cache_manifest.write_text("[]\n", encoding="utf-8")

                manifest, lock, device = self.bootstrap_profile()
                result = self.run_cli(
                    "sync",
                    "--codex-home",
                    str(self.codex_home),
                    "--manifest",
                    str(manifest),
                    "--lock",
                    str(lock),
                    "--device",
                    str(device),
                    "--json",
                )

                self.assertEqual(result.returncode, 3, result.stderr or result.stdout)
                report = json.loads(result.stdout)
                self.assertEqual(report["status"], "blocked")
                identity_blockers = [
                    item
                    for item in report["blockers"]
                    if item["code"] == "identity_unavailable"
                ]
                self.assertTrue(identity_blockers, report)
                self.assertIn(expected_detail, identity_blockers[0]["detail"])
                self.assertNotIn("Traceback", result.stderr)

    def test_bootstrap_preview_returns_exact_files_but_writes_nothing(self) -> None:
        manifest = self.root / "profile" / "codex-fleet.json"
        lock = self.root / "profile" / "codex-fleet.lock.json"
        device = self.root / "device.json"

        result = self.run_cli(
            "bootstrap",
            "--codex-home",
            str(self.codex_home),
            "--project",
            f"game-one={self.project}",
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--json",
        )

        self.assertEqual(result.returncode, 2, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["kind"], "codex-fleet-bootstrap")
        self.assertEqual(report["status"], "preview")
        self.assertFalse(report["ok"])
        self.assertFalse(report["apply"])
        proposed = report["proposed"]
        self.assertEqual(proposed["manifest"]["profile"], "default")
        self.assertEqual(
            [item["selector"] for item in proposed["manifest"]["plugins"]],
            ["dev-flow@cy-codex-skills", "stateless-tools@cy-codex-skills"],
        )
        self.assertEqual(
            proposed["manifest"]["projects"],
            [{"id": "game-one", "plugins": ["dev-flow@cy-codex-skills"]}],
        )
        self.assertEqual(proposed["device"]["projects"]["game-one"]["trusted"], True)
        self.assertEqual(
            proposed["projectMarkers"][0]["content"]["managedPlugins"],
            ["dev-flow@cy-codex-skills"],
        )
        self.assertEqual(
            set(proposed["lock"]["plugins"]),
            {"dev-flow@cy-codex-skills", "stateless-tools@cy-codex-skills"},
        )
        self.assertFalse(manifest.exists())
        self.assertFalse(lock.exists())
        self.assertFalse(device.exists())
        self.assertFalse((self.project / ".codex-fleet" / "project.json").exists())

    def test_bootstrap_apply_writes_portable_profile_device_overlay_and_marker(self) -> None:
        manifest = self.root / "profile" / "codex-fleet.json"
        lock = self.root / "profile" / "codex-fleet.lock.json"
        device = self.root / "device.json"

        result = self.run_cli(
            "bootstrap",
            "--codex-home",
            str(self.codex_home),
            "--project",
            f"game-one={self.project}",
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--apply",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["status"], "adopted")
        self.assertTrue(report["apply"])
        marker = self.project / ".codex-fleet" / "project.json"
        self.assertEqual(
            set(report["writtenPaths"]),
            {str(manifest.resolve()), str(lock.resolve()), str(device.resolve()), str(marker.resolve())},
        )
        manifest_data = json.loads(manifest.read_text())
        lock_data = json.loads(lock.read_text())
        device_data = json.loads(device.read_text())
        marker_data = json.loads(marker.read_text())
        portable_text = json.dumps({"manifest": manifest_data, "lock": lock_data})
        self.assertNotIn(str(self.root), portable_text)
        self.assertEqual(
            manifest_data["marketplaces"][0]["source"],
            "device://cy-codex-skills",
        )
        self.assertEqual(
            device_data["marketplaces"]["cy-codex-skills"]["source"],
            str(self.marketplace_root.resolve()),
        )
        self.assertEqual(device_data["projects"]["game-one"]["path"], str(self.project.resolve()))
        self.assertEqual(marker_data["projectId"], "game-one")
        self.assertEqual(marker_data["managedPlugins"], ["dev-flow@cy-codex-skills"])
        self.assertEqual(device_data["manifestSha256"], lock_data["manifestSha256"])

        second = self.run_cli(
            "bootstrap",
            "--codex-home",
            str(self.codex_home),
            "--project",
            f"game-one={self.project}",
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--apply",
            "--json",
        )
        self.assertEqual(second.returncode, 0, second.stderr or second.stdout)
        second_report = json.loads(second.stdout)
        self.assertEqual(second_report["writtenPaths"], [])
        self.assertEqual(
            set(second_report["unchangedPaths"]),
            {str(manifest.resolve()), str(lock.resolve()), str(device.resolve()), str(marker.resolve())},
        )

    def test_bootstrap_apply_preflights_all_target_conflicts_before_writing(self) -> None:
        manifest = self.root / "profile" / "codex-fleet.json"
        lock = self.root / "profile" / "codex-fleet.lock.json"
        device = self.root / "device.json"
        lock.parent.mkdir(parents=True)
        lock.write_text('{"unrelated": true}\n', encoding="utf-8")

        result = self.run_cli(
            "bootstrap",
            "--codex-home",
            str(self.codex_home),
            "--project",
            f"game-one={self.project}",
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--apply",
            "--json",
        )

        self.assertEqual(result.returncode, 3, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "target_conflict")
        self.assertFalse(manifest.exists())
        self.assertEqual(lock.read_text(), '{"unrelated": true}\n')
        self.assertFalse(device.exists())
        self.assertFalse((self.project / ".codex-fleet" / "project.json").exists())

    def test_bootstrap_rejects_duplicate_project_and_stable_main_before_codex(self) -> None:
        manifest = self.root / "profile" / "codex-fleet.json"
        lock = self.root / "profile" / "codex-fleet.lock.json"
        device = self.root / "device.json"

        duplicate = self.run_cli(
            "bootstrap",
            "--codex-home",
            str(self.codex_home),
            "--project",
            f"game-one={self.project}",
            "--project",
            f"game-one={self.project}",
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--apply",
            "--json",
        )
        self.assertEqual(duplicate.returncode, 3, duplicate.stderr or duplicate.stdout)
        self.assertEqual(json.loads(duplicate.stdout)["status"], "invalid_request")
        self.assertEqual(self.read_commands(), [])

        stable_main = self.run_cli(
            "bootstrap",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--marketplace-git",
            "cy-codex-skills=git@github.com:cYz26/cy-codex-skills.git",
            "--marketplace-ref",
            "cy-codex-skills=main",
            "--marketplace-channel",
            "cy-codex-skills=stable",
            "--apply",
            "--json",
        )
        self.assertEqual(stable_main.returncode, 3, stable_main.stderr or stable_main.stdout)
        self.assertEqual(json.loads(stable_main.stdout)["status"], "invalid_manifest")
        self.assertFalse(manifest.exists())
        self.assertFalse(lock.exists())
        self.assertFalse(device.exists())

    def test_sync_rejects_invalid_profiles_and_symlinked_inputs_before_codex(self) -> None:
        manifest, lock, device = self.bootstrap_profile(("game-one", self.project))
        baseline_manifest = json.loads(manifest.read_text())
        baseline_lock = json.loads(lock.read_text())
        baseline_device = json.loads(device.read_text())

        def write_profile(
            selected_manifest: dict[str, object],
            selected_lock: dict[str, object],
            selected_device: dict[str, object],
        ) -> None:
            manifest_bytes = (
                json.dumps(
                    selected_manifest,
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=False,
                )
                + "\n"
            ).encode("utf-8")
            manifest_sha = "sha256:" + hashlib.sha256(manifest_bytes).hexdigest()
            selected_lock["manifestSha256"] = manifest_sha
            selected_device["manifestSha256"] = manifest_sha
            manifest.write_bytes(manifest_bytes)
            lock.write_text(
                json.dumps(selected_lock, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            device.write_text(
                json.dumps(selected_device, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

        mutations = {
            "unsupported-schema": lambda selected_manifest, _selected_device: selected_manifest.update(
                {"schemaVersion": "2.0"}
            ),
            "unknown-adapter": lambda selected_manifest, _selected_device: selected_manifest[
                "plugins"
            ][0].update({"projectAdapter": "shell-v1"}),
            "missing-device-mapping": lambda _selected_manifest, selected_device: selected_device[
                "projects"
            ].pop("game-one"),
            "untrusted-project": lambda _selected_manifest, selected_device: selected_device[
                "projects"
            ]["game-one"].update({"trusted": False}),
            "invalid-project-plugin": lambda selected_manifest, _selected_device: selected_manifest[
                "projects"
            ][0].update({"plugins": [{"not": "a selector"}]}),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                selected_manifest = json.loads(json.dumps(baseline_manifest))
                selected_lock = json.loads(json.dumps(baseline_lock))
                selected_device = json.loads(json.dumps(baseline_device))
                mutate(selected_manifest, selected_device)
                write_profile(selected_manifest, selected_lock, selected_device)
                if self.command_log.exists():
                    self.command_log.unlink()

                result = self.run_cli(
                    "sync",
                    "--codex-home",
                    str(self.codex_home),
                    "--manifest",
                    str(manifest),
                    "--lock",
                    str(lock),
                    "--device",
                    str(device),
                    "--state-dir",
                    str(self.root / "fleet-state-invalid"),
                    "--apply",
                    "--json",
                )

                self.assertEqual(result.returncode, 3, result.stderr or result.stdout)
                self.assertEqual(json.loads(result.stdout)["status"], "invalid_profile")
                self.assertEqual(self.read_commands(), [])

        write_profile(
            json.loads(json.dumps(baseline_manifest)),
            json.loads(json.dumps(baseline_lock)),
            json.loads(json.dumps(baseline_device)),
        )
        linked_manifest = self.root / "linked-manifest.json"
        linked_manifest.symlink_to(manifest)
        if self.command_log.exists():
            self.command_log.unlink()
        linked = self.run_cli(
            "sync",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(linked_manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--state-dir",
            str(self.root / "fleet-state-linked"),
            "--apply",
            "--json",
        )
        self.assertEqual(linked.returncode, 3, linked.stderr or linked.stdout)
        self.assertEqual(json.loads(linked.stdout)["status"], "invalid_profile")
        self.assertEqual(self.read_commands(), [])

        human = self.run_cli(
            "sync",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(linked_manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
        )
        self.assertEqual(human.returncode, 3, human.stderr or human.stdout)
        self.assertIn("error:", human.stdout)
        self.assertIn("symbolic link", human.stdout)

    def test_sync_dry_run_is_deterministic_deduplicated_and_write_free(self) -> None:
        second_project = self.make_second_project()
        manifest, lock, device = self.bootstrap_profile(
            ("game-one", self.project),
            ("game-two", second_project),
        )
        watched = [
            manifest,
            lock,
            device,
            self.project / ".codex-fleet" / "project.json",
            second_project / ".codex-fleet" / "project.json",
        ]
        before = {str(path): path.read_bytes() for path in watched}

        args = (
            "sync",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--json",
        )
        first = self.run_cli(*args)
        second = self.run_cli(*args)

        self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
        self.assertEqual(second.returncode, 0, second.stderr or second.stdout)
        first_report = json.loads(first.stdout)
        second_report = json.loads(second.stdout)
        self.assertEqual(first_report, second_report)
        self.assertEqual(first_report["kind"], "codex-fleet-plan")
        self.assertEqual(first_report["status"], "planned")
        self.assertTrue(first_report["ok"])
        self.assertFalse(first_report["apply"])
        self.assertRegex(first_report["planSha256"], r"^sha256:[0-9a-f]{64}$")
        actions = first_report["actions"]
        self.assertEqual(
            [item["kind"] for item in actions],
            [
                "plugin-install",
                "plugin-install",
                "cache-verify",
                "cache-verify",
                "project-plan",
                "project-apply",
                "project-verify",
                "project-plan",
                "project-apply",
                "project-verify",
            ],
        )
        self.assertEqual(
            [item["selector"] for item in actions if item["kind"] == "plugin-install"],
            ["dev-flow@cy-codex-skills", "stateless-tools@cy-codex-skills"],
        )
        self.assertEqual(
            [item["projectId"] for item in actions if item["kind"] == "project-plan"],
            ["game-one", "game-two"],
        )
        self.assertEqual(before, {str(path): path.read_bytes() for path in watched})
        self.assertEqual(
            self.read_commands(),
            [
                ["plugin", "marketplace", "list", "--json"],
                ["plugin", "list", "--available", "--json"],
                ["plugin", "marketplace", "list", "--json"],
                ["plugin", "list", "--available", "--json"],
            ],
        )

    def test_sync_blocks_locked_source_drift_before_project_actions(self) -> None:
        manifest, lock, device = self.bootstrap_profile(("game-one", self.project))
        (self.devflow_source / "skills" / "dev-flow-skill" / "SKILL.md").write_text(
            "---\nname: dev-flow-skill\ndescription: drifted\n---\n",
            encoding="utf-8",
        )

        result = self.run_cli(
            "sync",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--json",
        )

        self.assertEqual(result.returncode, 3, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "blocked")
        self.assertIn("locked_plugin_source_drift", {item["code"] for item in report["blockers"]})
        self.assertFalse(any(item["kind"].startswith("project-") for item in report["actions"]))

    def test_sync_advance_lock_plans_each_git_marketplace_once(self) -> None:
        self.make_git_marketplace()
        manifest, lock, device = self.bootstrap_profile(("game-one", self.project))

        result = self.run_cli(
            "sync",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--advance-lock",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        self.assertTrue(report["advanceLock"])
        actions = report["actions"]
        self.assertEqual(
            [item["marketplace"] for item in actions if item["kind"] == "marketplace-upgrade"],
            ["cy-codex-skills"],
        )
        self.assertEqual(sum(item["kind"] == "plugin-install" for item in actions), 2)
        self.assertEqual(sum(item["kind"] == "lock-promote" for item in actions), 1)
        self.assertEqual(actions[-1]["kind"], "lock-promote")
        self.assertEqual(
            actions[-1]["dependsOn"],
            [
                "cache-verify:dev-flow@cy-codex-skills",
                "cache-verify:stateless-tools@cy-codex-skills",
                "project-verify:game-one:dev-flow@cy-codex-skills",
            ],
        )

    def test_locked_sync_apply_repairs_cache_without_advancing_marketplace(self) -> None:
        manifest, lock, device = self.bootstrap_profile()
        cache_skill = (
            self.codex_home
            / "plugins"
            / "cache"
            / "cy-codex-skills"
            / "dev-flow"
            / "1.2.3"
            / "skills"
            / "dev-flow-skill"
            / "SKILL.md"
        )
        cache_skill.write_text("drifted cache\n", encoding="utf-8")
        lock_before = lock.read_bytes()
        state_dir = self.root / "fleet-state"

        result = self.run_cli(
            "sync",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--state-dir",
            str(state_dir),
            "--apply",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["status"], "applied_and_verified")
        self.assertTrue(report["apply"])
        self.assertFalse(report["advanceLock"])
        self.assertEqual(lock.read_bytes(), lock_before)
        self.assertEqual(
            cache_skill.read_bytes(),
            (self.devflow_source / "skills" / "dev-flow-skill" / "SKILL.md").read_bytes(),
        )
        receipt = Path(report["receiptPath"])
        self.assertTrue(receipt.is_file())
        receipt_data = json.loads(receipt.read_text())
        self.assertEqual(receipt_data["planSha256"], report["planSha256"])
        commands = self.read_commands()
        self.assertNotIn(["plugin", "marketplace", "upgrade", "cy-codex-skills", "--json"], commands)
        self.assertEqual(
            [command[2] for command in commands if command[:2] == ["plugin", "add"]],
            ["dev-flow@cy-codex-skills", "stateless-tools@cy-codex-skills"],
        )
        self.assertTrue(
            all(
                command[:2] in (["plugin", "list"], ["plugin", "marketplace"], ["plugin", "add"])
                for command in commands
            )
        )

        for snapshot_name in ("beforeIdentities", "afterIdentities"):
            snapshot = receipt_data[snapshot_name]
            self.assertEqual(
                set(snapshot),
                {"marketplaces", "plugins", "caches"},
            )
            self.assertEqual(
                set(snapshot["caches"]),
                {
                    "dev-flow@cy-codex-skills",
                    "stateless-tools@cy-codex-skills",
                },
            )
        self.assertEqual(receipt_data["afterIdentities"], receipt_data["identities"])
        self.assertNotEqual(
            receipt_data["beforeIdentities"]["caches"]["dev-flow@cy-codex-skills"],
            receipt_data["afterIdentities"]["caches"]["dev-flow@cy-codex-skills"],
        )
        self.assertEqual(receipt_data["restart"]["scope"], "codex-session")
        self.assertTrue(receipt_data["restart"]["required"])
        self.assertTrue(receipt_data["restart"]["guidance"])

    def test_advance_lock_apply_promotes_only_after_new_cache_identity_verifies(self) -> None:
        self.make_git_marketplace()
        manifest, lock, device = self.bootstrap_profile()
        old_lock_bytes = lock.read_bytes()
        old_lock = json.loads(lock.read_text())
        upgrade = self.root / "upgrade.json"
        upgrade.write_text(
            json.dumps(
                {
                    "revision": "2222222222222222222222222222222222222222",
                    "plugins": {
                        "dev-flow": {"version": "1.3.0", "content": "dev-flow-1.3.0"},
                        "stateless-tools": {"version": "2.1.0", "content": "tools-2.1.0"},
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )

        result = self.run_cli(
            "sync",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--state-dir",
            str(self.root / "fleet-state"),
            "--advance-lock",
            "--apply",
            "--json",
            extra_env={"FAKE_CODEX_UPGRADE_STATE": str(upgrade)},
        )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        promoted = json.loads(lock.read_text())
        self.assertNotEqual(promoted, old_lock)
        self.assertEqual(
            promoted["marketplaces"]["cy-codex-skills"]["revision"],
            "2222222222222222222222222222222222222222",
        )
        self.assertEqual(promoted["plugins"]["dev-flow@cy-codex-skills"]["version"], "1.3.0")
        self.assertEqual(
            promoted["plugins"]["stateless-tools@cy-codex-skills"]["version"],
            "2.1.0",
        )
        commands = self.read_commands()
        self.assertEqual(
            commands.count(["plugin", "marketplace", "upgrade", "cy-codex-skills", "--json"]),
            1,
        )
        self.assertEqual(sum(command[:2] == ["plugin", "add"] for command in commands), 2)
        receipt = json.loads(Path(report["receiptPath"]).read_text())
        self.assertEqual(
            receipt["lockChange"]["beforeSha256"],
            "sha256:" + __import__("hashlib").sha256(old_lock_bytes).hexdigest(),
        )
        self.assertEqual(receipt["lockChange"]["afterSha256"], report["lockSha256"])

    def test_cache_mismatch_fails_before_lock_promotion_and_writes_failure_receipt(self) -> None:
        self.make_git_marketplace()
        manifest, lock, device = self.bootstrap_profile()
        lock_before = lock.read_bytes()
        upgrade = self.root / "upgrade.json"
        upgrade.write_text(
            json.dumps(
                {
                    "revision": "3333333333333333333333333333333333333333",
                    "plugins": {
                        "dev-flow": {"version": "1.3.0"},
                        "stateless-tools": {"version": "2.1.0"},
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )

        result = self.run_cli(
            "sync",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--state-dir",
            str(self.root / "fleet-state"),
            "--advance-lock",
            "--apply",
            "--json",
            extra_env={
                "FAKE_CODEX_UPGRADE_STATE": str(upgrade),
                "FAKE_CODEX_CORRUPT_CACHE_SELECTOR": "dev-flow@cy-codex-skills",
            },
        )

        self.assertEqual(result.returncode, 3, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "identity_mismatch")
        self.assertEqual(lock.read_bytes(), lock_before)
        self.assertTrue(Path(report["receiptPath"]).is_file())
        self.assertFalse(any(item["kind"].startswith("project-") for item in report["results"]))

    def test_apply_rechecks_bound_files_before_each_mutating_stage(self) -> None:
        manifest, lock, device = self.bootstrap_profile()
        lock_before = lock.read_bytes()

        result = self.run_cli(
            "sync",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--state-dir",
            str(self.root / "fleet-state"),
            "--apply",
            "--json",
            extra_env={
                "FAKE_CODEX_MUTATE_AFTER": "plugin add dev-flow@cy-codex-skills --json",
                "FAKE_CODEX_MUTATE_PATH": str(manifest),
                "FAKE_CODEX_MUTATE_CONTENT": '{"changed": true}\n',
            },
        )

        self.assertEqual(result.returncode, 3, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "stale_plan")
        self.assertEqual(lock.read_bytes(), lock_before)
        commands = self.read_commands()
        self.assertIn(["plugin", "add", "dev-flow@cy-codex-skills", "--json"], commands)
        self.assertNotIn(["plugin", "add", "stateless-tools@cy-codex-skills", "--json"], commands)
        self.assertTrue(Path(report["receiptPath"]).is_file())

    def test_apply_rejects_bound_file_symlink_substitution_before_next_write(self) -> None:
        manifest, lock, device = self.bootstrap_profile()
        identical_target = self.root / "identical-manifest.json"
        identical_target.write_bytes(manifest.read_bytes())

        result = self.run_cli(
            "sync",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--state-dir",
            str(self.root / "fleet-state"),
            "--apply",
            "--json",
            extra_env={
                "FAKE_CODEX_MUTATE_AFTER": "plugin add dev-flow@cy-codex-skills --json",
                "FAKE_CODEX_MUTATE_PATH": str(manifest),
                "FAKE_CODEX_REPLACE_WITH_SYMLINK_TARGET": str(identical_target),
            },
        )

        self.assertEqual(result.returncode, 3, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "stale_plan")
        self.assertTrue(manifest.is_symlink())
        commands = self.read_commands()
        self.assertIn(["plugin", "add", "dev-flow@cy-codex-skills", "--json"], commands)
        self.assertNotIn(["plugin", "add", "stateless-tools@cy-codex-skills", "--json"], commands)

    def test_plugin_install_rejects_unrelated_runtime_effect(self) -> None:
        manifest, lock, device = self.bootstrap_profile()

        result = self.run_cli(
            "sync",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--state-dir",
            str(self.root / "fleet-state"),
            "--apply",
            "--json",
            extra_env={
                "FAKE_CODEX_MUTATE_UNRELATED_AFTER": "dev-flow@cy-codex-skills",
                "FAKE_CODEX_UNRELATED_SELECTOR": "stateless-tools@cy-codex-skills",
            },
        )

        self.assertEqual(result.returncode, 3, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "stale_plan")
        self.assertIn("unrelated runtime", report["error"])
        commands = self.read_commands()
        self.assertIn(["plugin", "add", "dev-flow@cy-codex-skills", "--json"], commands)
        self.assertNotIn(["plugin", "add", "stateless-tools@cy-codex-skills", "--json"], commands)

    def test_apply_rechecks_runtime_and_source_before_each_native_write(self) -> None:
        manifest, lock, device = self.bootstrap_profile()
        mutated_source = self.devflow_source / "skills" / "dev-flow-skill" / "SKILL.md"

        result = self.run_cli(
            "sync",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--state-dir",
            str(self.root / "fleet-state"),
            "--apply",
            "--json",
            extra_env={
                "FAKE_CODEX_MUTATE_AFTER": "plugin add dev-flow@cy-codex-skills --json",
                "FAKE_CODEX_MUTATE_PATH": str(mutated_source),
                "FAKE_CODEX_MUTATE_CONTENT": "changed between native stages\n",
            },
        )

        self.assertEqual(result.returncode, 3, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "stale_plan")
        commands = self.read_commands()
        self.assertIn(["plugin", "add", "dev-flow@cy-codex-skills", "--json"], commands)
        self.assertNotIn(["plugin", "add", "stateless-tools@cy-codex-skills", "--json"], commands)

    def test_devflow_adapter_applies_only_routine_actions_from_verified_cache(self) -> None:
        manifest, lock, device = self.bootstrap_profile(("game-one", self.project))

        result = self.run_cli(
            "sync",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--state-dir",
            str(self.root / "fleet-state"),
            "--apply",
            "--json",
        )

        self.assertEqual(result.returncode, 2, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["status"], "applied_with_manual_actions")
        self.assertEqual(
            {item["authorization"] for item in report["manualActions"]},
            {"workflow-config-migration"},
        )
        self.assertEqual((self.project / ".fake-devflow-refreshed").read_text(), "refreshed\n")
        adapter_commands = self.read_adapter_commands()
        self.assertEqual([command[0] for command in adapter_commands], ["plan", "apply", "verify"])
        apply_command = adapter_commands[1]
        self.assertEqual(apply_command.count("--allow"), 1)
        self.assertIn("project-refresh-apply", apply_command)
        self.assertIn("refresh-managed-skills", apply_command)
        self.assertNotIn("migrate-workflow-config", apply_command)
        cache_root = (
            self.codex_home
            / "plugins"
            / "cache"
            / "cy-codex-skills"
            / "dev-flow"
            / "1.2.3"
        ).resolve()
        self.assertEqual(
            Path(apply_command[apply_command.index("--plugin-root") + 1]),
            cache_root,
        )
        receipt = json.loads(Path(report["receiptPath"]).read_text())
        self.assertEqual(len(receipt["projectResults"]), 1)
        self.assertTrue(Path(receipt["projectResults"][0]["adapterReceipt"]).is_file())
        self.assertEqual(
            receipt["changedManagedFiles"],
            [str((self.project / ".fake-devflow-refreshed").absolute())],
        )
        self.assertEqual(report["changedManagedFiles"], receipt["changedManagedFiles"])

    def test_unadopted_or_unverified_project_never_invokes_adapter(self) -> None:
        manifest, lock, device = self.bootstrap_profile(("game-one", self.project))
        marker = self.project / ".codex-fleet" / "project.json"
        marker_data = json.loads(marker.read_text())
        marker_data["projectId"] = "different-project"
        marker.write_text(json.dumps(marker_data, sort_keys=True) + "\n", encoding="utf-8")

        unadopted = self.run_cli(
            "sync",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--state-dir",
            str(self.root / "fleet-state"),
            "--apply",
            "--json",
        )
        self.assertEqual(unadopted.returncode, 3, unadopted.stderr or unadopted.stdout)
        self.assertEqual(self.read_adapter_commands(), [])

        marker.write_text(
            json.dumps(
                {
                    "schemaVersion": "1.0",
                    "profile": "default",
                    "projectId": "game-one",
                    "adopted": True,
                    "managedPlugins": ["dev-flow@cy-codex-skills"],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        if self.command_log.exists():
            self.command_log.unlink()
        corrupt = self.run_cli(
            "sync",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--state-dir",
            str(self.root / "fleet-state-two"),
            "--apply",
            "--json",
            extra_env={"FAKE_CODEX_CORRUPT_CACHE_SELECTOR": "dev-flow@cy-codex-skills"},
        )
        self.assertEqual(corrupt.returncode, 3, corrupt.stderr or corrupt.stdout)
        self.assertEqual(json.loads(corrupt.stdout)["status"], "identity_mismatch")
        self.assertEqual(self.read_adapter_commands(), [])

    def test_stateless_plugin_sync_never_requires_a_project_adapter(self) -> None:
        plain_project = self.root / "projects" / "plain"
        plain_project.mkdir(parents=True)
        manifest, lock, device = self.bootstrap_profile(("plain", plain_project))

        result = self.run_cli(
            "sync",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--state-dir",
            str(self.root / "fleet-state"),
            "--apply",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "applied_and_verified")
        self.assertEqual(self.read_adapter_commands(), [])
        marker = json.loads((plain_project / ".codex-fleet" / "project.json").read_text())
        self.assertEqual(marker["managedPlugins"], [])

    def test_verify_freshly_checks_global_and_project_receipt_state(self) -> None:
        manifest, lock, device = self.bootstrap_profile(("game-one", self.project))
        applied = self.run_cli(
            "sync",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--state-dir",
            str(self.root / "fleet-state"),
            "--apply",
            "--json",
        )
        self.assertEqual(applied.returncode, 2, applied.stderr or applied.stdout)
        receipt = Path(json.loads(applied.stdout)["receiptPath"])
        self.command_log.unlink()
        self.adapter_log.unlink()

        verified = self.run_cli("verify", "--receipt", str(receipt), "--json")

        self.assertEqual(verified.returncode, 2, verified.stderr or verified.stdout)
        report = json.loads(verified.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["status"], "verified_with_manual_actions")
        self.assertEqual([command[0] for command in self.read_adapter_commands()], ["verify"])
        self.assertEqual(
            self.read_commands(),
            [
                ["plugin", "marketplace", "list", "--json"],
                ["plugin", "list", "--available", "--json"],
            ],
        )

        cache = (
            self.codex_home
            / "plugins"
            / "cache"
            / "cy-codex-skills"
            / "dev-flow"
            / "1.2.3"
        )
        (cache / "post-receipt-drift.txt").write_text("drift\n", encoding="utf-8")
        self.command_log.unlink()
        self.adapter_log.unlink()
        drifted = self.run_cli("verify", "--receipt", str(receipt), "--json")
        self.assertEqual(drifted.returncode, 3, drifted.stderr or drifted.stdout)
        self.assertEqual(json.loads(drifted.stdout)["status"], "verification_failed")
        self.assertEqual(self.read_adapter_commands(), [])

    def test_failed_project_verification_keeps_receipt_bound_rollback(self) -> None:
        manifest, lock, device = self.bootstrap_profile(("game-one", self.project))
        applied = self.run_cli(
            "sync",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--state-dir",
            str(self.root / "fleet-state"),
            "--apply",
            "--json",
            extra_env={"FAKE_ADAPTER_CORRUPT_AFTER_APPLY": "1"},
        )

        self.assertEqual(applied.returncode, 3, applied.stderr or applied.stdout)
        report = json.loads(applied.stdout)
        self.assertEqual(report["status"], "adapter_verification_failed")
        receipt_path = Path(report["receiptPath"])
        receipt = json.loads(receipt_path.read_text())
        self.assertFalse(receipt["ok"])
        self.assertEqual(len(receipt["projectResults"]), 1)
        self.assertTrue(receipt["projectResults"][0]["adapterReceipt"])
        self.assertTrue((self.project / ".fake-devflow-refreshed").is_file())

        preview = self.run_cli("rollback", "--receipt", str(receipt_path), "--json")
        self.assertEqual(preview.returncode, 2, preview.stderr or preview.stdout)
        self.assertEqual(json.loads(preview.stdout)["status"], "rollback_preview")

        rolled_back = self.run_cli(
            "rollback",
            "--receipt",
            str(receipt_path),
            "--apply",
            "--json",
        )
        self.assertEqual(rolled_back.returncode, 2, rolled_back.stderr or rolled_back.stdout)
        self.assertEqual(json.loads(rolled_back.stdout)["status"], "rollback_incomplete")
        self.assertFalse((self.project / ".fake-devflow-refreshed").exists())

    def test_verify_reports_missing_bound_file_as_structured_failure(self) -> None:
        manifest, lock, device = self.bootstrap_profile()
        applied = self.run_cli(
            "sync",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--state-dir",
            str(self.root / "fleet-state"),
            "--apply",
            "--json",
        )
        self.assertEqual(applied.returncode, 0, applied.stderr or applied.stdout)
        receipt = Path(json.loads(applied.stdout)["receiptPath"])
        manifest.unlink()

        verified = self.run_cli("verify", "--receipt", str(receipt), "--json")

        self.assertEqual(verified.returncode, 3, verified.stderr or verified.stdout)
        report = json.loads(verified.stdout)
        self.assertEqual(report["status"], "verification_failed")
        self.assertIn("manifest", report["error"])

    def test_verify_reports_lock_disappearance_during_runtime_read_as_json(self) -> None:
        manifest, lock, device = self.bootstrap_profile()
        applied = self.run_cli(
            "sync",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--state-dir",
            str(self.root / "fleet-state"),
            "--apply",
            "--json",
        )
        self.assertEqual(applied.returncode, 0, applied.stderr or applied.stdout)
        receipt = Path(json.loads(applied.stdout)["receiptPath"])

        verified = self.run_cli(
            "verify",
            "--receipt",
            str(receipt),
            "--json",
            extra_env={"FAKE_CODEX_REMOVE_ON_PLUGIN_LIST": str(lock)},
        )

        self.assertEqual(verified.returncode, 3, verified.stderr or verified.stdout)
        report = json.loads(verified.stdout)
        self.assertEqual(report["status"], "verification_failed")
        self.assertIn("lock", report["error"])

    def test_verify_rejects_digest_valid_but_structurally_invalid_receipt(self) -> None:
        manifest, lock, device = self.bootstrap_profile()
        applied = self.run_cli(
            "sync",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--state-dir",
            str(self.root / "fleet-state"),
            "--apply",
            "--json",
        )
        self.assertEqual(applied.returncode, 0, applied.stderr or applied.stdout)
        receipt = Path(json.loads(applied.stdout)["receiptPath"])
        payload = json.loads(receipt.read_text())
        payload.pop("plan")
        payload.pop("receiptSha256")
        canonical = (
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        ).encode("utf-8")
        payload["receiptSha256"] = "sha256:" + hashlib.sha256(canonical).hexdigest()
        receipt.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        verified = self.run_cli("verify", "--receipt", str(receipt), "--json")

        self.assertEqual(verified.returncode, 3, verified.stderr or verified.stdout)
        self.assertEqual(json.loads(verified.stdout)["status"], "invalid_receipt")

    def test_rollback_previews_without_writes_then_rolls_projects_back_in_reverse(self) -> None:
        second_project = self.make_second_project()
        manifest, lock, device = self.bootstrap_profile(
            ("game-one", self.project),
            ("game-two", second_project),
        )
        applied = self.run_cli(
            "sync",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--state-dir",
            str(self.root / "fleet-state"),
            "--apply",
            "--json",
        )
        self.assertEqual(applied.returncode, 2, applied.stderr or applied.stdout)
        receipt = Path(json.loads(applied.stdout)["receiptPath"])
        self.adapter_log.unlink()

        preview = self.run_cli("rollback", "--receipt", str(receipt), "--json")

        self.assertEqual(preview.returncode, 2, preview.stderr or preview.stdout)
        preview_report = json.loads(preview.stdout)
        self.assertEqual(preview_report["status"], "rollback_preview")
        self.assertFalse(preview_report["apply"])
        self.assertTrue((self.project / ".fake-devflow-refreshed").is_file())
        self.assertTrue((second_project / ".fake-devflow-refreshed").is_file())
        self.assertEqual(self.read_adapter_commands(), [])
        self.assertEqual(
            [item["projectId"] for item in preview_report["actions"] if item["kind"] == "project-rollback"],
            ["game-two", "game-one"],
        )

        rolled_back = self.run_cli(
            "rollback",
            "--receipt",
            str(receipt),
            "--apply",
            "--json",
        )
        self.assertEqual(rolled_back.returncode, 2, rolled_back.stderr or rolled_back.stdout)
        rollback_report = json.loads(rolled_back.stdout)
        self.assertEqual(rollback_report["status"], "rollback_incomplete")
        self.assertFalse((self.project / ".fake-devflow-refreshed").exists())
        self.assertFalse((second_project / ".fake-devflow-refreshed").exists())
        commands = self.read_adapter_commands()
        self.assertEqual([command[0] for command in commands], ["rollback", "rollback"])
        repos = [command[command.index("--repo") + 1] for command in commands]
        self.assertEqual(repos, [str(second_project.resolve()), str(self.project.resolve())])
        self.assertTrue(Path(rollback_report["rollbackReceiptPath"]).is_file())
        self.assertTrue(rollback_report["manualActions"])

    def test_rollback_preflights_lock_postimage_before_any_project_write(self) -> None:
        self.make_git_marketplace()
        manifest, lock, device = self.bootstrap_profile(("game-one", self.project))
        upgrade = self.root / "upgrade.json"
        upgrade.write_text(
            json.dumps(
                {
                    "revision": "4444444444444444444444444444444444444444",
                    "plugins": {
                        "dev-flow": {"version": "1.3.0"},
                        "stateless-tools": {"version": "2.1.0"},
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        applied = self.run_cli(
            "sync",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--state-dir",
            str(self.root / "fleet-state"),
            "--advance-lock",
            "--apply",
            "--json",
            extra_env={"FAKE_CODEX_UPGRADE_STATE": str(upgrade)},
        )
        self.assertEqual(applied.returncode, 2, applied.stderr or applied.stdout)
        receipt = Path(json.loads(applied.stdout)["receiptPath"])
        lock.write_text('{"postReceiptEdit": true}\n', encoding="utf-8")
        self.adapter_log.unlink()

        rollback = self.run_cli(
            "rollback",
            "--receipt",
            str(receipt),
            "--apply",
            "--json",
        )

        self.assertEqual(rollback.returncode, 3, rollback.stderr or rollback.stdout)
        report = json.loads(rollback.stdout)
        self.assertEqual(report["status"], "rollback_blocked")
        self.assertEqual(lock.read_text(), '{"postReceiptEdit": true}\n')
        self.assertTrue((self.project / ".fake-devflow-refreshed").is_file())
        self.assertEqual(self.read_adapter_commands(), [])

    def test_rollback_rechecks_verified_cache_before_adapter_execution(self) -> None:
        manifest, lock, device = self.bootstrap_profile(("game-one", self.project))
        applied = self.run_cli(
            "sync",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--state-dir",
            str(self.root / "fleet-state"),
            "--apply",
            "--json",
        )
        self.assertEqual(applied.returncode, 2, applied.stderr or applied.stdout)
        receipt = Path(json.loads(applied.stdout)["receiptPath"])
        cache = (
            self.codex_home
            / "plugins"
            / "cache"
            / "cy-codex-skills"
            / "dev-flow"
            / "1.2.3"
        )
        (cache / "rollback-code-drift.txt").write_text("drift\n", encoding="utf-8")
        self.adapter_log.unlink()

        rollback = self.run_cli(
            "rollback",
            "--receipt",
            str(receipt),
            "--apply",
            "--json",
        )

        self.assertEqual(rollback.returncode, 3, rollback.stderr or rollback.stdout)
        self.assertEqual(json.loads(rollback.stdout)["status"], "rollback_blocked")
        self.assertEqual(self.read_adapter_commands(), [])
        self.assertTrue((self.project / ".fake-devflow-refreshed").is_file())

    def test_partial_rollback_writes_receipt_and_blocks_unsafe_retry(self) -> None:
        second_project = self.make_second_project()
        manifest, lock, device = self.bootstrap_profile(
            ("game-one", self.project),
            ("game-two", second_project),
        )
        applied = self.run_cli(
            "sync",
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(manifest),
            "--lock",
            str(lock),
            "--device",
            str(device),
            "--state-dir",
            str(self.root / "fleet-state"),
            "--apply",
            "--json",
        )
        self.assertEqual(applied.returncode, 2, applied.stderr or applied.stdout)
        receipt = Path(json.loads(applied.stdout)["receiptPath"])
        self.adapter_log.unlink()

        partial = self.run_cli(
            "rollback",
            "--receipt",
            str(receipt),
            "--apply",
            "--json",
            extra_env={"FAKE_ADAPTER_FAIL_ROLLBACK_REPO": str(self.project)},
        )

        self.assertEqual(partial.returncode, 3, partial.stderr or partial.stdout)
        report = json.loads(partial.stdout)
        self.assertEqual(report["status"], "rollback_failed")
        rollback_receipt_path = Path(report["rollbackReceiptPath"])
        rollback_receipt = json.loads(rollback_receipt_path.read_text())
        self.assertEqual(rollback_receipt["status"], "rollback_failed")
        self.assertFalse(rollback_receipt["retryAllowed"])
        self.assertEqual(
            rollback_receipt["completedActionIds"],
            ["project-rollback:game-two:dev-flow@cy-codex-skills"],
        )
        self.assertEqual(
            [item["id"] for item in rollback_receipt["pendingActions"]],
            ["project-rollback:game-one:dev-flow@cy-codex-skills"],
        )
        self.assertFalse((second_project / ".fake-devflow-refreshed").exists())
        self.assertTrue((self.project / ".fake-devflow-refreshed").exists())
        attempted_commands = list(self.read_adapter_commands())

        retry = self.run_cli(
            "rollback",
            "--receipt",
            str(receipt),
            "--apply",
            "--json",
        )

        self.assertEqual(retry.returncode, 3, retry.stderr or retry.stdout)
        retry_report = json.loads(retry.stdout)
        self.assertEqual(retry_report["status"], "rollback_blocked")
        self.assertEqual(retry_report["rollbackReceiptPath"], str(rollback_receipt_path))
        self.assertEqual(self.read_adapter_commands(), attempted_commands)
        self.assertTrue((self.project / ".fake-devflow-refreshed").exists())

    def test_project_lock_contention_starts_no_adapter_mutation(self) -> None:
        manifest, lock, device = self.bootstrap_profile(("game-one", self.project))
        state_dir = self.root / "fleet-state"
        lock_root = state_dir / "locks"
        lock_root.mkdir(parents=True)
        key = hashlib.sha256(b"default\0game-one").hexdigest()
        project_lock_path = lock_root / f"{key}.lock"
        handle = project_lock_path.open("a+")
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            result = self.run_cli(
                "sync",
                "--codex-home",
                str(self.codex_home),
                "--manifest",
                str(manifest),
                "--lock",
                str(lock),
                "--device",
                str(device),
                "--state-dir",
                str(state_dir),
                "--apply",
                "--json",
            )
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

        self.assertEqual(result.returncode, 3, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "project_locked")
        self.assertEqual([command[0] for command in self.read_adapter_commands()], ["plan"])
        self.assertFalse((self.project / ".fake-devflow-refreshed").exists())

    def test_repository_wrapper_and_distribution_entrypoint_expose_cli_help(self) -> None:
        wrapper = REPO_ROOT / "dev" / "scripts" / "codex_fleet.py"
        metadata = tomllib.loads((TOOL_ROOT / "pyproject.toml").read_text())
        self.assertEqual(metadata["build-system"]["requires"], ["setuptools>=61"])
        self.assertEqual(metadata["project"]["name"], "codex-fleet")
        self.assertEqual(metadata["project"]["requires-python"], ">=3.11")
        self.assertEqual(metadata["project"]["scripts"]["codex-fleet"], "codex_fleet.cli:main")
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        wrapped = subprocess.run(
            [sys.executable, str(wrapper), "--help"],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        module_env = dict(env)
        module_env["PYTHONPATH"] = str(SOURCE_ROOT)
        module = subprocess.run(
            [sys.executable, "-m", "codex_fleet", "--help"],
            cwd=REPO_ROOT,
            env=module_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(wrapped.returncode, 0, wrapped.stderr)
        self.assertEqual(module.returncode, 0, module.stderr)
        for output in (wrapped.stdout, module.stdout):
            self.assertIn("inventory", output)
            self.assertIn("bootstrap", output)
            self.assertIn("sync", output)
            self.assertIn("verify", output)
            self.assertIn("rollback", output)

    def test_operator_docs_examples_and_schemas_cover_safe_workflows(self) -> None:
        readme = (TOOL_ROOT / "README.md").read_text(encoding="utf-8")
        for required in (
            "codex-fleet inventory",
            "codex-fleet bootstrap",
            "codex-fleet sync --apply",
            "--advance-lock",
            "codex-fleet verify",
            "codex-fleet rollback",
            "Exit codes",
            "new Codex session",
            "workflow-config-migration",
            "non-reversible",
            "Automatic retry",
            "additional device",
        ):
            self.assertIn(required, readme)

        examples = TOOL_ROOT / "examples"
        manifest = json.loads((examples / "codex-fleet.json").read_text())
        lock = json.loads((examples / "codex-fleet.lock.json").read_text())
        device = json.loads((examples / "default.device.json").read_text())
        self.assertEqual(manifest["schemaVersion"], "1.0")
        self.assertNotIn("/Users/", json.dumps({"manifest": manifest, "lock": lock}))
        self.assertIn("/absolute/path", json.dumps(device))
        for name in ("manifest", "lock", "device", "project-marker", "receipt"):
            schema = json.loads((TOOL_ROOT / "schemas" / f"{name}-v1.schema.json").read_text())
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertEqual(schema["type"], "object")


if __name__ == "__main__":
    unittest.main()
