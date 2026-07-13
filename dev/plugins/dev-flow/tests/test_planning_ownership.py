import hashlib
import importlib
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

TEST_ROOT = Path(__file__).resolve().parent
PLUGIN_ROOT = TEST_ROOT.parent
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))


class PlanningOwnershipTests(unittest.TestCase):
    def planning_module(self):
        spec = importlib.util.find_spec("workflow_planning_paths")
        self.assertIsNotNone(spec, "planning ownership module must exist")
        return importlib.import_module("workflow_planning_paths")

    def repo(self):
        return Path(tempfile.mkdtemp(prefix="devflow-planning-owner-"))

    def repo_with_external_devflow_parent(self):
        repo = self.repo()
        outside = Path(tempfile.mkdtemp(prefix="devflow-planning-outside-"))
        planning = repo / ".planning"
        planning.mkdir()
        (planning / "devflow").symlink_to(outside, target_is_directory=True)
        return repo, outside

    def write_state(self, path, marker="workflow_version: 0.3.0"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\n{marker}\ncurrent_stage: planning\n---\n\n# State\n")

    def digest(self, path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_devflow_paths_are_fully_namespaced(self):
        module = self.planning_module()
        repo = self.repo().resolve()

        self.assertEqual(module.state_path(repo), repo / ".planning" / "devflow" / "STATE.md")
        self.assertEqual(module.verification_root(repo), repo / ".planning" / "devflow" / "verification")
        self.assertEqual(module.checkpoint_root(repo), repo / ".planning" / "devflow" / "checkpoints")
        self.assertEqual(module.compact_result_root(repo), repo / ".planning" / "devflow" / "compact-results")
        self.assertEqual(module.context_health_root(repo), repo / ".planning" / "devflow" / "context-health")
        self.assertEqual(module.codebase_root(repo), repo / ".planning" / "devflow" / "codebase")
        self.assertEqual(module.delegation_root(repo), repo / ".planning" / "devflow" / "claude-code")
        self.assertEqual(
            module.plugin_migration_root(repo),
            repo / ".planning" / "devflow" / "plugin-project-migration",
        )

    def test_write_guard_rejects_gsd_root_casefold_and_outside_paths(self):
        module = self.planning_module()
        repo = self.repo()

        allowed = module.guard_devflow_write(repo, repo / ".planning" / "devflow" / "verification" / "a.md")

        self.assertTrue(allowed)
        for path in [
            repo / ".planning" / "STATE.md",
            repo / ".planning" / "phases" / "01" / "VERIFICATION.md",
            repo / ".planning" / "codebase" / "ARCHITECTURE.md",
            repo / ".planning" / "DEVFLOW" / "STATE.md",
            repo.parent / "outside.md",
        ]:
            with self.subTest(path=path):
                with self.assertRaises(module.PlanningOwnershipError):
                    module.guard_devflow_write(repo, path)

    def test_verification_writer_rejects_symlinked_namespace_parent(self):
        module = self.planning_module()
        verification = importlib.import_module("workflow_verification")
        repo, outside = self.repo_with_external_devflow_parent()

        with self.assertRaises(module.PlanningOwnershipError):
            verification.record_verification(repo, "python -m unittest", "pass")

        self.assertEqual(list(outside.rglob("*")), [])

    def test_compact_result_writer_rejects_symlinked_namespace_parent(self):
        module = self.planning_module()
        compact = importlib.import_module("workflow_compact_result")
        repo, outside = self.repo_with_external_devflow_parent()
        target = repo / ".planning" / "devflow" / "compact-results" / "checkpoint.json"

        with self.assertRaises(module.PlanningOwnershipError):
            compact.write_compact_result(
                repo,
                target,
                {"checkpoint_id": "checkpoint", "checkpoint_file": "checkpoint.md"},
                "completed",
                "manual",
                "2026-07-10T00:00:00+00:00",
                None,
                {},
            )

        self.assertEqual(list(outside.rglob("*")), [])

    def test_provider_lock_writer_rejects_symlinked_namespace_parent(self):
        module = self.planning_module()
        activation = importlib.import_module("workflow_provider_activation")
        repo, outside = self.repo_with_external_devflow_parent()
        diagnosis = {"selection": {}, "selectedProviders": [], "providers": {}}

        with self.assertRaises(module.PlanningOwnershipError):
            activation.persist_provider_lock(
                diagnosis,
                repo,
                apply=True,
                persist_selection=True,
            )

        self.assertEqual(list(outside.rglob("*")), [])

    def test_scaffold_writer_rejects_symlinked_repo_parent_without_external_write(self):
        scaffold = importlib.import_module("workflow_scaffold")
        repo = self.repo()
        outside = Path(tempfile.mkdtemp(prefix="devflow-scaffold-outside-"))
        (repo / "openspec").symlink_to(outside, target_is_directory=True)
        writer = scaffold.WritePlan(repo)

        with self.assertRaises(scaffold.ScaffoldWriteError):
            writer.write("openspec/config.yaml", "schema: spec-driven\n")

        self.assertEqual(list(outside.rglob("*")), [])

    def test_project_skill_writer_rejects_symlinked_agents_skill_root(self):
        paths = importlib.import_module("workflow_project_skill_paths")
        installer = importlib.import_module("workflow_project_skill_install")
        repo = self.repo()
        outside = Path(tempfile.mkdtemp(prefix="devflow-skill-outside-"))
        source = Path(tempfile.mkdtemp(prefix="devflow-skill-source-"))
        (source / "SKILL.md").write_text("---\nname: fixture\n---\n")
        (repo / ".agents").mkdir()
        (repo / ".agents" / "skills").symlink_to(outside, target_is_directory=True)

        with self.assertRaises(paths.ProjectSkillOwnershipError):
            installer.install_project_skill(
                repo,
                "fixture",
                "fixture",
                source,
                dry_run=False,
            )

        self.assertEqual(list(outside.rglob("*")), [])

    def test_namespaced_state_has_read_write_precedence(self):
        module = self.planning_module()
        state = importlib.import_module("workflow_state")
        repo = self.repo()
        legacy = repo / ".planning" / "STATE.md"
        namespaced = module.state_path(repo)
        self.write_state(legacy)
        self.write_state(namespaced)

        resolution = state.resolve_state(repo)

        self.assertEqual(resolution["status"], "namespaced")
        self.assertEqual(Path(resolution["readPath"]), namespaced)
        self.assertEqual(Path(resolution["writePath"]), namespaced)
        self.assertTrue(resolution["writeAllowed"])

    def test_legacy_devflow_state_is_read_only_before_sunset(self):
        module = self.planning_module()
        state = importlib.import_module("workflow_state")
        repo = self.repo()
        legacy = repo / ".planning" / "STATE.md"
        self.write_state(legacy)
        before = self.digest(legacy)

        resolution = state.resolve_state(repo, current_version="0.4.0")

        self.assertEqual(resolution["status"], "legacy_read_only")
        self.assertEqual(resolution["data"]["workflow_version"], "0.3.0")
        self.assertFalse(resolution["writeAllowed"])
        self.assertEqual(resolution["nextAction"], "migrate_devflow_state")
        with self.assertRaises(module.PlanningOwnershipError) as caught:
            state.update_state(repo, current_stage="implementing")
        self.assertEqual(caught.exception.code, "migration_required")
        self.assertEqual(self.digest(legacy), before)
        self.assertFalse(module.state_path(repo).exists())

    def test_legacy_state_is_not_read_at_or_after_sunset(self):
        self.planning_module()
        state = importlib.import_module("workflow_state")
        repo = self.repo()
        self.write_state(repo / ".planning" / "STATE.md")

        resolution = state.resolve_state(repo, current_version="1.0.0")

        self.assertEqual(resolution["status"], "legacy_expired")
        self.assertEqual(resolution["data"], {})
        self.assertEqual(resolution["sunsetRelease"], "1.0.0")

    def test_gsd_and_mixed_root_state_are_never_devflow_input(self):
        module = self.planning_module()
        state = importlib.import_module("workflow_state")
        gsd_repo = self.repo()
        mixed_repo = self.repo()
        self.write_state(gsd_repo / ".planning" / "STATE.md", "gsd_state_version: 1")
        self.write_state(
            mixed_repo / ".planning" / "STATE.md",
            "workflow_version: 0.3.0\ngsd_state_version: 1",
        )

        gsd = state.resolve_state(gsd_repo)
        mixed = state.resolve_state(mixed_repo)

        self.assertEqual(gsd["status"], "gsd_owned")
        self.assertEqual(gsd["data"], {})
        self.assertEqual(mixed["status"], "manual_review_required")
        self.assertEqual(mixed["data"], {})
        with self.assertRaises(module.PlanningOwnershipError) as caught:
            state.write_state(gsd_repo, state.default_state_values("brownfield", "x"))
        self.assertEqual(caught.exception.code, "gsd_owned")


if __name__ == "__main__":
    unittest.main()
