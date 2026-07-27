import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
LOCAL_ARCHIVE = PLUGIN_ROOT / "scripts" / "devflow_runtime.pyz"
if LOCAL_ARCHIVE.is_file():
    RUNTIME_ARCHIVE = LOCAL_ARCHIVE
    RELEASE_PLUGIN_ROOT = PLUGIN_ROOT
else:
    REPO_ROOT = PLUGIN_ROOT.parents[2]
    RELEASE_PLUGIN_ROOT = REPO_ROOT / "plugins" / "dev-flow"
    RUNTIME_ARCHIVE = RELEASE_PLUGIN_ROOT / "scripts" / "devflow_runtime.pyz"

MATT_SKILLS = (
    "grilling",
    "tdd",
    "diagnosing-bugs",
    "code-review",
    "codebase-design",
    "domain-modeling",
)
CURRENT_RUNTIME_MODULES = {
    "workflow_archive_policy.py",
    "workflow_dependencies.py",
    "workflow_dependency_provenance.py",
    "workflow_generated_artifacts.py",
    "workflow_methodology.py",
    "workflow_planning_paths.py",
    "workflow_project_activation.py",
    "workflow_release_sync.py",
    "workflow_side_effect_policy.py",
}
REMOVED_RUNTIME_MEMBERS = {
    "aggregate_provider_benchmark.py",
    "archive_roadmap_binding.py",
    "run_provider_benchmark.py",
    "superpowers_artifact_mapping.py",
    "workflow_dependency_plugin_checks.py",
    "workflow_provider_activation.py",
    "workflow_provider_deactivation.py",
    "workflow_provider_migration.py",
    "workflow_provider_profiles.py",
    "workflow_provider_registry.py",
    "workflow_roadmap_provider.py",
    "workflow_superpowers_gates.py",
}


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runtime_module_text(name: str) -> str:
    with zipfile.ZipFile(RUNTIME_ARCHIVE) as archive:
        return archive.read(name).decode("utf-8")


class PackagedRuntimeTests(unittest.TestCase):
    def run_lifecycle_cli(self, cli, repo, environment, *arguments):
        return subprocess.run(
            [sys.executable, str(cli), *map(str, arguments)],
            cwd=repo,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def prepare_packaged_lifecycle(self, cli, repo, environment):
        prepared = self.run_lifecycle_cli(
            cli,
            repo,
            environment,
            "prepare",
            "--repo",
            repo,
            "--task-id",
            "packaged-task",
            "--run-id",
            "run-1",
            "--owner-id",
            "main",
            "--owner-pid",
            "999999999",
            "--command-json",
            '["python3","build.py"]',
            "--isolated-root",
            ".devflow-generated/packaged-task/run-1",
        )
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        contract_path = repo / "contract.json"
        contract_path.write_text(prepared.stdout)
        artifact = (
            repo
            / ".devflow-generated"
            / "packaged-task"
            / "run-1"
            / "output.bin"
        )
        artifact.parent.mkdir(parents=True)
        artifact.write_bytes(b"packaged")
        return contract_path, artifact

    def observe_and_plan_packaged_lifecycle(
        self,
        cli,
        repo,
        environment,
        contract_path,
    ):
        observed = self.run_lifecycle_cli(
            cli,
            repo,
            environment,
            "observe",
            "--repo",
            repo,
            "--contract",
            contract_path,
            "--exit-code",
            "0",
        )
        self.assertEqual(observed.returncode, 0, observed.stderr)
        manifest_path = repo / "manifest.json"
        manifest_path.write_text(observed.stdout)
        planned = self.run_lifecycle_cli(
            cli,
            repo,
            environment,
            "plan",
            "--repo",
            repo,
            "--contract",
            contract_path,
            "--manifest",
            manifest_path,
        )
        self.assertEqual(planned.returncode, 0, planned.stderr)
        self.assertEqual(json.loads(planned.stdout)["decision"], "AUTO_CLEAN")
        plan_path = repo / "plan.json"
        plan_path.write_text(planned.stdout)
        return manifest_path, plan_path

    def test_packaged_runtime_imports_current_matt_native_modules(self):
        module_names = sorted(name.removesuffix(".py") for name in CURRENT_RUNTIME_MODULES)
        code = """
import importlib
import json
import sys

archive, *module_names = sys.argv[1:]
sys.path.insert(0, archive)
modules = {name: importlib.import_module(name) for name in module_names}
methodology = modules["workflow_methodology"].methodology_manifest()
print(json.dumps({
    "controlPlane": methodology["controlPlane"],
    "moduleFiles": {name: module.__file__ for name, module in modules.items()},
    "pluginRoot": str(modules["workflow_dependency_provenance"].default_plugin_root()),
    "policyRoot": str(modules["workflow_side_effect_policy"].default_plugin_root()),
    "version": modules["workflow_planning_paths"].current_plugin_version(),
}, sort_keys=True))
"""
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run(
                [sys.executable, "-c", code, str(RUNTIME_ARCHIVE), *module_names],
                cwd=temporary,
                env={
                    **os.environ,
                    "DEVFLOW_PLUGIN_ROOT": str(RELEASE_PLUGIN_ROOT),
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        manifest = json.loads(
            (RELEASE_PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text()
        )
        self.assertEqual(report["controlPlane"], "devflow-openspec")
        self.assertEqual(report["pluginRoot"], str(RELEASE_PLUGIN_ROOT.resolve()))
        self.assertEqual(report["policyRoot"], str(RELEASE_PLUGIN_ROOT.resolve()))
        self.assertEqual(report["version"], manifest["version"])
        for module_file in report["moduleFiles"].values():
            self.assertTrue(
                module_file.startswith(f"{RUNTIME_ARCHIVE}/"),
                module_file,
            )

    def test_packaged_methodology_provenance_and_vendor_resources_are_complete(self):
        provenance = json.loads(
            (RELEASE_PLUGIN_ROOT / "docs" / "dependency-provenance.json").read_text()
        )

        self.assertEqual(provenance["schemaVersion"], 3)
        self.assertNotIn("providerSources", provenance)
        methodology = provenance["methodology"]
        self.assertEqual(methodology["name"], "mattpocock-skills")
        self.assertEqual(methodology["repository"], "mattpocock/skills")
        self.assertEqual(methodology["ref"], "v1.1.0")
        self.assertEqual(
            methodology["commit"],
            "d574778f94cf620fcc8ce741584093bc650a61d3",
        )
        self.assertEqual(
            methodology["installCommand"],
            [
                "npx",
                "-y",
                "skills@1.5.20",
                "add",
                "https://github.com/mattpocock/skills/tree/v1.1.0",
                "--skill",
                "grilling",
                "--skill",
                "tdd",
                "--skill",
                "diagnosing-bugs",
                "--skill",
                "code-review",
                "--skill",
                "codebase-design",
                "--skill",
                "domain-modeling",
                "--agent",
                "codex",
                "--yes",
            ],
        )
        self.assertEqual(
            methodology["runtimeRequirements"],
            {"node": ">=22.20.0"},
        )
        self.assertEqual(tuple(methodology["skillHashes"]), MATT_SKILLS)
        self.assertNotIn("--global", methodology["installCommand"])
        self.assertEqual(
            {item["name"] for item in provenance["dependencies"]},
            {"openspec-cli", "plugin-eval"},
        )

        vendor_root = RELEASE_PLUGIN_ROOT / "vendor" / "mattpocock-skills"
        license_path = RELEASE_PLUGIN_ROOT / methodology["licensePath"]
        self.assertEqual(file_digest(license_path), methodology["licenseSha256"])
        file_hashes = methodology["fileHashes"]
        actual_files = {
            path.relative_to(vendor_root).as_posix()
            for path in vendor_root.rglob("*")
            if path.is_file()
        }
        expected_files = set(file_hashes) | {
            license_path.relative_to(vendor_root).as_posix()
        }
        self.assertEqual(actual_files, expected_files)
        for relative, expected_digest in file_hashes.items():
            path = vendor_root / relative
            self.assertFalse(path.is_symlink(), relative)
            self.assertEqual(file_digest(path), expected_digest, relative)
        for skill, expected_digest in methodology["skillHashes"].items():
            self.assertEqual(file_hashes[f"{skill}/SKILL.md"], expected_digest)

        serialized = json.dumps(provenance, sort_keys=True).lower()
        self.assertNotIn("superpowers", serialized)
        self.assertNotIn("gsd", serialized)

    def test_runtime_archive_contains_current_modules_and_no_removed_provider_modules(self):
        with zipfile.ZipFile(RUNTIME_ARCHIVE) as archive:
            members = set(archive.namelist())

        self.assertTrue(
            CURRENT_RUNTIME_MODULES.issubset(members),
            f"missing current runtime members: {sorted(CURRENT_RUNTIME_MODULES - members)}",
        )
        self.assertTrue(
            REMOVED_RUNTIME_MEMBERS.isdisjoint(members),
            f"obsolete runtime members remain: {sorted(REMOVED_RUNTIME_MEMBERS & members)}",
        )

    def test_current_release_entrypoints_exist(self):
        for relative in (
            "scripts/activate_project_dependencies.py",
            "scripts/check_dependencies.py",
            "scripts/generated_artifact_lifecycle.py",
            "scripts/record_task_evidence.py",
            "scripts/verify_release_runtime.py",
        ):
            with self.subTest(relative=relative):
                self.assertTrue((RELEASE_PLUGIN_ROOT / relative).is_file())

    def test_packaged_generated_artifact_lifecycle_exact_apply_smoke(self):
        cli = RELEASE_PLUGIN_ROOT / "scripts" / "generated_artifact_lifecycle.py"
        with tempfile.TemporaryDirectory(prefix="packaged-artifact-", dir="/tmp") as temporary:
            repo = Path(temporary)
            subprocess.run(
                ["git", "init", "-q"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            )
            preserved = repo / "user-config.json"
            preserved.write_text('{"preserve":true}\n')
            environment = {
                **os.environ,
                "DEVFLOW_PLUGIN_ROOT": str(RELEASE_PLUGIN_ROOT),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            contract_path, artifact = self.prepare_packaged_lifecycle(
                cli,
                repo,
                environment,
            )
            manifest_path, plan_path = self.observe_and_plan_packaged_lifecycle(
                cli,
                repo,
                environment,
                contract_path,
            )
            applied = self.run_lifecycle_cli(
                cli,
                repo,
                environment,
                "cleanup",
                "--repo",
                repo,
                "--contract",
                contract_path,
                "--manifest",
                manifest_path,
                "--plan",
                plan_path,
                "--apply",
            )

            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertEqual(json.loads(applied.stdout)["status"], "complete")
            self.assertFalse(artifact.exists())
            self.assertEqual(preserved.read_text(), '{"preserve":true}\n')

        for relative in (
            "schemas/generated-artifact-contract.schema.json",
            "schemas/generated-artifact-manifest.schema.json",
            "schemas/generated-artifact-cleanup-receipt.schema.json",
            "docs/generated-artifact-lifecycle.md",
            "assets/templates/AGENT_TASK_CONTRACT.md.template",
        ):
            self.assertTrue((RELEASE_PLUGIN_ROOT / relative).is_file(), relative)

    def test_agent_kb_is_absent(self):
        workflow_lib = runtime_module_text("workflow_lib.py")

        self.assertNotIn("workflow_agent_kb", workflow_lib)
        self.assertNotIn("workflow_obsidian_kb", workflow_lib)
        self.assertNotIn("record_kb_event", workflow_lib)


if __name__ == "__main__":
    unittest.main()
