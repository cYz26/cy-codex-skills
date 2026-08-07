import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import os
from pathlib import Path
from unittest import mock


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import workflow_project_refresh as refresh_module
from workflow_project_refresh import plan_project_refresh

LEGACY_PROFILE_KEY = "methodology" + "_profile"
LEGACY_PROFILE_CAMEL_KEY = "methodology" + "Profile"


class ProjectRefreshTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config_plugin = self.make_contract_plugin()

    def make_repo(self, *, git: bool = False) -> Path:
        repo = Path(tempfile.mkdtemp(prefix="devflow-project-refresh-"))
        if git:
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "DevFlow Tests"], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "config", "user.email", "devflow-tests@example.invalid"],
                check=True,
            )
        return repo

    def snapshot(self, repo: Path) -> dict[str, str]:
        snapshot: dict[str, str] = {}
        for path in sorted(repo.rglob("*")):
            relative = path.relative_to(repo).as_posix()
            if path.is_symlink():
                snapshot[relative] = f"symlink:{path.readlink()}"
            elif path.is_file():
                try:
                    snapshot[relative] = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
                except OSError:
                    metadata = path.stat()
                    snapshot[relative] = f"unreadable:{metadata.st_mode:o}:{metadata.st_size}"
            elif path.is_dir():
                snapshot[relative] = "directory"
        return snapshot

    def write_json(self, path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n")

    def make_contract_plugin(
        self,
        *,
        head: int = 1,
        minimum: int = 0,
        steps: list[dict[str, object]] | None = None,
    ) -> Path:
        plugin = Path(tempfile.mkdtemp(prefix="devflow-project-refresh-plugin-"))
        self.write_json(plugin / ".codex-plugin" / "plugin.json", {"name": "dev-flow", "version": "test"})
        self.write_json(plugin / "assets" / "project-refresh" / f"config-v{head}.json", {
            "workflow": {"mode": "full-openspec"}
        })
        self.write_json(
            plugin / ".codex-plugin" / "project-migration.json",
            {
                "schemaVersion": "2.0",
                "engineSchemaVersion": "2.0",
                "plugin": "dev-flow",
                "projectSchema": {"head": head, "minimumSupported": minimum},
                "configTargets": {str(head): f"assets/project-refresh/config-v{head}.json"},
                "migrationSteps": steps if steps is not None else [
                    {
                        "id": "legacy-selection-v0-to-v1",
                        "from": 0,
                        "to": 1,
                        "authorization": "workflow-config-migration",
                        "configTarget": 1,
                    }
                ],
                "refreshContract": {"revision": 1, "impact": "changed", "trackedInputs": []},
                "projectLocalSkills": [],
                "managedFiles": [],
            },
        )
        return plugin

    def make_future_contract_plugin(self) -> Path:
        future_step = {
            "id": "fixture-current-v1-to-v2",
            "from": 1,
            "to": 2,
            "authorization": "workflow-config-migration",
            "configTarget": 2,
        }
        refresh_module.MIGRATION_STEP_REGISTRY[future_step["id"]] = {
            **future_step,
            "planner": "merge-config-target",
            "verifier": "configuration-schema-v2",
        }
        self.addCleanup(refresh_module.MIGRATION_STEP_REGISTRY.pop, future_step["id"], None)
        plugin = self.make_contract_plugin(
            head=2,
            minimum=0,
            steps=[
                {
                    "id": "legacy-selection-v0-to-v1",
                    "from": 0,
                    "to": 1,
                    "authorization": "workflow-config-migration",
                    "configTarget": 1,
                },
                future_step,
            ],
        )
        self.write_json(
            plugin / "assets" / "project-refresh" / "config-v1.json",
            {"workflow": {"mode": "full-openspec"}},
        )
        self.write_json(
            plugin / "assets" / "project-refresh" / "config-v2.json",
            {"workflow": {"mode": "full-openspec"}, "projectContract": 2},
        )
        manifest_path = plugin / ".codex-plugin" / "project-migration.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["configTargets"] = {
            "1": "assets/project-refresh/config-v1.json",
            "2": "assets/project-refresh/config-v2.json",
        }
        self.write_json(manifest_path, manifest)
        return plugin

    def enable_agents_guidance(self, plugin: Path) -> None:
        template = plugin / "assets" / "templates" / "AGENTS.md.template"
        template.parent.mkdir(parents=True, exist_ok=True)
        template.write_bytes((PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template").read_bytes())
        manifest_path = plugin / ".codex-plugin" / "project-migration.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["agentsGuidance"] = {
            "activePath": "AGENTS.md",
            "candidatePath": "AGENTS.md.generated",
            "template": "assets/templates/AGENTS.md.template",
        }
        manifest["refreshContract"]["trackedInputs"] = ["assets/templates/AGENTS.md.template"]
        self.write_json(manifest_path, manifest)

    def enable_managed_skill(self, plugin: Path, skill: str) -> None:
        skill_file = plugin / "skills" / skill / "SKILL.md"
        skill_file.parent.mkdir(parents=True, exist_ok=True)
        skill_file.write_text(f"---\nname: {skill}\ndescription: fixture\n---\n")
        manifest_path = plugin / ".codex-plugin" / "project-migration.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["projectLocalSkills"] = [skill]
        self.write_json(manifest_path, manifest)

    def commit_all(self, repo: Path, message: str = "fixture") -> None:
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", message], check=True)

    def test_plan_for_non_adopted_directory_is_read_only_and_not_applicable(self):
        repo = self.make_repo()
        (repo / "README.md").write_text("# Unrelated project\n")
        before = self.snapshot(repo)

        plan = plan_project_refresh(repo, self.config_plugin)

        self.assertTrue(plan["ok"], plan)
        self.assertEqual(plan["status"], "not_applicable")
        self.assertEqual(plan["writeSet"], [])
        self.assertEqual(plan["actions"], [])
        self.assertEqual(self.snapshot(repo), before)
        self.assertFalse((repo / ".planning").exists())

    def test_adoption_marker_below_a_symlinked_parent_is_not_trusted(self):
        repo = self.make_repo()
        external = self.make_repo()
        state = external / "devflow" / "STATE.md"
        state.parent.mkdir(parents=True)
        state.write_text("---\nworkflow_version: 0.3.0\n---\n# External state\n")
        (repo / ".planning").symlink_to(external, target_is_directory=True)
        before = self.snapshot(repo)

        plan = plan_project_refresh(repo, self.config_plugin)

        self.assertTrue(plan["ok"], plan)
        self.assertEqual(plan["status"], "not_applicable")
        self.assertEqual(plan["writeSet"], [])
        self.assertEqual(self.snapshot(repo), before)

    def test_current_configuration_reports_schema_one_without_a_config_write(self):
        repo = self.make_repo()
        self.write_json(
            repo / ".dev-flow.json",
            {"workflow": {"mode": "full-openspec", "customFlag": True}, "customRoot": [1, "two"]},
        )
        before = self.snapshot(repo)

        plan = plan_project_refresh(repo, self.config_plugin)

        self.assertTrue(plan["ok"], plan)
        self.assertEqual(plan["config"]["status"], "current")
        self.assertEqual(plan["projectSchema"]["observed"], 1)
        self.assertEqual(plan["status"], "migration_pending")
        self.assertEqual(plan["migrationState"]["status"], "missing")
        self.assertTrue(plan["stateSyncRequired"])
        self.assertNotIn(".dev-flow.json", plan["writeSet"])
        self.assertEqual(self.snapshot(repo), before)

    def test_future_contract_head_drives_current_detection_and_create_target_bytes(self):
        plugin = self.make_future_contract_plugin()
        target = plugin / "assets" / "project-refresh" / "config-v2.json"
        current_repo = self.make_repo()
        (current_repo / ".dev-flow.json").write_bytes(target.read_bytes())

        current = plan_project_refresh(current_repo, plugin)

        self.assertTrue(current["ok"], current)
        self.assertEqual(current["config"]["status"], "current")
        self.assertEqual(current["projectSchema"], {"observed": 2, "target": 2})

        missing_repo = self.make_repo()
        marker = missing_repo / ".planning" / "devflow" / "STATE.md"
        marker.parent.mkdir(parents=True)
        marker.write_text("---\nworkflow_version: 0.3.0\n---\n# State\n")
        plan = plan_project_refresh(missing_repo, plugin)

        self.assertTrue(plan["ok"], plan)
        self.assertEqual(plan["projectSchema"], {"observed": 0, "target": 2})
        self.assertEqual(
            plan["actions"][0]["afterFingerprint"]["sha256"],
            hashlib.sha256(target.read_bytes()).hexdigest(),
        )
        applied = refresh_module.apply_project_refresh(
            missing_repo,
            plugin,
            expected_plan=plan["planSha256"],
            authorizations={"workflow-config-migration"},
        )
        self.assertTrue(applied["ok"], applied)
        self.assertEqual((missing_repo / ".dev-flow.json").read_bytes(), target.read_bytes())
        after = plan_project_refresh(missing_repo, plugin)
        self.assertEqual(after["status"], "current")
        self.assertEqual(after["projectSchema"], {"observed": 2, "target": 2})

        v1_repo = self.make_repo(git=True)
        self.write_json(
            v1_repo / ".dev-flow.json",
            {"workflow": {"mode": "full-openspec", "customFlag": True}},
        )
        self.commit_all(v1_repo)
        v1_plan = plan_project_refresh(v1_repo, plugin)
        self.assertEqual(v1_plan["migrationPath"], ["fixture-current-v1-to-v2"])
        self.assertEqual(
            v1_plan["actions"][0]["source"]["steps"],
            ["fixture-current-v1-to-v2"],
        )
        v1_applied = refresh_module.apply_project_refresh(
            v1_repo,
            plugin,
            expected_plan=v1_plan["planSha256"],
            authorizations={"workflow-config-migration"},
        )
        self.assertTrue(v1_applied["ok"], v1_applied)
        v1_payload = json.loads((v1_repo / ".dev-flow.json").read_text())
        self.assertTrue(v1_payload["workflow"]["customFlag"])
        self.assertEqual(v1_payload["projectContract"], 2)
        self.assertEqual(plan_project_refresh(v1_repo, plugin)["status"], "current")

        legacy_repo = self.make_repo(git=True)
        self.write_json(
            legacy_repo / ".dev-flow.json",
            {LEGACY_PROFILE_KEY: "legacy", "customRoot": {"preserved": True}},
        )
        self.commit_all(legacy_repo)
        legacy_plan = plan_project_refresh(legacy_repo, plugin)
        self.assertEqual(
            legacy_plan["migrationPath"],
            ["legacy-selection-v0-to-v1", "fixture-current-v1-to-v2"],
        )
        self.assertEqual(
            legacy_plan["actions"][0]["source"]["steps"],
            legacy_plan["migrationPath"],
        )
        legacy_applied = refresh_module.apply_project_refresh(
            legacy_repo,
            plugin,
            expected_plan=legacy_plan["planSha256"],
            authorizations={"workflow-config-migration"},
        )
        self.assertTrue(legacy_applied["ok"], legacy_applied)
        legacy_payload = json.loads((legacy_repo / ".dev-flow.json").read_text())
        self.assertNotIn(LEGACY_PROFILE_KEY, legacy_payload)
        self.assertEqual(legacy_payload["customRoot"], {"preserved": True})
        self.assertEqual(legacy_payload["projectContract"], 2)
        legacy_receipt = json.loads(Path(legacy_applied["receiptPath"]).read_text())
        self.assertEqual(legacy_receipt["migrationPath"], legacy_plan["migrationPath"])
        self.assertEqual(plan_project_refresh(legacy_repo, plugin)["status"], "current")

        future_repo = self.make_repo(git=True)
        self.write_json(
            future_repo / ".dev-flow.json",
            {
                "projectContract": 3,
                "workflow": {"mode": "full-openspec"},
                "futureSetting": True,
            },
        )
        self.commit_all(future_repo)
        future_plan = plan_project_refresh(future_repo, plugin)
        self.assertFalse(future_plan["ok"], future_plan)
        self.assertEqual(future_plan["status"], "blocked")
        self.assertEqual(future_plan["config"]["status"], "baseline_unsupported")
        self.assertNotIn(".dev-flow.json", future_plan["writeSet"])

    def test_trusted_configuration_and_state_schema_disagreement_is_ambiguous(self):
        repo = self.make_repo(git=True)
        self.write_json(repo / ".dev-flow.json", {"workflow": {"mode": "full-openspec"}})
        self.commit_all(repo)
        initial = plan_project_refresh(repo, self.config_plugin)
        applied = refresh_module.apply_project_refresh(
            repo,
            self.config_plugin,
            expected_plan=initial["planSha256"],
            authorizations={"project-refresh-apply"},
        )
        self.assertTrue(applied["ok"], applied)

        self.write_json(repo / ".dev-flow.json", {LEGACY_PROFILE_KEY: "legacy"})
        self.commit_all(repo, "replace config with conflicting trusted evidence")
        conflict = plan_project_refresh(repo, self.config_plugin)

        self.assertFalse(conflict["ok"], conflict)
        self.assertEqual(conflict["status"], "baseline_ambiguous")
        self.assertEqual(conflict["projectSchema"], {"observed": 0, "target": 1})
        self.assertEqual(conflict["migrationState"]["recordedProjectSchemaVersion"], 1)
        self.assertEqual(conflict["actions"], [])
        self.assertEqual(conflict["writeSet"], [])
        self.assertFalse(conflict["stateSyncRequired"])

    def test_current_configuration_requires_and_can_record_current_refresh_evidence(self):
        repo = self.make_repo()
        self.write_json(repo / ".dev-flow.json", {"workflow": {"mode": "full-openspec"}})
        plan = plan_project_refresh(repo, self.config_plugin)

        unauthorized = refresh_module.apply_project_refresh(
            repo,
            self.config_plugin,
            expected_plan=plan["planSha256"],
            authorizations=set(),
        )
        self.assertFalse(unauthorized["ok"], unauthorized)
        self.assertEqual(unauthorized["status"], "authorization_required")

        applied = refresh_module.apply_project_refresh(
            repo,
            self.config_plugin,
            expected_plan=plan["planSha256"],
            authorizations={"project-refresh-apply"},
        )
        current = plan_project_refresh(repo, self.config_plugin)

        self.assertTrue(applied["ok"], applied)
        self.assertEqual(applied["status"], "applied_and_verified")
        self.assertEqual(applied["changedPaths"], [])
        self.assertEqual(current["status"], "current")
        self.assertEqual(current["migrationState"]["status"], "current")
        self.assertFalse(current["stateSyncRequired"])

        rolled_back = refresh_module.rollback_project_refresh(
            repo,
            self.config_plugin,
            applied["receiptPath"],
            apply=True,
        )
        self.assertTrue(rolled_back["ok"], rolled_back)
        self.assertFalse(
            (repo / ".planning" / "devflow" / "plugin-project-migration" / "state.json").exists()
        )

    def test_clean_tracked_legacy_config_has_redacted_authorized_migration_plan(self):
        repo = self.make_repo(git=True)
        self.write_json(
            repo / ".dev-flow.json",
            {
                LEGACY_PROFILE_KEY: "legacy-secret-profile",
                "workflow": {"customFlag": False},
                "customRoot": {"token": "should-never-appear"},
            },
        )
        self.commit_all(repo)
        before = self.snapshot(repo)

        plan = plan_project_refresh(repo, self.config_plugin)
        encoded = json.dumps(plan, sort_keys=True)

        self.assertTrue(plan["ok"], plan)
        self.assertEqual(plan["status"], "migration_pending")
        self.assertEqual(plan["projectSchema"], {"observed": 0, "target": 1})
        self.assertEqual(plan["writeSet"], [".dev-flow.json"])
        self.assertEqual(plan["requiredAuthorizations"], ["workflow-config-migration"])
        self.assertEqual(plan["actions"][0]["id"], "legacy-selection-v0-to-v1")
        self.assertEqual(plan["actions"][0]["path"], ".dev-flow.json")
        expected_after = (
            b'{\n  "customRoot": {\n    "token": "should-never-appear"\n  },\n'
            b'  "workflow": {\n    "customFlag": false,\n    "mode": "full-openspec"\n  }\n}\n'
        )
        self.assertEqual(
            plan["actions"][0]["afterFingerprint"]["sha256"],
            hashlib.sha256(expected_after).hexdigest(),
        )
        self.assertNotIn("legacy-secret-profile", encoded)
        self.assertNotIn("should-never-appear", encoded)
        self.assertEqual(self.snapshot(repo), before)

    def test_adopted_project_without_config_plans_authorized_create_if_absent(self):
        repo = self.make_repo()
        state = repo / ".planning" / "devflow" / "STATE.md"
        state.parent.mkdir(parents=True)
        state.write_text("---\nworkflow_version: 0.3.0\n---\n# State\n")
        before = self.snapshot(repo)

        plan = plan_project_refresh(repo, self.config_plugin)

        self.assertTrue(plan["ok"], plan)
        self.assertEqual(plan["status"], "migration_pending")
        self.assertEqual(plan["projectSchema"], {"observed": 0, "target": 1})
        self.assertEqual(plan["writeSet"], [".dev-flow.json"])
        self.assertEqual(plan["actions"][0]["kind"], "create_file")
        self.assertEqual(plan["actions"][0]["id"], "create-current-workflow-config")
        self.assertEqual(plan["requiredAuthorizations"], ["workflow-config-migration"])
        self.assertEqual(self.snapshot(repo), before)

    def test_conflicting_legacy_aliases_are_redacted_preserved_and_manual_only(self):
        repo = self.make_repo(git=True)
        self.write_json(
            repo / ".dev-flow.json",
            {
                LEGACY_PROFILE_KEY: "secret-a",
                "workflow": {LEGACY_PROFILE_CAMEL_KEY: "secret-b"},
            },
        )
        self.commit_all(repo)
        before = self.snapshot(repo)

        plan = plan_project_refresh(repo, self.config_plugin)
        encoded = json.dumps(plan, sort_keys=True)

        self.assertTrue(plan["ok"], plan)
        self.assertEqual(plan["status"], "manual_review_required")
        self.assertEqual(plan["writeSet"], [])
        self.assertIn(".dev-flow.json", plan["preservedPaths"])
        self.assertIn(f"conflicting_legacy_{LEGACY_PROFILE_KEY}", encoded)
        self.assertNotIn("secret-a", encoded)
        self.assertNotIn("secret-b", encoded)
        self.assertEqual(self.snapshot(repo), before)

    def test_unsafe_legacy_config_shapes_remain_unchanged_and_manual_only(self):
        cases: list[tuple[str, Path]] = []

        untracked = self.make_repo(git=True)
        self.write_json(untracked / ".dev-flow.json", {LEGACY_PROFILE_KEY: "untracked-secret"})
        cases.append(("untracked", untracked))

        dirty = self.make_repo(git=True)
        self.write_json(dirty / ".dev-flow.json", {LEGACY_PROFILE_KEY: "tracked-secret"})
        self.commit_all(dirty)
        (dirty / ".dev-flow.json").write_text(json.dumps({LEGACY_PROFILE_KEY: "dirty-secret"}) + "\n")
        cases.append(("dirty", dirty))

        non_git = self.make_repo()
        self.write_json(non_git / ".dev-flow.json", {LEGACY_PROFILE_KEY: "nongit-secret"})
        cases.append(("non_git", non_git))

        symlinked = self.make_repo()
        state = symlinked / ".planning" / "devflow" / "STATE.md"
        state.parent.mkdir(parents=True)
        state.write_text("---\nworkflow_version: 0.3.0\n---\n# State\n")
        external = Path(tempfile.mkdtemp(prefix="devflow-project-refresh-external-")) / "config.json"
        external.write_text(json.dumps({LEGACY_PROFILE_KEY: "external-secret"}) + "\n")
        (symlinked / ".dev-flow.json").symlink_to(external)
        cases.append(("symlinked", symlinked))

        non_regular = self.make_repo()
        state = non_regular / ".planning" / "devflow" / "STATE.md"
        state.parent.mkdir(parents=True)
        state.write_text("---\nworkflow_version: 0.3.0\n---\n# State\n")
        (non_regular / ".dev-flow.json").mkdir()
        cases.append(("non_regular", non_regular))

        unreadable = self.make_repo()
        self.write_json(unreadable / ".dev-flow.json", {LEGACY_PROFILE_KEY: "unreadable-secret"})
        os.chmod(unreadable / ".dev-flow.json", 0)
        cases.append(("unreadable", unreadable))

        for name, repo in cases:
            with self.subTest(name=name):
                before = self.snapshot(repo)
                plan = plan_project_refresh(repo, self.config_plugin)
                encoded = json.dumps(plan, sort_keys=True)

                self.assertTrue(plan["ok"], plan)
                self.assertEqual(plan["status"], "manual_review_required")
                self.assertEqual(plan["writeSet"], [])
                self.assertIn(".dev-flow.json", plan["preservedPaths"])
                self.assertNotIn("-secret", encoded)
                self.assertEqual(self.snapshot(repo), before)

    def test_plan_exposes_independent_contract_versions_and_unique_migration_path(self):
        repo = self.make_repo(git=True)
        self.write_json(repo / ".dev-flow.json", {LEGACY_PROFILE_KEY: "legacy"})
        self.commit_all(repo)

        plan = plan_project_refresh(repo, self.config_plugin)

        identity = plan["sourceIdentity"]
        self.assertEqual(identity["engineSchemaVersion"], "2.0")
        self.assertEqual(identity["projectSchemaHead"], 1)
        self.assertEqual(identity["minimumSupportedProjectSchema"], 0)
        self.assertEqual(identity["refreshContractRevision"], 1)
        self.assertRegex(identity["refreshContractDigest"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(plan["migrationPath"], ["legacy-selection-v0-to-v1"])

    def test_invalid_migration_graphs_fail_closed_before_any_project_write(self):
        cases = {
            "gap": (
                self.make_contract_plugin(head=2, steps=[{"id": "v0-v1", "from": 0, "to": 1}]),
                "migration_graph_gap",
            ),
            "fork": (
                self.make_contract_plugin(
                    steps=[
                        {"id": "first", "from": 0, "to": 1},
                        {"id": "second", "from": 0, "to": 1},
                    ]
                ),
                "migration_graph_fork",
            ),
            "cycle": (
                self.make_contract_plugin(steps=[{"id": "cycle", "from": 0, "to": 0}]),
                "migration_graph_cycle",
            ),
            "duplicate_id": (
                self.make_contract_plugin(
                    head=2,
                    steps=[
                        {"id": "duplicate", "from": 0, "to": 1},
                        {"id": "duplicate", "from": 1, "to": 2},
                    ],
                ),
                "migration_step_duplicate_or_missing_id",
            ),
            "unknown_predecessor": (
                self.make_contract_plugin(head=2, steps=[{"id": "v1-v2", "from": 1, "to": 2}]),
                "migration_graph_gap",
            ),
        }
        for name, (plugin, expected_error) in cases.items():
            with self.subTest(name=name):
                repo = self.make_repo()
                self.write_json(repo / ".dev-flow.json", {"workflow": {"mode": "full-openspec"}})
                before = self.snapshot(repo)

                plan = plan_project_refresh(repo, plugin)

                self.assertFalse(plan["ok"], plan)
                self.assertEqual(plan["status"], "blocked")
                self.assertIn(expected_error, plan["contractErrors"])
                self.assertEqual(plan["writeSet"], [])
                self.assertEqual(self.snapshot(repo), before)

    def test_unknown_or_mismatched_migration_step_is_rejected_by_the_registry(self):
        cases = {
            "unknown": [{"id": "renamed-v0-v1", "from": 0, "to": 1}],
            "mismatched": [
                {
                    "id": "legacy-selection-v0-to-v1",
                    "from": 0,
                    "to": 1,
                    "authorization": "wrong-authorization",
                    "configTarget": 1,
                }
            ],
        }
        for name, steps in cases.items():
            with self.subTest(name=name):
                plugin = self.make_contract_plugin(steps=steps)
                repo = self.make_repo(git=True)
                self.write_json(repo / ".dev-flow.json", {LEGACY_PROFILE_KEY: "legacy"})
                self.commit_all(repo)
                before = self.snapshot(repo)

                plan = plan_project_refresh(repo, plugin)

                self.assertFalse(plan["ok"], plan)
                self.assertEqual(plan["status"], "blocked")
                self.assertTrue(
                    any("migration_step_registry" in item for item in plan["contractErrors"]),
                    plan,
                )
                self.assertEqual(self.snapshot(repo), before)

    def test_plan_digest_is_deterministic_and_ignores_unrelated_worktree_changes(self):
        repo = self.make_repo(git=True)
        self.write_json(repo / ".dev-flow.json", {LEGACY_PROFILE_KEY: "legacy"})
        (repo / "notes.md").write_text("original\n")
        self.commit_all(repo)

        first = plan_project_refresh(repo, self.config_plugin)
        second = plan_project_refresh(repo, self.config_plugin)
        (repo / "notes.md").write_text("unrelated edit\n")
        third = plan_project_refresh(repo, self.config_plugin)

        self.assertEqual(first, second)
        self.assertEqual(first["planSha256"], third["planSha256"])
        self.assertEqual(first["writeSet"], third["writeSet"])
        self.assertEqual(first["unrelatedWorktree"], [])
        self.assertEqual(third["unrelatedWorktree"], ["notes.md"])

    def test_contract_digest_changes_when_a_declared_source_input_changes(self):
        plugin = self.make_contract_plugin()
        tracked = plugin / "tracked.txt"
        tracked.write_text("first\n")
        manifest_path = plugin / ".codex-plugin" / "project-migration.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["refreshContract"]["trackedInputs"] = ["tracked.txt"]
        self.write_json(manifest_path, manifest)
        repo = self.make_repo()
        self.write_json(repo / ".dev-flow.json", {"workflow": {"mode": "full-openspec"}})

        first = plan_project_refresh(repo, plugin)
        tracked.write_text("second\n")
        second = plan_project_refresh(repo, plugin)

        self.assertNotEqual(
            first["sourceIdentity"]["refreshContractDigest"],
            second["sourceIdentity"]["refreshContractDigest"],
        )
        self.assertNotEqual(first["planSha256"], second["planSha256"])

    def test_apply_rejects_a_stale_managed_config_plan_without_additional_writes(self):
        repo = self.make_repo(git=True)
        self.write_json(repo / ".dev-flow.json", {LEGACY_PROFILE_KEY: "legacy"})
        self.commit_all(repo)
        plan = plan_project_refresh(repo, self.config_plugin)
        (repo / ".dev-flow.json").write_text(
            json.dumps({LEGACY_PROFILE_KEY: "changed-after-plan"}) + "\n"
        )
        before_apply = self.snapshot(repo)

        result = refresh_module.apply_project_refresh(
            repo,
            self.config_plugin,
            expected_plan=plan["planSha256"],
            authorizations={"workflow-config-migration"},
        )

        self.assertFalse(result["ok"], result)
        self.assertEqual(result["status"], "plan_stale")
        self.assertEqual(result["changedPaths"], [])
        self.assertEqual(self.snapshot(repo), before_apply)

    def test_apply_rejects_a_stale_declared_source_contract_without_project_writes(self):
        plugin = self.make_contract_plugin()
        tracked = plugin / "tracked.txt"
        tracked.write_text("first\n")
        manifest_path = plugin / ".codex-plugin" / "project-migration.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["refreshContract"]["trackedInputs"] = ["tracked.txt"]
        self.write_json(manifest_path, manifest)
        repo = self.make_repo()
        self.write_json(repo / ".dev-flow.json", {"workflow": {"mode": "full-openspec"}})
        plan = plan_project_refresh(repo, plugin)
        tracked.write_text("changed-after-plan\n")
        before_apply = self.snapshot(repo)

        result = refresh_module.apply_project_refresh(
            repo,
            plugin,
            expected_plan=plan["planSha256"],
            authorizations=set(),
        )

        self.assertFalse(result["ok"], result)
        self.assertEqual(result["status"], "plan_stale")
        self.assertEqual(result["changedPaths"], [])
        self.assertEqual(self.snapshot(repo), before_apply)

    def test_unrecognized_configuration_shape_is_baseline_ambiguous(self):
        repo = self.make_repo()
        self.write_json(repo / ".dev-flow.json", {"workflow": {"custom": True}})
        before = self.snapshot(repo)

        plan = plan_project_refresh(repo, self.config_plugin)

        self.assertFalse(plan["ok"], plan)
        self.assertEqual(plan["status"], "baseline_ambiguous")
        self.assertEqual(plan["projectSchema"]["observed"], None)
        self.assertEqual(plan["writeSet"], [])
        self.assertEqual(self.snapshot(repo), before)

    def test_authorized_legacy_config_apply_verifies_receipts_and_rolls_back(self):
        repo = self.make_repo(git=True)
        original = {
            LEGACY_PROFILE_KEY: "legacy-secret-profile",
            "workflow": {"customFlag": False},
            "customRoot": {"token": "preserved-secret"},
        }
        self.write_json(repo / ".dev-flow.json", original)
        self.commit_all(repo)
        plan = plan_project_refresh(repo, self.config_plugin)

        result = refresh_module.apply_project_refresh(
            repo,
            self.config_plugin,
            expected_plan=plan["planSha256"],
            authorizations={"workflow-config-migration"},
        )

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["status"], "applied_and_verified")
        self.assertEqual(result["changedPaths"], [".dev-flow.json"])
        migrated = json.loads((repo / ".dev-flow.json").read_text())
        self.assertNotIn(LEGACY_PROFILE_KEY, migrated)
        self.assertEqual(migrated["workflow"], {"customFlag": False, "mode": "full-openspec"})
        self.assertEqual(migrated["customRoot"], {"token": "preserved-secret"})
        receipt = Path(result["receiptPath"])
        self.assertTrue(receipt.is_file())
        verification_receipt = Path(result["verificationReceiptPath"])
        self.assertTrue(verification_receipt.is_file())
        self.assertEqual(
            json.loads(verification_receipt.read_text())["kind"],
            "devflow-project-refresh-verification-receipt",
        )
        receipt_text = receipt.read_text()
        verification_text = verification_receipt.read_text()
        self.assertNotIn("legacy-secret-profile", receipt_text)
        self.assertNotIn("preserved-secret", receipt_text)
        self.assertNotIn("legacy-secret-profile", verification_text)
        self.assertNotIn("preserved-secret", verification_text)
        state_path = repo / ".planning" / "devflow" / "plugin-project-migration" / "state.json"
        state = json.loads(state_path.read_text())
        self.assertEqual(state["schemaVersion"], "2.0")
        self.assertEqual(state["plugins"]["dev-flow"]["projectSchemaVersion"], 1)

        verification = refresh_module.verify_project_refresh(repo, self.config_plugin, receipt)
        self.assertTrue(verification["ok"], verification)
        self.assertEqual(verification["status"], "verified")

        rollback = refresh_module.rollback_project_refresh(repo, self.config_plugin, receipt, apply=True)
        self.assertTrue(rollback["ok"], rollback)
        self.assertEqual(rollback["status"], "rolled_back")
        self.assertEqual(json.loads((repo / ".dev-flow.json").read_text()), original)
        self.assertFalse(state_path.exists())

    def test_apply_without_named_authorization_performs_zero_writes(self):
        repo = self.make_repo(git=True)
        self.write_json(repo / ".dev-flow.json", {LEGACY_PROFILE_KEY: "legacy"})
        self.commit_all(repo)
        plan = plan_project_refresh(repo, self.config_plugin)
        before = self.snapshot(repo)

        result = refresh_module.apply_project_refresh(
            repo,
            self.config_plugin,
            expected_plan=plan["planSha256"],
            authorizations=set(),
        )

        self.assertFalse(result["ok"], result)
        self.assertEqual(result["status"], "authorization_required")
        self.assertEqual(result["missingAuthorizations"], ["workflow-config-migration"])
        self.assertEqual(result["changedPaths"], [])
        self.assertEqual(self.snapshot(repo), before)

    def test_preflight_conflict_performs_zero_writes(self):
        repo = self.make_repo()
        before = self.snapshot(repo)
        actions = [
            {
                "id": identifier,
                "kind": "create_file",
                "path": relative,
                "ownership": "devflow-create-if-absent",
                "beforeFingerprint": refresh_module._fingerprint(repo / relative),
                "afterFingerprint": {"kind": "file", "sha256": "0" * 64},
                "dependencies": [],
                "rollback": {"kind": "remove_if_created", "pruneEmptyParents": []},
                "source": {"kind": "plugin_file", "path": "fixture"},
            }
            for identifier, relative in (
                ("one", ".agents"),
                ("two", ".agents/skills/example"),
            )
        ]

        issues = refresh_module._preflight_actions(repo, actions)

        self.assertEqual(issues, ["path_overlap:one:two"])
        self.assertEqual(self.snapshot(repo), before)

    def test_preflight_rejects_symlink_parent_without_external_writes(self):
        repo = self.make_repo()
        external = self.make_repo()
        (repo / ".agents").symlink_to(external, target_is_directory=True)
        before_repo = self.snapshot(repo)
        before_external = self.snapshot(external)
        action = {
            "id": "symlink-parent",
            "kind": "create_file",
            "path": ".agents/skills/example",
            "ownership": "devflow-create-if-absent",
            "beforeFingerprint": {"kind": "absent", "sha256": hashlib.sha256(b"").hexdigest()},
            "afterFingerprint": {"kind": "file", "sha256": "0" * 64},
            "dependencies": [],
            "rollback": {"kind": "remove_if_created", "pruneEmptyParents": []},
            "source": {"kind": "plugin_file", "path": "fixture"},
        }

        issues = refresh_module._preflight_actions(repo, [action])

        self.assertTrue(any(issue.startswith("invalid_path:symlink-parent:") for issue in issues), issues)
        self.assertEqual(self.snapshot(repo), before_repo)
        self.assertEqual(self.snapshot(external), before_external)

    def test_verified_tree_executor_cleans_temporary_control_plane_on_success(self):
        repo = self.make_repo()
        content = b"---\nname: fixture-skill\n---\n"

        result = refresh_module.apply_verified_skill_tree_transaction(
            repo,
            [
                {
                    "id": "install-project-skill:fixture-skill",
                    "skill": "fixture-skill",
                    "replace": False,
                    "files": {"SKILL.md": {"content": content, "mode": 0o644}},
                    "expectedSha256": {"SKILL.md": hashlib.sha256(content).hexdigest()},
                }
            ],
        )

        self.assertTrue(result["ok"], result)
        self.assertEqual(
            (repo / ".agents" / "skills" / "fixture-skill" / "SKILL.md").read_bytes(),
            content,
        )
        self.assertFalse((repo / ".planning").exists())

    def test_promotion_and_verification_failures_restore_project_and_state(self):
        for fault in ("promotion:legacy-selection-v0-to-v1", "verification"):
            with self.subTest(fault=fault):
                repo = self.make_repo(git=True)
                original = {LEGACY_PROFILE_KEY: "legacy", "custom": {"keep": True}}
                self.write_json(repo / ".dev-flow.json", original)
                self.commit_all(repo)
                plan = plan_project_refresh(repo, self.config_plugin)

                result = refresh_module.apply_project_refresh(
                    repo,
                    self.config_plugin,
                    expected_plan=plan["planSha256"],
                    authorizations={"workflow-config-migration"},
                    fault_injection=fault,
                )

                self.assertFalse(result["ok"], result)
                self.assertEqual(result["status"], "verification_failed_rolled_back")
                self.assertEqual(json.loads((repo / ".dev-flow.json").read_text()), original)
                runtime = repo / ".planning" / "devflow" / "plugin-project-migration"
                self.assertFalse((runtime / "state.json").exists())
                self.assertFalse((runtime / "transactions").exists())

    def test_state_is_advanced_only_after_project_paths_verify(self):
        repo = self.make_repo(git=True)
        self.write_json(repo / ".dev-flow.json", {LEGACY_PROFILE_KEY: "legacy"})
        self.commit_all(repo)
        plan = plan_project_refresh(repo, self.config_plugin)
        observed_modes: list[str | None] = []
        original_atomic_write = refresh_module.atomic_write_devflow

        def observe_state_write(repo_path, path, text):
            if Path(path).name == "state.json":
                config = json.loads((repo / ".dev-flow.json").read_text())
                observed_modes.append(config.get("workflow", {}).get("mode"))
            return original_atomic_write(repo_path, path, text)

        with mock.patch.object(
            refresh_module,
            "atomic_write_devflow",
            side_effect=observe_state_write,
        ):
            result = refresh_module.apply_project_refresh(
                repo,
                self.config_plugin,
                expected_plan=plan["planSha256"],
                authorizations={"workflow-config-migration"},
            )

        self.assertTrue(result["ok"], result)
        self.assertEqual(observed_modes, ["full-openspec"])

    def test_rollback_failure_retains_transaction_evidence_and_does_not_advance_state(self):
        repo = self.make_repo(git=True)
        original = {LEGACY_PROFILE_KEY: "legacy"}
        self.write_json(repo / ".dev-flow.json", original)
        self.commit_all(repo)
        plan = plan_project_refresh(repo, self.config_plugin)

        result = refresh_module.apply_project_refresh(
            repo,
            self.config_plugin,
            expected_plan=plan["planSha256"],
            authorizations={"workflow-config-migration"},
            fault_injection="rollback",
        )

        self.assertFalse(result["ok"], result)
        self.assertEqual(result["status"], "rollback_failed")
        retained = repo / result["retainedTransactionPath"]
        self.assertTrue((retained / "contract.json").is_file())
        transaction = json.loads((retained / "contract.json").read_text())
        self.assertEqual(transaction["actions"], plan["actions"])
        self.assertIn("stateBefore", transaction)
        state = repo / ".planning" / "devflow" / "plugin-project-migration" / "state.json"
        self.assertFalse(state.exists())

        blocked = plan_project_refresh(repo, self.config_plugin)
        self.assertFalse(blocked["ok"], blocked)
        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(blocked["recovery"]["status"], "recovery_required")

    def test_retained_verified_tree_transaction_blocks_later_refresh(self):
        repo = self.make_repo()
        self.write_json(repo / ".dev-flow.json", {"workflow": {"mode": "full-openspec"}})
        retained = (
            repo
            / ".planning"
            / "devflow"
            / "plugin-project-migration"
            / "verified-tree-transactions"
            / "retained-fixture"
        )
        retained.mkdir(parents=True)
        self.write_json(retained / "contract.json", {"kind": "retained-fixture"})
        before = self.snapshot(repo)

        plan = plan_project_refresh(repo, self.config_plugin)

        self.assertFalse(plan["ok"], plan)
        self.assertEqual(plan["status"], "blocked")
        self.assertEqual(plan["recovery"]["status"], "recovery_required")
        self.assertIn(
            ".planning/devflow/plugin-project-migration/verified-tree-transactions/retained-fixture",
            plan["recovery"]["retainedPaths"],
        )
        self.assertEqual(self.snapshot(repo), before)

    def test_explicit_rollback_refuses_to_overwrite_post_apply_edits(self):
        repo = self.make_repo(git=True)
        self.write_json(repo / ".dev-flow.json", {LEGACY_PROFILE_KEY: "legacy"})
        self.commit_all(repo)
        plan = plan_project_refresh(repo, self.config_plugin)
        applied = refresh_module.apply_project_refresh(
            repo,
            self.config_plugin,
            expected_plan=plan["planSha256"],
            authorizations={"workflow-config-migration"},
        )
        edited = {"workflow": {"mode": "full-openspec"}, "afterApply": True}
        self.write_json(repo / ".dev-flow.json", edited)

        rollback = refresh_module.rollback_project_refresh(
            repo,
            self.config_plugin,
            applied["receiptPath"],
            apply=True,
        )

        self.assertFalse(rollback["ok"], rollback)
        self.assertEqual(rollback["status"], "rollback_blocked")
        self.assertIn("post_apply_edit:.dev-flow.json", rollback["issues"])
        self.assertEqual(json.loads((repo / ".dev-flow.json").read_text()), edited)

    def test_receipt_is_repo_bound_and_cannot_be_replayed_in_another_project(self):
        source_repo = self.make_repo(git=True)
        self.write_json(source_repo / ".dev-flow.json", {LEGACY_PROFILE_KEY: "legacy"})
        self.commit_all(source_repo)
        plan = plan_project_refresh(source_repo, self.config_plugin)
        applied = refresh_module.apply_project_refresh(
            source_repo,
            self.config_plugin,
            expected_plan=plan["planSha256"],
            authorizations={"workflow-config-migration"},
        )

        target_repo = self.make_repo()
        (target_repo / ".dev-flow.json").write_bytes(
            (source_repo / ".dev-flow.json").read_bytes()
        )
        target_receipt = (
            target_repo
            / ".planning"
            / "devflow"
            / "plugin-project-migration"
            / "receipts"
            / "copied.json"
        )
        target_receipt.parent.mkdir(parents=True)
        target_receipt.write_bytes(Path(applied["receiptPath"]).read_bytes())
        before = self.snapshot(target_repo)

        rollback = refresh_module.rollback_project_refresh(
            target_repo,
            self.config_plugin,
            target_receipt,
            apply=True,
        )

        self.assertFalse(rollback["ok"], rollback)
        self.assertEqual(rollback["status"], "rollback_blocked")
        self.assertIn("receipt_repo_mismatch", rollback["issues"])
        self.assertEqual(self.snapshot(target_repo), before)

    def test_tampered_receipt_cannot_delete_an_arbitrary_project_file(self):
        repo = self.make_repo()
        victim = repo / "victim.txt"
        victim.write_text("must survive\n")
        receipt_path = (
            repo
            / ".planning"
            / "devflow"
            / "plugin-project-migration"
            / "receipts"
            / "tampered.json"
        )
        receipt_path.parent.mkdir(parents=True)
        state_path = repo / ".planning" / "devflow" / "plugin-project-migration" / "state.json"
        receipt = {
            "schemaVersion": "1.0",
            "kind": "devflow-project-refresh-apply-receipt",
            "createdAt": "2026-08-06T00:00:00+00:00",
            "repo": str(repo),
            "status": "applied_and_verified",
            "planSha256": "sha256:" + "0" * 64,
            "sourceIdentity": {},
            "projectSchema": {"observed": 1, "target": 1},
            "migrationPath": [],
            "actions": [
                {
                    "id": "delete-victim",
                    "kind": "create_file",
                    "path": "victim.txt",
                    "beforeFingerprint": refresh_module._fingerprint(repo / "missing"),
                    "afterFingerprint": refresh_module._fingerprint(victim),
                    "authorization": "project-refresh-apply",
                    "dependencies": [],
                    "ownership": "devflow-create-if-absent",
                    "source": {"kind": "plugin_file", "path": "victim.txt"},
                    "rollback": {"kind": "remove_if_created", "pruneEmptyParents": []},
                    "verification": ["managed-path-readback"],
                }
            ],
            "authorizations": ["project-refresh-apply"],
            "changedPaths": ["victim.txt"],
            "preservedPaths": [],
            "stateBefore": None,
            "stateAfterFingerprint": refresh_module._fingerprint(state_path),
            "verification": {},
            "verificationReceiptPath": "unused",
            "rollbackStatus": "available",
            "receiptPath": str(receipt_path),
            "valuesRedacted": True,
        }
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")

        rollback = refresh_module.rollback_project_refresh(
            repo,
            self.config_plugin,
            receipt_path,
            apply=True,
        )

        self.assertFalse(rollback["ok"], rollback)
        self.assertEqual(rollback["status"], "rollback_blocked")
        self.assertIn("receipt_action_path_invalid:delete-victim", rollback["issues"])
        self.assertEqual(victim.read_text(), "must survive\n")

    def test_create_if_absent_configuration_has_conditional_delete_rollback(self):
        repo = self.make_repo()
        state = repo / ".planning" / "devflow" / "STATE.md"
        state.parent.mkdir(parents=True)
        state.write_text("---\nworkflow_version: 0.3.0\n---\n# State\n")
        plan = plan_project_refresh(repo, self.config_plugin)

        applied = refresh_module.apply_project_refresh(
            repo,
            self.config_plugin,
            expected_plan=plan["planSha256"],
            authorizations={"workflow-config-migration"},
        )
        rollback = refresh_module.rollback_project_refresh(
            repo,
            self.config_plugin,
            applied["receiptPath"],
            apply=True,
        )

        self.assertTrue(applied["ok"], applied)
        self.assertTrue(rollback["ok"], rollback)
        self.assertFalse((repo / ".dev-flow.json").exists())

    def test_cli_plan_apply_verify_and_explicit_rollback_have_stable_exit_classes(self):
        repo = self.make_repo(git=True)
        self.write_json(repo / ".dev-flow.json", {LEGACY_PROFILE_KEY: "legacy"})
        self.commit_all(repo)
        script = PLUGIN_ROOT / "scripts" / "plugin_project_migration.py"

        planned = subprocess.run(
            [
                sys.executable,
                str(script),
                "plan",
                "--repo",
                str(repo),
                "--plugin-root",
                str(self.config_plugin),
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        plan = json.loads(planned.stdout)
        self.assertEqual(planned.returncode, 2, planned.stderr)
        self.assertEqual(plan["status"], "migration_pending")

        applied = subprocess.run(
            [
                sys.executable,
                str(script),
                "apply",
                "--repo",
                str(repo),
                "--plugin-root",
                str(self.config_plugin),
                "--expect-plan",
                plan["planSha256"],
                "--allow",
                "workflow-config-migration",
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        result = json.loads(applied.stdout)
        self.assertEqual(applied.returncode, 0, applied.stderr)
        self.assertEqual(result["status"], "applied_and_verified")

        verified = subprocess.run(
            [
                sys.executable,
                str(script),
                "verify",
                "--repo",
                str(repo),
                "--plugin-root",
                str(self.config_plugin),
                "--receipt",
                result["receiptPath"],
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertEqual(json.loads(verified.stdout)["status"], "verified")

        rollback_plan = subprocess.run(
            [
                sys.executable,
                str(script),
                "rollback",
                "--repo",
                str(repo),
                "--plugin-root",
                str(self.config_plugin),
                "--receipt",
                result["receiptPath"],
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(rollback_plan.returncode, 2, rollback_plan.stderr)
        self.assertEqual(json.loads(rollback_plan.stdout)["status"], "authorization_required")

        rolled_back = subprocess.run(
            [
                sys.executable,
                str(script),
                "rollback",
                "--repo",
                str(repo),
                "--plugin-root",
                str(self.config_plugin),
                "--receipt",
                result["receiptPath"],
                "--apply",
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(rolled_back.returncode, 0, rolled_back.stderr)
        self.assertEqual(json.loads(rolled_back.stdout)["status"], "rolled_back")

        missing_receipt = subprocess.run(
            [
                sys.executable,
                str(script),
                "verify",
                "--repo",
                str(repo),
                "--plugin-root",
                str(self.config_plugin),
                "--receipt",
                "missing.json",
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(missing_receipt.returncode, 3, missing_receipt.stderr)
        failure = json.loads(missing_receipt.stdout)
        self.assertEqual(failure["status"], "invalid_request")
        self.assertEqual(failure["retryability"], "after_correction")
        self.assertNotIn("Traceback", missing_receipt.stderr)

    def test_current_agents_guidance_does_not_create_a_generated_candidate(self):
        plugin = self.make_contract_plugin()
        self.enable_agents_guidance(plugin)
        repo = self.make_repo()
        self.write_json(repo / ".dev-flow.json", {"workflow": {"mode": "full-openspec"}})
        agents = (plugin / "assets" / "templates" / "AGENTS.md.template").read_text()
        (repo / "AGENTS.md").write_text(agents.replace("{{project_mode}}", "greenfield"))
        before = self.snapshot(repo)

        plan = plan_project_refresh(repo, plugin)

        self.assertTrue(plan["ok"], plan)
        self.assertEqual(plan["agentsGuidance"]["status"], "unchanged")
        self.assertNotIn("AGENTS.md.generated", plan["writeSet"])
        self.assertEqual(self.snapshot(repo), before)

    def test_revision_two_agents_guidance_missing_only_readiness_rule_creates_merge_candidate(self):
        plugin = self.make_contract_plugin()
        self.enable_agents_guidance(plugin)
        repo = self.make_repo()
        self.write_json(repo / ".dev-flow.json", {"workflow": {"mode": "full-openspec"}})
        revision_two_fixture = json.loads(
            (
                PLUGIN_ROOT
                / "fixtures"
                / "implementation-readiness"
                / "agents-guidance-markers-revision2.json"
            ).read_text()
        )
        self.assertEqual(revision_two_fixture["refreshContractRevision"], 2)
        revision_two = "\n".join(revision_two_fixture["markers"]) + "\n"
        self.assertNotIn("## Project-Directed Implementation Readiness", revision_two)
        (repo / "AGENTS.md").write_text(revision_two)

        plan = plan_project_refresh(repo, plugin)

        self.assertTrue(plan["ok"], plan)
        self.assertEqual(plan["agentsGuidance"]["status"], "agents_merge_required")
        self.assertEqual(
            plan["agentsGuidance"]["missingMarkers"],
            ["Project-Directed Implementation Readiness"],
        )
        self.assertIn("AGENTS.md.generated", plan["writeSet"])

    def test_stale_agents_guidance_creates_only_a_merge_candidate_and_remains_incomplete(self):
        plugin = self.make_contract_plugin()
        self.enable_agents_guidance(plugin)
        repo = self.make_repo()
        self.write_json(repo / ".dev-flow.json", {"workflow": {"mode": "full-openspec"}})
        (repo / "AGENTS.md").write_text("# Project-owned rules\n")
        original = (repo / "AGENTS.md").read_text()
        plan = plan_project_refresh(repo, plugin)

        result = refresh_module.apply_project_refresh(
            repo,
            plugin,
            expected_plan=plan["planSha256"],
            authorizations={"project-refresh-apply"},
        )

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["status"], "applied_incomplete")
        self.assertEqual(result["changedPaths"], ["AGENTS.md.generated"])
        self.assertEqual((repo / "AGENTS.md").read_text(), original)
        self.assertTrue((repo / "AGENTS.md.generated").is_file())
        self.assertTrue(result["manualActions"])

    def test_divergent_agents_candidate_blocks_candidate_creation_without_data_loss(self):
        plugin = self.make_contract_plugin()
        self.enable_agents_guidance(plugin)
        repo = self.make_repo()
        self.write_json(repo / ".dev-flow.json", {"workflow": {"mode": "full-openspec"}})
        (repo / "AGENTS.md").write_text("# Project-owned rules\n")
        (repo / "AGENTS.md.generated").write_text("# Human draft that must survive\n")
        before = self.snapshot(repo)

        plan = plan_project_refresh(repo, plugin)

        self.assertTrue(plan["ok"], plan)
        self.assertEqual(plan["status"], "manual_review_required")
        self.assertEqual(plan["agentsGuidance"]["status"], "candidate_conflict")
        self.assertNotIn("AGENTS.md.generated", plan["writeSet"])
        self.assertIn("AGENTS.md.generated", plan["preservedPaths"])
        self.assertEqual(self.snapshot(repo), before)

    def test_legacy_skills_and_custom_official_skill_copies_are_report_only(self):
        plugin = self.make_contract_plugin()
        self.enable_managed_skill(plugin, "managed-skill")
        repo = self.make_repo()
        self.write_json(repo / ".dev-flow.json", {"workflow": {"mode": "full-openspec"}})
        legacy = repo / ".codex" / "skills" / "managed-skill" / "SKILL.md"
        legacy.parent.mkdir(parents=True)
        legacy.write_text("legacy bytes\n")
        official = repo / ".agents" / "skills" / "managed-skill" / "SKILL.md"
        official.parent.mkdir(parents=True)
        official.write_text("custom official bytes\n")
        before = self.snapshot(repo)

        plan = plan_project_refresh(repo, plugin)

        self.assertTrue(plan["ok"], plan)
        self.assertEqual(plan["status"], "manual_review_required")
        self.assertEqual(plan["managedSkills"]["status"], "manual_review_required")
        self.assertEqual(plan["legacySkillLayout"]["status"], "manual_review_required")
        self.assertEqual(plan["writeSet"], [])
        self.assertIn(".agents/skills/managed-skill", plan["preservedPaths"])
        self.assertIn(".codex/skills/managed-skill", plan["preservedPaths"])
        self.assertEqual(self.snapshot(repo), before)

    def test_managed_skill_source_with_a_symlinked_ancestor_is_manual_only(self):
        plugin = self.make_contract_plugin()
        external = self.make_repo()
        skill_file = external / "managed-skill" / "SKILL.md"
        skill_file.parent.mkdir(parents=True)
        skill_file.write_text("---\nname: managed-skill\ndescription: external\n---\n")
        (plugin / "skills").symlink_to(external, target_is_directory=True)
        manifest_path = plugin / ".codex-plugin" / "project-migration.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["projectLocalSkills"] = ["managed-skill"]
        self.write_json(manifest_path, manifest)
        repo = self.make_repo()
        self.write_json(repo / ".dev-flow.json", {"workflow": {"mode": "full-openspec"}})
        before = self.snapshot(repo)

        plan = plan_project_refresh(repo, plugin)

        self.assertTrue(plan["ok"], plan)
        self.assertEqual(plan["managedSkills"]["status"], "manual_review_required")
        self.assertEqual(plan["writeSet"], [])
        self.assertIn(".agents/skills/managed-skill", plan["preservedPaths"])
        self.assertEqual(self.snapshot(repo), before)

    def test_historical_and_legacy_integration_paths_are_report_only(self):
        repo = self.make_repo()
        self.write_json(repo / ".dev-flow.json", {"workflow": {"mode": "full-openspec"}})
        roadmap = repo / ".planning" / "ROADMAP.md"
        roadmap.parent.mkdir(parents=True)
        roadmap.write_text("# Historical plan that must survive\n")
        before = self.snapshot(repo)

        plan = plan_project_refresh(repo, self.config_plugin)

        self.assertEqual(plan["status"], "manual_review_required")
        self.assertIn(".planning/ROADMAP.md", plan["preservedPaths"])
        self.assertIn(".planning/ROADMAP.md", plan["readSet"])
        self.assertEqual(plan["legacySkillLayout"]["inspectorStatus"], "legacy_detected")
        self.assertEqual(self.snapshot(repo), before)

    def test_v1_migration_state_is_upgraded_compatibly_and_restored_on_rollback(self):
        repo = self.make_repo(git=True)
        self.write_json(repo / ".dev-flow.json", {LEGACY_PROFILE_KEY: "legacy"})
        self.commit_all(repo)
        state_path = repo / ".planning" / "devflow" / "plugin-project-migration" / "state.json"
        state_v1 = {
            "schemaVersion": "1.0",
            "plugins": {
                "dev-flow": {
                    "version": "old",
                    "projectLocalSkills": ["legacy-entry"],
                    "managedFiles": [],
                },
                "other-plugin": {"version": "keep-me"},
            },
        }
        self.write_json(state_path, state_v1)
        plan = plan_project_refresh(repo, self.config_plugin)

        applied = refresh_module.apply_project_refresh(
            repo,
            self.config_plugin,
            expected_plan=plan["planSha256"],
            authorizations={"workflow-config-migration"},
        )
        state_v2 = json.loads(state_path.read_text())

        self.assertTrue(applied["ok"], applied)
        self.assertEqual(state_v2["schemaVersion"], "2.0")
        self.assertEqual(state_v2["plugins"]["other-plugin"], {"version": "keep-me"})
        self.assertEqual(
            state_v2["plugins"]["dev-flow"]["projectLocalSkills"],
            ["legacy-entry"],
        )
        rolled_back = refresh_module.rollback_project_refresh(
            repo,
            self.config_plugin,
            applied["receiptPath"],
            apply=True,
        )
        self.assertTrue(rolled_back["ok"], rolled_back)
        self.assertEqual(json.loads(state_path.read_text()), state_v1)

    def test_contract_plan_and_receipt_match_their_published_json_schemas(self):
        from jsonschema import Draft202012Validator

        schema_root = PLUGIN_ROOT / "schemas"
        contract_schema = json.loads((schema_root / "project-refresh-contract.schema.json").read_text())
        plan_schema = json.loads((schema_root / "project-refresh-plan.schema.json").read_text())
        receipt_schema = json.loads((schema_root / "project-refresh-receipt.schema.json").read_text())
        contract = json.loads((PLUGIN_ROOT / ".codex-plugin" / "project-migration.json").read_text())
        Draft202012Validator(contract_schema).validate(contract)

        repo = self.make_repo(git=True)
        self.write_json(repo / ".dev-flow.json", {LEGACY_PROFILE_KEY: "legacy"})
        self.commit_all(repo)
        plan = plan_project_refresh(repo, self.config_plugin)
        Draft202012Validator(plan_schema).validate(plan)
        applied = refresh_module.apply_project_refresh(
            repo,
            self.config_plugin,
            expected_plan=plan["planSha256"],
            authorizations={"workflow-config-migration"},
        )
        receipt = json.loads(Path(applied["receiptPath"]).read_text())
        Draft202012Validator(receipt_schema).validate(receipt)
        verification_receipt = json.loads(Path(applied["verificationReceiptPath"]).read_text())
        Draft202012Validator(receipt_schema).validate(verification_receipt)
        required_verification_fields = {
            "projectSchema",
            "migrationPath",
            "actions",
            "authorizations",
            "changedPaths",
            "preservedPaths",
            "stateBeforeFingerprint",
            "stateAfterFingerprint",
            "actionSetSha256",
            "receiptEvidenceSha256",
            "verification",
            "rollbackStatus",
            "applyReceiptPath",
            "valuesRedacted",
        }
        self.assertTrue(
            required_verification_fields <= set(verification_receipt),
            sorted(required_verification_fields - set(verification_receipt)),
        )
        self.assertEqual(verification_receipt["actions"], receipt["actions"])
        self.assertEqual(verification_receipt["authorizations"], receipt["authorizations"])
        self.assertEqual(verification_receipt["actionSetSha256"], receipt["actionSetSha256"])
        self.assertEqual(verification_receipt["rollbackStatus"], "available")

    def test_apply_and_verification_receipts_reject_runtime_evidence_tampering(self):
        repo = self.make_repo(git=True)
        self.write_json(repo / ".dev-flow.json", {LEGACY_PROFILE_KEY: "legacy"})
        self.commit_all(repo)
        plan = plan_project_refresh(repo, self.config_plugin)
        applied = refresh_module.apply_project_refresh(
            repo,
            self.config_plugin,
            expected_plan=plan["planSha256"],
            authorizations={"workflow-config-migration"},
        )
        self.assertTrue(applied["ok"], applied)

        standalone = refresh_module.verify_project_refresh(
            repo,
            self.config_plugin,
            applied["verificationReceiptPath"],
        )
        self.assertTrue(standalone["ok"], standalone)

        apply_path = Path(applied["receiptPath"])
        original_apply_receipt = json.loads(apply_path.read_text())
        apply_receipt = json.loads(json.dumps(original_apply_receipt))
        original_before_fingerprint = dict(apply_receipt["stateBeforeFingerprint"])
        apply_receipt["stateBeforeFingerprint"] = "not-a-fingerprint"
        apply_path.write_text(json.dumps(apply_receipt, indent=2, sort_keys=True) + "\n")
        apply_tamper = refresh_module.verify_project_refresh(
            repo,
            self.config_plugin,
            apply_path,
        )
        self.assertFalse(apply_tamper["ok"], apply_tamper)
        self.assertIn("receipt_state_before_fingerprint_invalid", apply_tamper["issues"])

        apply_receipt["stateBeforeFingerprint"] = {
            **original_before_fingerprint,
            "sha256": "f" * 64,
        }
        apply_receipt["receiptEvidenceSha256"] = refresh_module._receipt_evidence_digest(
            apply_receipt
        )
        apply_path.write_text(json.dumps(apply_receipt, indent=2, sort_keys=True) + "\n")
        resealed_apply_tamper = refresh_module.verify_project_refresh(
            repo,
            self.config_plugin,
            apply_path,
        )
        self.assertFalse(resealed_apply_tamper["ok"], resealed_apply_tamper)
        self.assertIn(
            "receipt_action_set_digest_mismatch",
            resealed_apply_tamper["issues"],
        )

        resealed_apply_verification = json.loads(json.dumps(original_apply_receipt))
        resealed_apply_verification["verification"]["ok"] = False
        resealed_apply_verification["receiptEvidenceSha256"] = (
            refresh_module._receipt_evidence_digest(resealed_apply_verification)
        )
        apply_path.write_text(
            json.dumps(resealed_apply_verification, indent=2, sort_keys=True) + "\n"
        )
        apply_verification_tamper = refresh_module.verify_project_refresh(
            repo,
            self.config_plugin,
            apply_path,
        )
        self.assertFalse(apply_verification_tamper["ok"], apply_verification_tamper)
        self.assertIn(
            "receipt_action_set_digest_mismatch",
            apply_verification_tamper["issues"],
        )

        resealed_apply_rollback = json.loads(json.dumps(original_apply_receipt))
        resealed_apply_rollback["rollbackStatus"] = "forged-status"
        resealed_apply_rollback["receiptEvidenceSha256"] = (
            refresh_module._receipt_evidence_digest(resealed_apply_rollback)
        )
        apply_path.write_text(
            json.dumps(resealed_apply_rollback, indent=2, sort_keys=True) + "\n"
        )
        apply_rollback_tamper = refresh_module.verify_project_refresh(
            repo,
            self.config_plugin,
            apply_path,
        )
        self.assertFalse(apply_rollback_tamper["ok"], apply_rollback_tamper)
        self.assertIn(
            "receipt_action_set_digest_mismatch",
            apply_rollback_tamper["issues"],
        )

        apply_path.write_text(json.dumps(apply_receipt, indent=2, sort_keys=True) + "\n")

        verification_path = Path(applied["verificationReceiptPath"])
        verification_without_apply_trust = refresh_module.verify_project_refresh(
            repo,
            self.config_plugin,
            verification_path,
        )
        self.assertTrue(
            verification_without_apply_trust["ok"],
            verification_without_apply_trust,
        )
        original_verification_receipt = json.loads(verification_path.read_text())
        verification_receipt = json.loads(json.dumps(original_verification_receipt))
        verification_receipt["stateBeforeFingerprint"] = {
            **verification_receipt["stateBeforeFingerprint"],
            "sha256": "e" * 64,
        }
        verification_receipt["receiptEvidenceSha256"] = (
            refresh_module._receipt_evidence_digest(verification_receipt)
        )
        verification_path.write_text(
            json.dumps(verification_receipt, indent=2, sort_keys=True) + "\n"
        )
        resealed_verification_tamper = refresh_module.verify_project_refresh(
            repo,
            self.config_plugin,
            verification_path,
        )
        self.assertFalse(
            resealed_verification_tamper["ok"],
            resealed_verification_tamper,
        )
        self.assertIn(
            "receipt_action_set_digest_mismatch",
            resealed_verification_tamper["issues"],
        )

        resealed_verification_result = json.loads(
            json.dumps(original_verification_receipt)
        )
        resealed_verification_result["verification"]["ok"] = False
        resealed_verification_result["receiptEvidenceSha256"] = (
            refresh_module._receipt_evidence_digest(resealed_verification_result)
        )
        verification_path.write_text(
            json.dumps(resealed_verification_result, indent=2, sort_keys=True) + "\n"
        )
        verification_result_tamper = refresh_module.verify_project_refresh(
            repo,
            self.config_plugin,
            verification_path,
        )
        self.assertFalse(verification_result_tamper["ok"], verification_result_tamper)
        self.assertIn(
            "receipt_action_set_digest_mismatch",
            verification_result_tamper["issues"],
        )

        resealed_verification_rollback = json.loads(
            json.dumps(original_verification_receipt)
        )
        resealed_verification_rollback["rollbackStatus"] = "forged-status"
        resealed_verification_rollback["receiptEvidenceSha256"] = (
            refresh_module._receipt_evidence_digest(resealed_verification_rollback)
        )
        verification_path.write_text(
            json.dumps(resealed_verification_rollback, indent=2, sort_keys=True) + "\n"
        )
        verification_rollback_tamper = refresh_module.verify_project_refresh(
            repo,
            self.config_plugin,
            verification_path,
        )
        self.assertFalse(
            verification_rollback_tamper["ok"],
            verification_rollback_tamper,
        )
        self.assertIn(
            "receipt_action_set_digest_mismatch",
            verification_rollback_tamper["issues"],
        )

        verification_receipt = json.loads(json.dumps(original_verification_receipt))
        verification_receipt["verification"]["ok"] = False
        verification_path.write_text(
            json.dumps(verification_receipt, indent=2, sort_keys=True) + "\n"
        )
        verification_tamper = refresh_module.verify_project_refresh(
            repo,
            self.config_plugin,
            verification_path,
        )
        self.assertFalse(verification_tamper["ok"], verification_tamper)
        self.assertIn("receipt_evidence_digest_mismatch", verification_tamper["issues"])

    def test_supported_project_refresh_fixture_matrix_reaches_the_current_schema(self):
        fixture_root = PLUGIN_ROOT / "fixtures" / "project-refresh"
        matrix = json.loads((fixture_root / "manifest.json").read_text())
        self.assertEqual(matrix["currentProjectSchema"], 2)
        plugin = self.make_contract_plugin(
            head=2,
            steps=[
                {
                    "id": "legacy-selection-v0-to-v1",
                    "from": 0,
                    "to": 1,
                    "authorization": "workflow-config-migration",
                    "configTarget": 1,
                },
                {
                    "id": "full-openspec-v1-to-v2",
                    "from": 1,
                    "to": 2,
                    "authorization": "workflow-config-migration",
                    "configTarget": 2,
                },
            ],
        )
        for version in (1, 2):
            target = plugin / "assets" / "project-refresh" / f"config-v{version}.json"
            target.write_bytes(
                (PLUGIN_ROOT / "assets" / "project-refresh" / f"config-v{version}.json").read_bytes()
            )
        manifest_path = plugin / ".codex-plugin" / "project-migration.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["configTargets"] = {
            "1": "assets/project-refresh/config-v1.json",
            "2": "assets/project-refresh/config-v2.json",
        }
        self.write_json(manifest_path, manifest)

        for entry in matrix["fixtures"]:
            with self.subTest(fixture=entry["path"]):
                repo = self.make_repo(git=True)
                source = fixture_root / entry["path"]
                (repo / ".dev-flow.json").write_bytes(source.read_bytes())
                self.commit_all(repo)
                before = (repo / ".dev-flow.json").read_bytes()
                plan = plan_project_refresh(repo, plugin)
                self.assertEqual(plan["projectSchema"]["observed"], entry["observedSchema"])
                if entry.get("manualOnly"):
                    self.assertEqual(plan["status"], "manual_review_required")
                    self.assertEqual(plan["writeSet"], [])
                    self.assertEqual((repo / ".dev-flow.json").read_bytes(), before)
                    continue
                self.assertEqual(plan["migrationPath"], entry["expectedMigrationPath"])
                if not entry["expectedMigrationPath"]:
                    self.assertEqual(plan["status"], "migration_pending")
                    applied = refresh_module.apply_project_refresh(
                        repo,
                        plugin,
                        expected_plan=plan["planSha256"],
                        authorizations={"project-refresh-apply"},
                    )
                    self.assertTrue(applied["ok"], applied)
                    self.assertEqual(
                        plan_project_refresh(repo, plugin)["status"],
                        "current",
                    )
                    continue
                result = refresh_module.apply_project_refresh(
                    repo,
                    plugin,
                    expected_plan=plan["planSha256"],
                    authorizations={"workflow-config-migration"},
                )
                self.assertTrue(result["ok"], result)
                migrated = json.loads((repo / ".dev-flow.json").read_text())
                self.assertEqual(migrated["workflow"]["mode"], "full-openspec")
                recognized, _ = refresh_module._legacy_inputs(migrated)
                self.assertEqual(recognized, [])


if __name__ == "__main__":
    unittest.main()
