import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
LOCAL_ARCHIVE = PLUGIN_ROOT / "scripts" / "devflow_runtime.pyz"
PACKAGED = LOCAL_ARCHIVE.is_file()
if PACKAGED:
    RUNTIME_ARCHIVE = LOCAL_ARCHIVE
    os.environ.setdefault("DEVFLOW_PLUGIN_ROOT", str(PLUGIN_ROOT))
    sys.path.insert(0, str(RUNTIME_ARCHIVE))
else:
    REPO_ROOT = PLUGIN_ROOT.parents[2]
    RUNTIME_ARCHIVE = REPO_ROOT / "plugins" / "dev-flow" / "scripts" / "devflow_runtime.pyz"
    sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))


from workflow_dependency_provenance import default_plugin_root as provenance_plugin_root
from workflow_planning_paths import current_plugin_version
from workflow_provider_profiles import diagnose_provider_selection, resolve_provider_selection
from workflow_dependency_catalog import PROJECT_ORCHESTRATOR_SKILLS
from workflow_routing_matrix import default_plugin_root as routing_plugin_root
from workflow_superpowers_gates import default_plugin_root as gate_plugin_root


def runtime_module_text(name):
    with zipfile.ZipFile(RUNTIME_ARCHIVE) as archive:
        return archive.read(name).decode("utf-8")


def make_core_repo(root, methodology, roadmap):
    repo = root / f"{methodology}-{roadmap}"
    (repo / "openspec").mkdir(parents=True)
    (repo / "openspec" / "config.yaml").write_text("schema: spec-driven\n")
    (repo / ".dev-flow.json").write_text(
        json.dumps(
            {
                "workflow": {
                    "methodology_profile": methodology,
                    "roadmap_provider": roadmap,
                }
            }
        )
    )
    skill_root = repo / ".agents" / "skills"
    skill_root.mkdir(parents=True)
    for skill in PROJECT_ORCHESTRATOR_SKILLS:
        (skill_root / skill).symlink_to(PLUGIN_ROOT / "skills" / skill, target_is_directory=True)
    return repo


class PackagedRuntimeTests(unittest.TestCase):
    def test_provider_defaults(self):
        profiles = json.loads((PLUGIN_ROOT / "docs" / "provider_profiles.json").read_text())

        self.assertEqual(profiles["defaults"]["methodologyProfile"], "core")
        self.assertEqual(profiles["defaults"]["roadmapProvider"], "none")
        self.assertEqual(
            set(profiles["methodologyProfiles"]),
            {"core", "lean-matt", "strict-superpowers"},
        )
        self.assertEqual(set(profiles["roadmapProviders"]), {"none", "gsd"})

    def test_provider_provenance(self):
        provenance = json.loads(
            (PLUGIN_ROOT / "docs" / "dependency-provenance.json").read_text()
        )
        gsd = provenance["providerSources"]["gsd-core-1-6-1"]
        matt = provenance["providerSources"]["mattpocock-skills-v1-1-0"]

        self.assertEqual(gsd["package"], "@opengsd/gsd-core")
        self.assertEqual(gsd["version"], "1.6.1")
        self.assertEqual(matt["ref"], "v1.1.0")
        self.assertEqual(len(matt["skillHashes"]), 6)

    def test_provider_roadmap_matrix(self):
        methodology_providers = {
            "core": [],
            "lean-matt": ["mattpocock-skills"],
            "strict-superpowers": ["superpowers"],
        }
        roadmap_providers = {"none": [], "gsd": ["gsd"]}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / "codex-home"
            home.mkdir()
            for methodology, methodology_selected in methodology_providers.items():
                for roadmap, roadmap_selected in roadmap_providers.items():
                    repo = make_core_repo(root, methodology, roadmap)
                    selection = resolve_provider_selection(repo, home, {})
                    report = diagnose_provider_selection(selection, repo, home)

                    with self.subTest(methodology=methodology, roadmap=roadmap):
                        self.assertTrue(report["coreReady"])
                        self.assertEqual(
                            report["selectedProviders"],
                            methodology_selected + roadmap_selected,
                        )
                        self.assertEqual(report["methodologyReady"], methodology == "core")
                        self.assertEqual(report["roadmapReady"], roadmap == "none")

    def test_runtime_members(self):
        with zipfile.ZipFile(RUNTIME_ARCHIVE) as archive:
            members = set(archive.namelist())

        self.assertIn("workflow_provider_profiles.py", members)
        self.assertIn("workflow_provider_migration.py", members)
        self.assertIn("workflow_roadmap_provider.py", members)
        self.assertIn("workflow_release_sync.py", members)

    def test_runtime_asset_roots(self):
        manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text())

        self.assertEqual(provenance_plugin_root(), PLUGIN_ROOT)
        self.assertEqual(routing_plugin_root(), PLUGIN_ROOT)
        self.assertEqual(gate_plugin_root(), PLUGIN_ROOT)
        self.assertEqual(current_plugin_version(), manifest["version"])

    def test_release_entrypoints(self):
        self.assertTrue((PLUGIN_ROOT / "scripts" / "check_dependencies.py").is_file())
        self.assertTrue((PLUGIN_ROOT / "scripts" / "archive_roadmap_binding.py").is_file())
        self.assertTrue((PLUGIN_ROOT / "scripts" / "verify_release_runtime.py").is_file())

    def test_agent_kb_is_absent(self):
        workflow_lib = runtime_module_text("workflow_lib.py")

        self.assertNotIn("workflow_agent_kb", workflow_lib)
        self.assertNotIn("workflow_obsidian_kb", workflow_lib)
        self.assertNotIn("record_kb_event", workflow_lib)


if __name__ == "__main__":
    unittest.main()
