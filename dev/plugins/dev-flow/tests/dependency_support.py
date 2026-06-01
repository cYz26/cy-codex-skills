import json
import subprocess
import sys
import tempfile
from pathlib import Path


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
    def make_codex_home(self, *, enable_plugin_eval=True, enable_superpowers_plugin=False):
        home = Path(tempfile.mkdtemp(prefix="cpo-codex-home-"))
        config_lines = ['model = "gpt-5"']
        self.add_plugin_config(config_lines, PLUGIN_ID, False)
        self.add_plugin_config(config_lines, "superpowers", enable_superpowers_plugin)
        self.add_plugin_config(config_lines, "plugin-eval", enable_plugin_eval)
        (home / "config.toml").write_text("\n".join(config_lines) + "\n")
        self.write_required_skills(home, enable_plugin_eval)
        return home

    def add_plugin_config(self, config_lines, plugin, enabled):
        if enabled:
            config_lines.extend(["", f'[plugins."{plugin}@openai-curated"]', "enabled = true"])
        if plugin == PLUGIN_ID and enabled:
            config_lines[-2] = f'[plugins."{PLUGIN_ID}@agents-dev-local"]'

    def write_required_skills(self, home, enable_plugin_eval):
        for skill in ["brainstorming", "writing-plans", "test-driven-development", "verification-before-completion"]:
            self.write_skill(home, "superpowers", skill)
        if enable_plugin_eval:
            self.write_skill(home, "plugin-eval", "evaluate-plugin")

    def write_skill(self, home, plugin, skill):
        path = home / "plugins" / "cache" / "openai-curated" / plugin / "local" / "skills" / skill / "SKILL.md"
        path.parent.mkdir(parents=True)
        path.write_text(f"---\nname: {skill}\ndescription: fixture\n---\n")

    def make_project_repo(
        self,
        *,
        enable_orchestrator=True,
        enable_superpowers=True,
        enable_legacy_openspec_skills=True,
        enable_openspec_config=True,
    ):
        repo = Path(tempfile.mkdtemp(prefix="cpo-project-"))
        (repo / ".codex").mkdir()
        (repo / ".codex" / "config.toml").write_text('model = "gpt-5"\n')
        if enable_openspec_config:
            (repo / "openspec").mkdir()
            (repo / "openspec" / "config.yaml").write_text("schema: spec-driven\n")
        self.write_project_skills(repo, enable_orchestrator, enable_superpowers, enable_legacy_openspec_skills)
        self.write_gsd_agents(repo)
        return repo

    def write_project_skills(
        self,
        repo,
        enable_orchestrator=True,
        enable_superpowers=True,
        enable_legacy_openspec_skills=True,
    ):
        skills = [
            "gsd-new-project",
            "gsd-discuss-phase",
            "gsd-plan-phase",
            "gsd-execute-phase",
            "gsd-progress",
            "gsd-verify-work",
        ]
        if enable_legacy_openspec_skills:
            skills.extend(
                [
                    "openspec-propose",
                    "openspec-explore",
                    "openspec-apply-change",
                    "openspec-archive-change",
                ]
            )
        if enable_superpowers:
            skills.extend(
                [
                    "brainstorming",
                    "writing-plans",
                    "test-driven-development",
                    "verification-before-completion",
                ]
            )
        if enable_orchestrator:
            skills.extend(
                [
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
                    "context-tool-audit",
                    "plugin-project-migration",
                ]
            )
        for skill in skills:
            path = repo / ".codex" / "skills" / skill / "SKILL.md"
            path.parent.mkdir(parents=True)
            path.write_text(f"---\nname: {skill}\ndescription: fixture\n---\n")

    def write_gsd_agents(self, repo):
        for agent in ["gsd-phase-researcher", "gsd-planner", "gsd-plan-checker", "gsd-executor"]:
            path = repo / ".codex" / "agents" / f"{agent}.toml"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"name = \"{agent}\"\n")
