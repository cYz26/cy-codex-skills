import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from workflow_dependency_catalog import OPENSPEC_WORKFLOW_SKILLS
from workflow_legacy_uninstall import inspect_legacy_workflow_uninstall


class LegacyWorkflowUninstallTests(unittest.TestCase):
    def make_repo(self) -> Path:
        repo = Path(tempfile.mkdtemp(prefix="devflow-legacy-uninstall-"))
        (repo / ".dev-flow.json").write_text(
            json.dumps({"projectContract": 2, "workflow": {"mode": "full-openspec"}})
            + "\n"
        )
        return repo

    def write(self, repo: Path, relative: str, content: str) -> Path:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def write_json(self, repo: Path, relative: str, payload: object) -> Path:
        return self.write(repo, relative, json.dumps(payload, indent=2) + "\n")

    def snapshot(self, repo: Path) -> list[tuple[str, str, str]]:
        result: list[tuple[str, str, str]] = []
        for path in sorted(repo.rglob("*")):
            relative = path.relative_to(repo).as_posix()
            if path.is_symlink():
                result.append((relative, "symlink", os.readlink(path)))
            elif path.is_file():
                result.append((relative, "file", hashlib.sha256(path.read_bytes()).hexdigest()))
            else:
                result.append((relative, "directory", ""))
        return result

    def install_official_openspec(self, repo: Path, version: str = "1.7.0") -> None:
        for skill in OPENSPEC_WORKFLOW_SKILLS:
            self.write(
                repo,
                f".agents/skills/{skill}/SKILL.md",
                f"---\nname: {skill}\ngeneratedBy: \"{version}\"\nallowed-tools: Bash(openspec:*)\n---\n",
            )

    def test_classifies_exact_active_capabilities_without_writes(self):
        repo = self.make_repo()
        manifest_files = {
            "skills/gsd-help/SKILL.md": "# generated gsd help\n",
            "gsd-core/VERSION": "1.6.1\n",
            "agents/gsd-planner.toml": "name = \"gsd-planner\"\n",
            "scripts/fix-slash-commands.cjs": "// gsd script\n",
        }
        for relative, content in manifest_files.items():
            target = (
                f".agents/{relative}"
                if relative.startswith("skills/")
                else f".codex/{relative}"
            )
            self.write(repo, target, content)
        self.write_json(
            repo,
            ".codex/gsd-file-manifest.json",
            {
                "version": "1.6.1",
                "mode": "full",
                "files": {
                    relative: hashlib.sha256(content.encode()).hexdigest()
                    for relative, content in manifest_files.items()
                },
            },
        )
        self.write_json(repo, ".codex/gsd-install-state.json", {"schemaVersion": 1})
        self.write_json(repo, ".codex/package.json", {"name": "@opengsd/gsd-core"})
        self.write(
            repo,
            ".codex/config.toml",
            "# GSD Agent Configuration — managed by gsd-core installer\n"
            "[features]\nhooks = true\n\n[agents.gsd-planner]\n"
            "config_file = \".codex/agents/gsd-planner.toml\"\n",
        )
        self.write(
            repo,
            ".codex/hooks/gsd-context-monitor.js",
            "// GSD context monitor\n",
        )
        self.write_json(
            repo,
            ".codex/hooks.json",
            {
                "hooks": {
                    "Stop": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "node .codex/hooks/gsd-context-monitor.js",
                                }
                            ]
                        }
                    ]
                }
            },
        )
        superpowers = repo / ".agents/skills/brainstorming"
        superpowers.parent.mkdir(parents=True, exist_ok=True)
        superpowers.symlink_to(
            "/tmp/superpowers-dev/superpowers/6.0.3/skills/brainstorming",
            target_is_directory=True,
        )
        self.install_official_openspec(repo)
        for skill in OPENSPEC_WORKFLOW_SKILLS:
            self.write(
                repo,
                f".codex/skills/{skill}/SKILL.md",
                f"---\nname: {skill}\ngeneratedBy: \"1.6.0\"\n---\n",
            )
        self.write(repo, ".codex/gsd-migration-journal/old.json", "{}\n")
        self.write(repo, ".codex/gsd-local-patches/skills/gsd-help/SKILL.md", "# patch\n")
        self.write(repo, ".planning/ROADMAP.md", "# history\n")
        before = self.snapshot(repo)

        first = inspect_legacy_workflow_uninstall(repo)
        second = inspect_legacy_workflow_uninstall(repo)

        self.assertEqual(first, second)
        self.assertEqual(self.snapshot(repo), before)
        self.assertTrue(first["readOnly"])
        self.assertEqual(first["status"], "cleanup_available")
        candidates = {item["path"]: item for item in first["candidates"]}
        self.assertEqual(candidates[".agents/skills/gsd-help"]["selectionGroup"], "legacy-gsd")
        self.assertEqual(
            candidates[".agents/skills/brainstorming"]["selectionGroup"],
            "legacy-superpowers",
        )
        self.assertEqual(
            candidates[".codex/skills/openspec-propose"]["authorization"],
            "legacy-skill-layout-cleanup",
        )
        self.assertIn(".codex/config.toml", candidates)
        self.assertIn(".codex/hooks.json", candidates)
        self.assertIn(".codex/hooks/gsd-context-monitor.js", candidates)
        self.assertIn(".codex/gsd-core", candidates)
        self.assertIn(".codex/gsd-file-manifest.json", candidates)
        self.assertIn(".codex/gsd-install-state.json", candidates)
        self.assertIn(".codex/package.json", candidates)
        self.assertIn(".codex/gsd-migration-journal", first["preservedPaths"])
        self.assertIn(".codex/gsd-local-patches", first["preservedPaths"])
        self.assertIn(".planning/ROADMAP.md", first["preservedPaths"])
        self.assertEqual(first["manualActions"], [])

    def test_modified_gsd_skill_is_quarantinable_but_mixed_config_is_manual(self):
        repo = self.make_repo()
        original = "# generated\n"
        self.write(repo, ".agents/skills/gsd-help/SKILL.md", "# locally adapted\n")
        self.write_json(
            repo,
            ".codex/gsd-file-manifest.json",
            {
                "version": "1.6.1",
                "files": {
                    "skills/gsd-help/SKILL.md": hashlib.sha256(original.encode()).hexdigest()
                },
            },
        )
        self.write(
            repo,
            ".codex/config.toml",
            "# GSD Agent Configuration — managed by gsd-core installer\n"
            "[agents.gsd-planner]\nconfig_file = \"gsd.toml\"\n\n"
            "[agents.custom-reviewer]\nconfig_file = \"custom.toml\"\n",
        )

        result = inspect_legacy_workflow_uninstall(repo)

        by_path = {item["path"]: item for item in result["candidates"]}
        self.assertEqual(
            by_path[".agents/skills/gsd-help"]["reason"],
            "recognized_gsd_tree_with_manifest_drift",
        )
        self.assertNotIn(".codex/config.toml", by_path)
        manual = {item["path"]: item for item in result["manualActions"]}
        self.assertEqual(manual[".codex/config.toml"]["reason"], "mixed_gsd_config_ownership")
        self.assertEqual(result["status"], "manual_review_required")

    def test_unattested_superpowers_copy_and_unverified_legacy_openspec_are_preserved(self):
        repo = self.make_repo()
        self.write(repo, ".agents/skills/brainstorming/SKILL.md", "# unrelated local skill\n")
        self.write(
            repo,
            ".agents/skills/using-superpowers/SKILL.md",
            "---\nname: using-superpowers\n---\n# unrelated local skill\n",
        )
        self.install_official_openspec(repo, version="1.6.0")
        self.write(
            repo,
            ".codex/skills/openspec-propose/SKILL.md",
            "---\nname: openspec-propose\ngeneratedBy: \"1.6.0\"\n---\n",
        )

        result = inspect_legacy_workflow_uninstall(repo)

        self.assertEqual(result["candidates"], [])
        manual = {item["path"]: item for item in result["manualActions"]}
        self.assertEqual(
            manual[".agents/skills/brainstorming"]["reason"],
            "superpowers_ownership_unattested",
        )
        self.assertEqual(
            manual[".agents/skills/using-superpowers"]["reason"],
            "superpowers_ownership_unattested",
        )
        self.assertEqual(
            manual[".codex/skills/openspec-propose"]["reason"],
            "official_openspec_skill_set_unverified",
        )


if __name__ == "__main__":
    unittest.main()
