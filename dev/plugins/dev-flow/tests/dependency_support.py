import hashlib
import importlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = next(
    path for path in [PLUGIN_ROOT, *PLUGIN_ROOT.parents] if (path / ".agents" / "plugins" / "marketplace.json").exists()
) / ".agents" / "plugins" / "marketplace.json"
REPO_ROOT = MARKETPLACE.parents[2]
DEV_MARKETPLACE = REPO_ROOT / ".agents" / "plugins" / "marketplace.dev.json"
RELEASE_PLUGIN_ROOT = REPO_ROOT / "plugins" / "dev-flow"
PLUGIN_ID = "dev-flow"


def run_json(name, *args):
    result = subprocess.run(
        [sys.executable, str(PLUGIN_ROOT / "scripts" / name), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"{name} failed with {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return json.loads(result.stdout)


class DependencyFixtureMixin:
    def setUp(self):
        profiles = importlib.import_module("workflow_provider_profiles")
        original = profiles.trusted_provider_sources

        def trusted_test_sources(provider):
            records = original(provider)
            if provider == "superpowers":
                fixture_hashes = {
                    skill: hashlib.sha256(self.skill_fixture_text(skill).encode()).hexdigest()
                    for record in records
                    for skill in record.get("skillHashes", {})
                }
                return [
                    record
                    if record.get("source_channel") == "openai-curated-remote"
                    else {
                        **record,
                        "skillHashes": dict(fixture_hashes),
                        "hookPolicy": {"mode": "hookless"},
                        "manifestSha256": hashlib.sha256(
                            json.dumps(
                                {
                                    "name": "superpowers",
                                    "version": str(record.get("version")),
                                    "skills": "./skills/",
                                }
                            ).encode()
                        ).hexdigest(),
                    }
                    for record in records
                ]
            if provider == "gsd":
                digest = hashlib.sha256(self.gsd_tools_fixture_text().encode()).hexdigest()
                return [{**record, "runtimeSha256": digest} for record in records]
            return records

        patcher = mock.patch.object(profiles, "trusted_provider_sources", side_effect=trusted_test_sources)
        patcher.start()
        self.addCleanup(patcher.stop)

    def skill_fixture_text(self, skill):
        return f"---\nname: {skill}\ndescription: fixture\n---\n"

    def make_codex_home(
        self,
        *,
        enable_plugin_eval=True,
        enable_superpowers_plugin=False,
        install_superpowers=True,
        superpowers_version="6.1.1",
        superpowers_channel="openai-curated-remote",
        superpowers_hooks=None,
    ):
        home = Path(tempfile.mkdtemp(prefix="cpo-codex-home-"))
        config_lines = ['model = "gpt-5"']
        self.add_plugin_config(config_lines, PLUGIN_ID, False)
        self.add_plugin_config(config_lines, "superpowers", enable_superpowers_plugin)
        self.add_plugin_config(config_lines, "plugin-eval", enable_plugin_eval)
        (home / "config.toml").write_text("\n".join(config_lines) + "\n")
        if install_superpowers:
            self.write_required_skills(
                home,
                enable_plugin_eval,
                superpowers_version=superpowers_version,
                superpowers_channel=superpowers_channel,
                superpowers_hooks=superpowers_hooks,
            )
        elif enable_plugin_eval:
            self.write_skill(home, "plugin-eval", "evaluate-plugin")
            self.write_plugin_manifest(home, "plugin-eval", version="0.1.0")
        return home

    def add_plugin_config(self, config_lines, plugin, enabled):
        if enabled:
            config_lines.extend(["", f'[plugins."{plugin}@openai-curated"]', "enabled = true"])
        if plugin == PLUGIN_ID and enabled:
            config_lines[-2] = f'[plugins."{PLUGIN_ID}@agents-dev-local"]'

    def write_required_skills(
        self,
        home,
        enable_plugin_eval,
        *,
        superpowers_version="6.1.1",
        superpowers_channel="openai-curated-remote",
        superpowers_hooks=None,
    ):
        skills = [
            "using-superpowers",
            "brainstorming",
            "writing-plans",
            "test-driven-development",
            "systematic-debugging",
            "requesting-code-review",
            "verification-before-completion",
        ]
        if superpowers_channel == "openai-curated-remote" and superpowers_version == "6.1.1":
            skills.extend(
                [
                    "receiving-code-review",
                    "executing-plans",
                    "subagent-driven-development",
                    "using-git-worktrees",
                    "finishing-a-development-branch",
                ]
            )
        for skill in skills:
            self.write_skill(home, "superpowers", skill, channel=superpowers_channel)
        self.write_plugin_manifest(
            home,
            "superpowers",
            version=superpowers_version,
            channel=superpowers_channel,
            hooks=superpowers_hooks,
        )
        if enable_plugin_eval:
            self.write_skill(home, "plugin-eval", "evaluate-plugin")
            self.write_plugin_manifest(home, "plugin-eval", version="0.1.0")

    def write_skill(self, home, plugin, skill, *, channel="openai-curated"):
        path = home / "plugins" / "cache" / channel / plugin / "local" / "skills" / skill / "SKILL.md"
        canonical = (
            PLUGIN_ROOT
            / "fixtures"
            / "provider-profiles"
            / "strict-superpowers"
            / ".agents"
            / "skills"
            / skill
        )
        if plugin == "superpowers" and channel == "openai-curated-remote" and canonical.is_dir():
            shutil.copytree(canonical, path.parent, dirs_exist_ok=True)
            return
        path.parent.mkdir(parents=True)
        path.write_text(self.skill_fixture_text(skill))

    def write_plugin_manifest(self, home, plugin, *, version, channel="openai-curated", hooks=None):
        root = home / "plugins" / "cache" / channel / plugin / "local"
        manifest = root / ".codex-plugin" / "plugin.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        canonical_manifest = (
            PLUGIN_ROOT
            / "fixtures"
            / "provider-profiles"
            / "strict-superpowers"
            / "codex-home"
            / "plugins"
            / "cache"
            / "openai-curated-remote"
            / "superpowers"
            / "6.1.1"
            / ".codex-plugin"
            / "plugin.json"
        )
        if (
            plugin == "superpowers"
            and channel == "openai-curated-remote"
            and version == "6.1.1"
            and hooks is None
            and canonical_manifest.is_file()
        ):
            shutil.copy2(canonical_manifest, manifest)
            return root
        payload = {"name": plugin, "version": version, "skills": "./skills/"}
        if hooks:
            payload["hooks"] = hooks
            hooks_path = root / hooks
            hooks_path.parent.mkdir(parents=True, exist_ok=True)
            hooks_path.write_text(
                '{"hooks":{"SessionStart":[{"hooks":[{"type":"command","command":"echo bootstrap"}]}]}}\n'
            )
        manifest.write_text(json.dumps(payload))
        return root

    def make_project_repo(
        self,
        *,
        enable_orchestrator=True,
        enable_superpowers=False,
        enable_gsd=False,
        enable_legacy_openspec_skills=True,
        enable_openspec_config=True,
        skill_layout="official",
        methodology_profile="core",
        roadmap_provider="none",
        provider_selectors=None,
    ):
        repo = Path(tempfile.mkdtemp(prefix="cpo-project-"))
        (repo / ".codex").mkdir()
        (repo / ".codex" / "config.toml").write_text('model = "gpt-5"\n')
        if enable_openspec_config:
            (repo / "openspec").mkdir()
            (repo / "openspec" / "config.yaml").write_text("schema: spec-driven\n")
        self.write_project_skills(
            repo,
            enable_orchestrator,
            enable_superpowers,
            enable_legacy_openspec_skills,
            layout=skill_layout,
            enable_gsd=enable_gsd,
        )
        if enable_gsd:
            self.write_gsd_agents(repo)
            self.write_gsd_core_runtime(repo)
        self.write_provider_config(
            repo,
            methodology_profile=methodology_profile,
            roadmap_provider=roadmap_provider,
            provider_selectors=provider_selectors,
        )
        if enable_gsd and roadmap_provider == "gsd":
            manifest_files = json.loads((repo / ".codex" / "gsd-file-manifest.json").read_text())["files"]
            if all(
                f"skills/{skill}/SKILL.md" in manifest_files
                for skill in [
                    "gsd-new-project",
                    "gsd-discuss-phase",
                    "gsd-plan-phase",
                    "gsd-execute-phase",
                    "gsd-progress",
                    "gsd-verify-work",
                ]
            ):
                self.write_gsd_provider_lock(repo)
        return repo

    def write_provider_config(
        self,
        repo,
        *,
        methodology_profile="core",
        roadmap_provider="none",
        provider_selectors=None,
        roadmap_bindings=None,
    ):
        config_path = repo / ".dev-flow.json"
        config_path.write_text(
            json.dumps(
                {
                    "workflow": {
                        "mode": "full-openspec",
                        "methodology_profile": methodology_profile,
                        "roadmap_provider": roadmap_provider,
                        "provider_selectors": provider_selectors or {},
                        "roadmap_bindings": roadmap_bindings or {},
                    }
                },
                indent=2,
            )
            + "\n"
        )

    def write_standalone_skills(self, home, skills):
        for skill in skills:
            path = home / "skills" / skill / "SKILL.md"
            canonical = PLUGIN_ROOT / "fixtures" / "provider-profiles" / "lean-matt" / ".agents" / "skills" / skill
            if canonical.is_dir():
                shutil.copytree(canonical, path.parent, dirs_exist_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(self.skill_fixture_text(skill))

    def write_provider_lock(self, repo, providers):
        path = repo / ".planning" / "devflow" / "providers.lock.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = json.loads(path.read_text()).get("providers", {}) if path.exists() else {}
        path.write_text(
            json.dumps(
                {"schemaVersion": 1, "providers": {**existing, **providers}},
                indent=2,
            )
            + "\n"
        )
        return path

    def write_project_skills(
        self,
        repo,
        enable_orchestrator=True,
        enable_superpowers=True,
        enable_legacy_openspec_skills=True,
        layout="official",
        enable_gsd=True,
    ):
        skills = []
        if enable_gsd:
            skills.extend(
                [
                    "gsd-new-project",
                    "gsd-discuss-phase",
                    "gsd-plan-phase",
                    "gsd-execute-phase",
                    "gsd-progress",
                    "gsd-verify-work",
                ]
            )
        legacy_openspec_skills = [
            "openspec-propose",
            "openspec-explore",
            "openspec-apply-change",
            "openspec-update-change",
            "openspec-sync-specs",
            "openspec-archive-change",
        ]
        if enable_legacy_openspec_skills and layout == "legacy":
            skills.extend(legacy_openspec_skills)
        if enable_superpowers:
            skills.extend(
                [
                    "using-superpowers",
                    "brainstorming",
                    "writing-plans",
                    "test-driven-development",
                    "systematic-debugging",
                    "requesting-code-review",
                    "verification-before-completion",
                ]
            )
        if enable_orchestrator:
            skills.extend(
                [
                    "ai-native-tech-plan",
                    "capability-research",
                    "claude-code-delegate",
                    "project-orchestrator",
                    "project-setup",
                    "feature-intake",
                    "change-plan",
                    "execute-task",
                    "verify-and-archive",
                    "workflow-doctor",
                    "checkpoint-compact",
                    "context-health-check",
                    "context-tool-audit",
                    "codex-updater",
                    "plugin-project-migration",
                    "dev-flow-refresh",
                ]
            )
        for skill in skills:
            path = self.project_skill_path(repo, skill, layout=layout)
            path.parent.mkdir(parents=True)
            path.write_text(f"---\nname: {skill}\ndescription: fixture\n---\n")
        if enable_legacy_openspec_skills and layout != "legacy":
            for skill in legacy_openspec_skills:
                path = self.project_skill_path(repo, skill, layout="legacy")
                path.parent.mkdir(parents=True)
                path.write_text(f"---\nname: {skill}\ndescription: fixture\n---\n")

    def project_skill_root(self, repo, layout="official"):
        if layout == "official":
            return repo / ".agents" / "skills"
        if layout == "legacy":
            return repo / ".codex" / "skills"
        raise ValueError(f"unknown skill layout: {layout}")

    def project_skill_path(self, repo, skill, layout="official"):
        return self.project_skill_root(repo, layout) / skill / "SKILL.md"

    def write_gsd_agents(self, repo):
        for agent in ["gsd-phase-researcher", "gsd-planner", "gsd-plan-checker", "gsd-executor"]:
            path = repo / ".codex" / "agents" / f"{agent}.toml"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"name = \"{agent}\"\n")

    def write_gsd_core_runtime(self, repo, version="1.6.1"):
        runtime = repo / ".codex" / "gsd-core"
        (runtime / "bin").mkdir(parents=True, exist_ok=True)
        (runtime / "VERSION").write_text(f"{version}\n")
        tools = runtime / "bin" / "gsd-tools.cjs"
        tools.write_text(self.gsd_tools_fixture_text())
        tools.chmod(0o755)
        files = {}
        for skill in [
            "gsd-new-project",
            "gsd-discuss-phase",
            "gsd-plan-phase",
            "gsd-execute-phase",
            "gsd-progress",
            "gsd-verify-work",
        ]:
            path = repo / ".agents" / "skills" / skill / "SKILL.md"
            if path.is_file():
                files[f"skills/{skill}/SKILL.md"] = hashlib.sha256(path.read_bytes()).hexdigest()
        for agent in [
            "gsd-phase-researcher.toml",
            "gsd-planner.toml",
            "gsd-plan-checker.toml",
            "gsd-executor.toml",
        ]:
            path = repo / ".codex" / "agents" / agent
            if path.is_file():
                files[f"agents/{agent}"] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest = repo / ".codex" / "gsd-file-manifest.json"
        manifest.write_text(json.dumps({"version": version, "files": files}, sort_keys=True) + "\n")

    def write_gsd_provider_lock(self, repo):
        runtime = repo / ".codex" / "gsd-core" / "bin" / "gsd-tools.cjs"
        manifest = repo / ".codex" / "gsd-file-manifest.json"
        content = json.loads(manifest.read_text())
        files = content["files"]
        skill_hashes = {
            skill: files[f"skills/{skill}/SKILL.md"]
            for skill in [
                "gsd-new-project",
                "gsd-discuss-phase",
                "gsd-plan-phase",
                "gsd-execute-phase",
                "gsd-progress",
                "gsd-verify-work",
            ]
        }
        agent_hashes = {
            agent: files[f"agents/{agent}"]
            for agent in [
                "gsd-phase-researcher.toml",
                "gsd-planner.toml",
                "gsd-plan-checker.toml",
                "gsd-executor.toml",
            ]
        }
        install_command = [
            "npx",
            "-y",
            "@opengsd/gsd-core@1.6.1",
            "--codex",
            "--local",
            "--profile=standard",
        ]
        relevant_files = {
            **{f"skills/{skill}/SKILL.md": digest for skill, digest in skill_hashes.items()},
            **{f"agents/{agent}": digest for agent, digest in agent_hashes.items()},
        }
        content_identity = hashlib.sha256(
            json.dumps(
                {"version": content["version"], "files": relevant_files},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        command_digest = hashlib.sha256(
            json.dumps(install_command, separators=(",", ":")).encode()
        ).hexdigest()
        return self.write_provider_lock(
            repo,
            {
                "gsd": {
                    "source_id": "gsd-core-1-6-1",
                    "package": "@opengsd/gsd-core",
                    "sourceRoot": str(runtime.parents[1]),
                    "version": content["version"],
                    "runtimeSha256": hashlib.sha256(runtime.read_bytes()).hexdigest(),
                    "contentIdentitySha256": content_identity,
                    "contentManifestSha256": content_identity,
                    "contentAttestation": {
                        "kind": "authorized-pinned-install",
                        "sourceId": "gsd-core-1-6-1",
                        "installCommandSha256": command_digest,
                    },
                    "skillHashes": skill_hashes,
                    "agentHashes": agent_hashes,
                }
            },
        )

    def gsd_tools_fixture_text(self):
        return (
            "#!/usr/bin/env node\n"
            "const command = process.argv.slice(2);\n"
            "if (command[0] === 'current-timestamp') {\n"
            "  console.log(JSON.stringify({timestamp: '2026-06-14T00:00:00.000Z'}));\n"
            "} else if (command[0] === 'state' && command[1] === 'load') {\n"
            "  console.log(JSON.stringify({ok: true, config: {commit_docs: false}}));\n"
            "} else if (command[0] === 'roadmap' && command[1] === 'validate') {\n"
            "  console.log(JSON.stringify({ok: true, valid: true}));\n"
            "} else if (command[0] === 'roadmap' && command[1] === 'get-phase') {\n"
            "  console.log(JSON.stringify({ok: true, found: true, phase: command[2]}));\n"
            "} else if (command[0] === 'find-phase') {\n"
            "  console.log(JSON.stringify({ok: true, found: true, phase: command[1]}));\n"
            "}\n"
        )
