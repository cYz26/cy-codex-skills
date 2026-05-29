import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
MARKETPLACE = next(
    path for path in [PLUGIN_ROOT, *PLUGIN_ROOT.parents] if (path / ".agents" / "plugins" / "marketplace.json").exists()
) / ".agents" / "plugins" / "marketplace.json"
REPO_ROOT = MARKETPLACE.parents[2]
DEV_MARKETPLACE = REPO_ROOT / ".agents" / "plugins" / "marketplace.dev.json"
RELEASE_PLUGIN_ROOT = REPO_ROOT / "plugins" / "agent-kb"
PROJECT = "agent-kb-project"
KB_SKILLS = {
    "kb-ingest",
    "kb-query",
    "kb-update",
    "kb-compact",
    "kb-lint",
    "kb-reflect",
    "kb-promote",
}


def registered_plugin_path(marketplace_path, plugin_name):
    marketplace = json.loads(marketplace_path.read_text())
    entry = next(item for item in marketplace["plugins"] if item["name"] == plugin_name)
    return (marketplace_path.parents[2] / entry["source"]["path"]).resolve(), entry


def run_script(name, *args, input_text=None, cwd=PLUGIN_ROOT):
    script = SCRIPTS / name
    result = subprocess.run(
        [sys.executable, str(script), *args],
        input=input_text,
        text=True,
        cwd=cwd,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"{name} failed with {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def run_json(name, *args, input_text=None, cwd=PLUGIN_ROOT):
    result = run_script(name, *args, input_text=input_text, cwd=cwd)
    return json.loads(result.stdout)


class AgentKBTests(unittest.TestCase):
    def make_repo_and_vault(self):
        root = Path(tempfile.mkdtemp(prefix="agent-kb-"))
        repo = root / "repo"
        vault = root / "vault"
        repo.mkdir()
        return repo, vault

    def scaffold(self, repo, vault):
        return run_json(
            "kb_scaffold.py",
            "--repo",
            str(repo),
            "--vault",
            str(vault),
            "--project",
            PROJECT,
            "--owner",
            "chanYu",
            "--json",
        )

    def test_manifest_marketplace_assets_and_hooks_are_declared(self):
        manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text())
        self.assertEqual(manifest["name"], "agent-kb")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(manifest["hooks"], "./hooks.json")
        self.assertEqual(manifest["interface"]["displayName"], "AgentKB")
        self.assertEqual(manifest["interface"]["category"], "Coding")
        self.assertTrue((PLUGIN_ROOT / manifest["interface"]["logo"]).exists())
        self.assertTrue((PLUGIN_ROOT / manifest["interface"]["composerIcon"]).exists())
        self.assertTrue((PLUGIN_ROOT / "hooks.json").exists())
        self.assertTrue((PLUGIN_ROOT / "scripts" / "kb_event_hook.py").exists())

        release_path, entry = registered_plugin_path(MARKETPLACE, "agent-kb")
        self.assertEqual(release_path, RELEASE_PLUGIN_ROOT.resolve())
        self.assertEqual(entry["source"]["path"], "./plugins/agent-kb")
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
        self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")

        dev_path, dev_entry = registered_plugin_path(DEV_MARKETPLACE, "agent-kb")
        self.assertEqual(dev_path, PLUGIN_ROOT.resolve())
        self.assertEqual(dev_entry["source"]["path"], "./dev/plugins/agent-kb")

    def test_scaffold_creates_markdown_canonical_vault_and_agent_config(self):
        repo, vault = self.make_repo_and_vault()

        report = self.scaffold(repo, vault)

        self.assertEqual(report["project"], PROJECT)
        self.assertTrue(report["configured"])
        self.assertGreater(len(report["written"]), 15)
        for relative in [
            "AGENTS.md",
            ".gitignore",
            "10-wiki/index.md",
            "10-wiki/log.md",
            f"20-projects/{PROJECT}/overview.md",
            f"20-projects/{PROJECT}/current-state.md",
            f"20-projects/{PROJECT}/architecture.md",
            f"20-projects/{PROJECT}/decisions.md",
            f"20-projects/{PROJECT}/open-questions.md",
            f"20-projects/{PROJECT}/context-pack.md",
            "40-decisions/adr-0001-use-markdown-as-canonical-kb.md",
            "40-decisions/adr-0002-use-context-pack.md",
            "50-playbooks/kb-ingest.md",
            "50-playbooks/kb-update.md",
            "50-playbooks/kb-lint.md",
            f"60-context-packs/{PROJECT}.md",
            "70-agent-logs",
            "80-bases/Projects.base",
            "80-bases/Decisions.base",
            "80-bases/Research.base",
            "80-bases/ContextPacks.base",
            "80-bases/OpenQuestions.base",
        ]:
            self.assertTrue((vault / relative).exists(), relative)

        config = json.loads((repo / ".agent-kb.json").read_text())
        self.assertEqual(Path(config["vault"]).resolve(), vault.resolve())
        self.assertEqual(config["project"], PROJECT)
        self.assertEqual(config["storage_adapter"], "markdown-filesystem")
        self.assertEqual(config["editor_profile"], "obsidian-compatible-markdown")
        self.assertEqual(config["agent_adapter"], "codex")
        self.assertFalse((repo / ".codex" / "obsidian-kb.json").exists())

        agents = (vault / "AGENTS.md").read_text()
        self.assertIn("Markdown is the canonical durable storage", agents)
        self.assertIn("Obsidian is an editor profile", agents)
        self.assertIn("Codex is one agent adapter", agents)

        context_pack = vault / "20-projects" / PROJECT / "context-pack.md"
        text = context_pack.read_text()
        self.assertTrue(text.startswith("---\n"))
        for required in [
            "type: context-pack",
            f"project: {PROJECT}",
            "confidence: high",
            "agent_readable: true",
        ]:
            self.assertIn(required, text)

        context_pack.write_text(text + "\nManual edit that must survive scaffold reruns.\n")
        second = self.scaffold(repo, vault)
        self.assertIn(f"20-projects/{PROJECT}/context-pack.md", second["skipped"])
        self.assertIn("Manual edit that must survive scaffold reruns.", context_pack.read_text())

    def test_lint_reports_health_and_writes_reviewable_report(self):
        repo, vault = self.make_repo_and_vault()
        self.scaffold(repo, vault)

        clean = run_json("kb_lint.py", "--vault", str(vault), "--project", PROJECT, "--json")

        self.assertTrue(clean["ok"], clean)
        self.assertEqual(clean["blocking_findings"], 0)
        self.assertEqual(clean["finding_count"], 0)
        self.assertTrue(clean["context_pack"].endswith(f"20-projects/{PROJECT}/context-pack.md"))

        bad_note = vault / "10-wiki" / "concepts" / "missing-frontmatter.md"
        bad_note.parent.mkdir(parents=True, exist_ok=True)
        bad_note.write_text("# Missing Frontmatter\n")

        report = run_json("kb_lint.py", "--vault", str(vault), "--project", PROJECT, "--write-report", "--json")

        findings = {(item["rule"], item["path"]) for item in report["findings"]}
        self.assertIn(("missing-frontmatter", "10-wiki/concepts/missing-frontmatter.md"), findings)
        report_path = vault / report["report_path"]
        self.assertTrue(report_path.exists(), report)
        self.assertTrue(report["report_path"].startswith(f"20-projects/{PROJECT}/proposed-changes/"))

    def test_event_hook_noops_and_records_agent_kb_or_legacy_configs(self):
        repo, vault = self.make_repo_and_vault()
        payload = {
            "cwd": str(repo),
            "prompt": "SECRET_PROMPT_TEXT",
            "tool_name": "Bash",
            "tool_input": {"command": "python3 -m unittest tests/test_example.py token=SECRET_TOKEN"},
            "tool_response": {"exit_code": 1, "output": "SECRET_OUTPUT_BODY\nline2"},
        }

        noop = run_json(
            "kb_event_hook.py",
            "--event",
            "user_prompt_submit",
            "--json",
            input_text=json.dumps(payload),
        )

        self.assertFalse(noop["recorded"])
        self.assertFalse((vault / ".agent-kb" / "events").exists())

        (repo / ".agent-kb.json").write_text(
            json.dumps(
                {
                    "enabled": True,
                    "vault": str(vault),
                    "project": PROJECT,
                    "storage_adapter": "markdown-filesystem",
                    "editor_profile": "obsidian-compatible-markdown",
                    "agent_adapter": "codex",
                }
            )
        )
        written = run_json(
            "kb_event_hook.py",
            "--event",
            "post_tool_use",
            "--json",
            input_text=json.dumps(payload),
        )

        self.assertTrue(written["recorded"], written)
        self.assertTrue(written["path"].startswith(".agent-kb/events/"), written)
        event_path = vault / written["path"]
        raw = event_path.read_text()
        self.assertNotIn("SECRET_PROMPT_TEXT", raw)
        self.assertNotIn("SECRET_OUTPUT_BODY", raw)
        self.assertNotIn("SECRET_TOKEN", raw)
        event = json.loads(raw.splitlines()[-1])
        self.assertEqual(event["event_type"], "post_tool_use")
        self.assertEqual(event["tool"], "Bash")
        self.assertEqual(event["status"], "fail")
        self.assertEqual(event["output_lines"], 2)

        legacy_repo, legacy_vault = self.make_repo_and_vault()
        legacy_payload = {"cwd": str(legacy_repo), "tool_name": "Read", "tool_response": {"status": "ok"}}
        (legacy_repo / ".codex").mkdir()
        (legacy_repo / ".codex" / "obsidian-kb.json").write_text(
            json.dumps({"enabled": True, "vault": str(legacy_vault), "project": PROJECT})
        )

        legacy = run_json(
            "kb_event_hook.py",
            "--event",
            "post_tool_use",
            "--json",
            input_text=json.dumps(legacy_payload),
        )

        self.assertTrue(legacy["recorded"], legacy)
        self.assertTrue(legacy["path"].startswith(".agent-kb/events/"), legacy)

    def test_kb_skills_are_packaged_with_markdown_first_safety_rules(self):
        self.assertEqual(KB_SKILLS, {path.name for path in (PLUGIN_ROOT / "skills").iterdir() if path.is_dir()})
        for skill in KB_SKILLS:
            text = (PLUGIN_ROOT / "skills" / skill / "SKILL.md").read_text()
            self.assertTrue(text.startswith("---\n"), skill)
            self.assertIn(f"name: {skill}", text)
            self.assertIn("context-pack", text)
            self.assertIn("Markdown", text)
            self.assertIn("Git diff", text)

if __name__ == "__main__":
    unittest.main()
