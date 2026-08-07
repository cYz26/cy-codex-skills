import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


class LegacyWorkflowConfigTests(unittest.TestCase):
    def make_repo(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="devflow-legacy-inspection-"))

    def module(self):
        return importlib.import_module("legacy_workflow_config")

    def snapshot(self, repo: Path) -> list[tuple[str, str, bytes | str]]:
        snapshot: list[tuple[str, str, bytes | str]] = []
        for path in sorted(repo.rglob("*")):
            relative = path.relative_to(repo).as_posix()
            if path.is_symlink():
                snapshot.append((relative, "symlink", path.readlink().as_posix()))
            elif path.is_file():
                snapshot.append((relative, "file", path.read_bytes()))
            else:
                snapshot.append((relative, "directory", b""))
        return snapshot

    def test_reports_legacy_config_fields_and_canonical_target_without_writes(self):
        repo = self.make_repo()
        config = {
            "workflow": {
                "mode": "full-openspec",
                "methodology_profile": "strict-superpowers",
                "roadmap_provider": "gsd",
                "provider_selectors": {
                    "superpowers": {"source_id": "superpowers-openai-curated-remote"}
                },
                "roadmap_bindings": {"change-a": {"phase_id": "02"}},
            },
            "hook": {"mode": "warn"},
            "archive": {"policy": "manual"},
        }
        (repo / ".dev-flow.json").write_text(json.dumps(config, indent=2) + "\n")
        before = self.snapshot(repo)

        first = self.module().inspect_legacy_workflow_config(repo)
        second = self.module().inspect_legacy_workflow_config(repo)

        self.assertEqual(first, second)
        self.assertEqual(self.snapshot(repo), before)
        self.assertEqual(first["status"], "legacy_detected")
        self.assertTrue(first["readOnly"])
        self.assertTrue(first["valuesRedacted"])
        by_field = {item["field"]: item for item in first["recognizedInputs"]}
        self.assertEqual(by_field["workflow.methodology_profile"]["valueType"], "string")
        self.assertEqual(by_field["workflow.roadmap_provider"]["valueType"], "string")
        self.assertEqual(by_field["workflow.provider_selectors"]["valueType"], "object")
        self.assertEqual(by_field["workflow.roadmap_bindings"]["valueType"], "object")
        self.assertTrue(all("value" not in item for item in first["recognizedInputs"]))
        self.assertEqual(
            first["targetConfiguration"],
            {"projectContract": 2, "workflow": {"mode": "full-openspec"}},
        )

    def test_reports_top_level_and_camel_case_legacy_config_aliases(self):
        repo = self.make_repo()
        (repo / ".dev-flow.json").write_text(
            json.dumps(
                {
                    "methodologyProfile": "lean-matt",
                    "roadmapBindings": {"change-a": {"phase_id": "01"}},
                    "workflow": {
                        "roadmapProvider": "gsd",
                        "providerSelectors": {"gsd": {"source_id": "gsd-core-1-6-1"}},
                    },
                }
            )
            + "\n"
        )

        result = self.module().inspect_legacy_workflow_config(repo)

        self.assertEqual(result["status"], "legacy_detected")
        by_field = {item["field"]: item for item in result["recognizedInputs"]}
        self.assertEqual(by_field["methodologyProfile"]["valueType"], "string")
        self.assertEqual(by_field["workflow.roadmapProvider"]["valueType"], "string")
        self.assertEqual(by_field["workflow.providerSelectors"]["valueType"], "object")
        self.assertEqual(by_field["roadmapBindings"]["valueType"], "object")

    def test_classifies_legacy_artifacts_and_preserves_ambiguous_history(self):
        repo = self.make_repo()
        lock = repo / ".planning" / "devflow" / "providers.lock.json"
        lock.parent.mkdir(parents=True)
        lock.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "providers": {
                        "gsd": {"version": "1.6.1"},
                        "superpowers": {"sourceChannel": "openai-curated-remote"},
                    },
                },
                sort_keys=True,
            )
            + "\n"
        )
        profile = repo / ".codex" / ".gsd-profile"
        profile.parent.mkdir(parents=True)
        profile.write_text("gsd\n")
        generated_target = repo / ".legacy-generated" / "gsd-progress"
        generated_target.mkdir(parents=True)
        gsd_link = repo / ".agents" / "skills" / "gsd-progress"
        gsd_link.parent.mkdir(parents=True)
        gsd_link.symlink_to(generated_target, target_is_directory=True)
        ambiguous_skill = repo / ".agents" / "skills" / "using-superpowers"
        ambiguous_skill.mkdir()
        (ambiguous_skill / "SKILL.md").write_text("# locally edited\n")
        roadmap = repo / ".planning" / "ROADMAP.md"
        roadmap.write_text("# historical roadmap\n")
        draft = repo / "docs" / "superpowers" / "plans" / "old-plan.md"
        draft.parent.mkdir(parents=True)
        draft.write_text("# historical draft\n")
        broken_agent = repo / ".codex" / "agents" / "gsd-planner.toml"
        broken_agent.parent.mkdir(parents=True)
        broken_agent.symlink_to(repo / "missing-gsd-planner.toml")
        before = self.snapshot(repo)

        result = self.module().inspect_legacy_workflow_config(repo)

        self.assertEqual(self.snapshot(repo), before)
        self.assertEqual(result["status"], "manual_review_required")
        by_path = {item["path"]: item for item in result["artifacts"]}
        self.assertEqual(
            by_path[".planning/devflow/providers.lock.json"]["classification"],
            "generated_candidate",
        )
        self.assertEqual(
            by_path[".codex/.gsd-profile"]["classification"],
            "generated_candidate",
        )
        self.assertEqual(
            by_path[".agents/skills/gsd-progress"]["classification"],
            "generated_candidate",
        )
        self.assertEqual(
            by_path[".agents/skills/using-superpowers"]["classification"],
            "preserved_unknown",
        )
        self.assertEqual(
            by_path[".planning/ROADMAP.md"]["classification"],
            "user_history_data",
        )
        self.assertEqual(
            by_path["docs/superpowers/plans"]["classification"],
            "user_history_data",
        )
        self.assertEqual(
            by_path[".codex/agents/gsd-planner.toml"]["classification"],
            "conflict",
        )
        self.assertEqual(
            [item["field"] for item in result["recognizedInputs"]],
            ["providerLock.providers[0]", "providerLock.providers[1]"],
        )
        self.assertIn(".agents/skills/using-superpowers", result["preservedPaths"])
        self.assertIn(".planning/ROADMAP.md", result["preservedPaths"])
        self.assertTrue(
            all("safe to remove" not in action.lower() for action in result["manualActions"])
        )

    def test_cli_emits_json_and_exposes_no_mutation_mode(self):
        repo = self.make_repo()
        (repo / ".dev-flow.json").write_text(
            json.dumps({"workflow": {"roadmap_provider": "gsd"}}) + "\n"
        )
        before = self.snapshot(repo)
        script = SCRIPTS / "inspect_legacy_workflow_config.py"

        completed = subprocess.run(
            [sys.executable, str(script), "--repo", str(repo), "--json"],
            text=True,
            capture_output=True,
            check=False,
        )
        help_result = subprocess.run(
            [sys.executable, str(script), "--help"],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["status"], "legacy_detected")
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        for flag in (
            "--apply",
            "--cleanup",
            "--rollback",
            "--install",
            "--activate",
            "--commit",
            "--push",
            "--archive",
            "--write",
        ):
            self.assertNotIn(flag, help_result.stdout)
        self.assertEqual(self.snapshot(repo), before)

    def test_redacts_secret_bearing_values_and_unrelated_current_config(self):
        repo = self.make_repo()
        secret = "legacy-token-must-never-appear"
        (repo / ".dev-flow.json").write_text(
            json.dumps(
                {
                    "workflow": {
                        "methodology_profile": secret,
                        "provider_selectors": {"secret": secret},
                    },
                    "credentials": {"token": secret},
                }
            )
            + "\n"
        )
        lock = repo / ".planning" / "devflow" / "providers.lock.json"
        lock.parent.mkdir(parents=True)
        lock.write_text(json.dumps({"providers": {secret: {"token": secret}}}) + "\n")

        result = self.module().inspect_legacy_workflow_config(repo)
        rendered = json.dumps(result, sort_keys=True)

        self.assertNotIn(secret, rendered)
        self.assertEqual(
            result["targetConfiguration"],
            {"projectContract": 2, "workflow": {"mode": "full-openspec"}},
        )
        self.assertTrue(result["valuesRedacted"])

    def test_broken_config_symlink_is_reported_as_conflict_without_target_read(self):
        repo = self.make_repo()
        (repo / ".dev-flow.json").symlink_to(repo / "missing-secret-config.json")

        result = self.module().inspect_legacy_workflow_config(repo)

        self.assertEqual(result["status"], "manual_review_required")
        self.assertFalse(result["ok"])
        self.assertIn(
            {"path": ".dev-flow.json", "reason": "config_not_regular_file"},
            result["conflicts"],
        )

    def test_inventories_legacy_hooks_agents_runtime_state_and_planning_history(self):
        repo = self.make_repo()
        secret = "hook-token-must-never-appear"
        hooks_config = repo / ".codex" / "hooks.json"
        hooks_config.parent.mkdir(parents=True)
        hooks_config.write_text(
            json.dumps(
                {
                    "hooks": {
                        "SessionStart": [
                            {"command": f"node .codex/hooks/gsd-check-update.js --token {secret}"}
                        ]
                    }
                }
            )
            + "\n"
        )
        hook = repo / ".codex" / "hooks" / "gsd-check-update.js"
        hook.parent.mkdir()
        hook.write_text(f"// {secret}\n")
        superpowers_hook = repo / ".codex" / "hooks" / "superpowers-session-start.sh"
        superpowers_hook.write_text(f"# {secret}\n")
        install_state = repo / ".codex" / "gsd-install-state.json"
        install_state.write_text(json.dumps({"token": secret}) + "\n")
        journal = repo / ".codex" / "gsd-migration-journal" / "entry.json"
        journal.parent.mkdir()
        journal.write_text(json.dumps({"token": secret}) + "\n")
        agent = repo / ".codex" / "agents" / "gsd-code-reviewer.md"
        agent.parent.mkdir()
        agent.write_text(f"# locally edited {secret}\n")
        planning = repo / ".planning" / "config.json"
        planning.parent.mkdir()
        planning.write_text(json.dumps({"token": secret}) + "\n")
        before = self.snapshot(repo)

        result = self.module().inspect_legacy_workflow_config(repo)
        by_path = {item["path"]: item for item in result["artifacts"]}
        rendered = json.dumps(result, sort_keys=True)

        self.assertEqual(self.snapshot(repo), before)
        self.assertNotIn(secret, rendered)
        self.assertEqual(by_path[".codex/hooks.json"]["classification"], "preserved_unknown")
        self.assertEqual(
            by_path[".codex/hooks/gsd-check-update.js"]["classification"],
            "preserved_unknown",
        )
        self.assertEqual(
            by_path[".codex/hooks/superpowers-session-start.sh"]["classification"],
            "preserved_unknown",
        )
        self.assertEqual(
            by_path[".codex/gsd-install-state.json"]["classification"],
            "generated_candidate",
        )
        self.assertEqual(
            by_path[".codex/gsd-migration-journal"]["classification"],
            "user_history_data",
        )
        self.assertEqual(
            by_path[".codex/agents/gsd-code-reviewer.md"]["classification"],
            "preserved_unknown",
        )
        self.assertEqual(by_path[".planning/config.json"]["classification"], "user_history_data")

    def test_inventories_legacy_agent_registrations_in_codex_config_without_values(self):
        repo = self.make_repo()
        secret = "agent-secret-must-never-appear"
        config = repo / ".codex" / "config.toml"
        config.parent.mkdir(parents=True)
        config.write_text(
            "[agents.gsd-planner]\n"
            'description = "legacy planner"\n'
            'config_file = "agents/gsd-planner.toml"\n'
            f'token = "{secret}"\n'
        )
        before = self.snapshot(repo)

        first = self.module().inspect_legacy_workflow_config(repo)
        second = self.module().inspect_legacy_workflow_config(repo)
        rendered = json.dumps(first, sort_keys=True)
        by_path = {item["path"]: item for item in first["artifacts"]}

        self.assertEqual(first, second)
        self.assertEqual(self.snapshot(repo), before)
        self.assertNotIn(secret, rendered)
        self.assertEqual(
            by_path[".codex/config.toml"]["classification"],
            "preserved_unknown",
        )
        self.assertEqual(
            by_path[".codex/config.toml"]["kind"],
            "legacy_agent_config",
        )

    def test_rejects_nonregular_or_unreadable_codex_config_without_following_it(self):
        symlink_repo = self.make_repo()
        config = symlink_repo / ".codex" / "config.toml"
        config.parent.mkdir(parents=True)
        config.symlink_to(symlink_repo / "missing-config.toml")

        symlink_result = self.module().inspect_legacy_workflow_config(symlink_repo)

        self.assertIn(
            {
                "path": ".codex/config.toml",
                "reason": "legacy_agent_config_not_regular_file",
            },
            symlink_result["conflicts"],
        )

        unreadable_repo = self.make_repo()
        unreadable = unreadable_repo / ".codex" / "config.toml"
        unreadable.parent.mkdir(parents=True)
        unreadable.write_bytes(b"\xff\xfe\x00")

        unreadable_result = self.module().inspect_legacy_workflow_config(unreadable_repo)

        self.assertIn(
            {
                "path": ".codex/config.toml",
                "reason": "legacy_agent_config_unreadable:UnicodeDecodeError",
            },
            unreadable_result["conflicts"],
        )

    def test_rejects_symlinked_legacy_parent_without_reading_external_content(self):
        repo = self.make_repo()
        external = self.make_repo()
        secret = "external-legacy-secret-must-not-be-read"
        (external / "config.toml").write_text(f"token = {secret!r}\n")
        hooks = external / "hooks"
        hooks.mkdir()
        (hooks / "gsd-external.sh").write_text(secret)
        (repo / ".codex").symlink_to(external, target_is_directory=True)
        before_repo = self.snapshot(repo)
        before_external = self.snapshot(external)

        result = self.module().inspect_legacy_workflow_config(repo)
        rendered = json.dumps(result, sort_keys=True)

        self.assertEqual(self.snapshot(repo), before_repo)
        self.assertEqual(self.snapshot(external), before_external)
        self.assertNotIn(secret, rendered)
        self.assertIn(
            {"path": ".codex", "reason": "legacy_path_parent_untrusted"},
            result["conflicts"],
        )


if __name__ == "__main__":
    unittest.main()
