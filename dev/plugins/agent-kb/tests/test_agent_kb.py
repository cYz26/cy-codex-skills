import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
HOOK_SCRIPT_PREFIX = (
    'python3 "${CODEX_HOME:-$HOME/.codex}/plugins/cache/cy-codex-skills/'
    'agent-kb/0.1.0/scripts/'
)
REPO_ROOT = PLUGIN_ROOT.parents[2]
MARKETPLACE = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
DEV_MARKETPLACE = REPO_ROOT / ".agents" / "plugins" / "marketplace.dev.json"
RELEASE_PLUGIN_ROOT = REPO_ROOT / "plugins" / "agent-kb"
PROJECT = "agent-kb-project"
KB_SKILLS = {
    "kb-capture",
    "kb-import",
    "kb-ingest",
    "kb-query",
    "kb-update",
    "kb-compact",
    "kb-lint",
    "kb-reflect",
    "kb-promote",
    "kb-enable-project",
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
        self.assertEqual(manifest["author"]["url"], "https://github.com/cYz26")
        self.assertEqual(manifest["repository"], "https://github.com/cYz26/cy-codex-skills")
        self.assertEqual(
            manifest["homepage"],
            "https://github.com/cYz26/cy-codex-skills/tree/main/plugins/agent-kb",
        )
        self.assertEqual(manifest["interface"]["developerName"], "cY")
        self.assertEqual(manifest["interface"]["websiteURL"], manifest["homepage"])
        self.assertNotIn("github.com/local", json.dumps(manifest))
        self.assertTrue((PLUGIN_ROOT / manifest["interface"]["logo"]).exists())
        self.assertTrue((PLUGIN_ROOT / manifest["interface"]["composerIcon"]).exists())
        self.assertTrue((PLUGIN_ROOT / "hooks.json").exists())
        self.assertTrue((PLUGIN_ROOT / "scripts" / "kb_event_hook.py").exists())
        hooks = json.loads((PLUGIN_ROOT / "hooks.json").read_text())["hooks"]
        hook_commands = [
            hook["command"]
            for group in hooks.values()
            for entry in group
            for hook in entry.get("hooks", [])
        ]
        self.assertTrue(all(command.startswith(HOOK_SCRIPT_PREFIX) for command in hook_commands))
        self.assertFalse(any("./scripts/" in command for command in hook_commands))

        release_path, entry = registered_plugin_path(MARKETPLACE, "agent-kb")
        self.assertEqual(release_path, RELEASE_PLUGIN_ROOT.resolve())
        self.assertEqual(entry["source"]["path"], "./plugins/agent-kb")
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
        self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")

        dev_path, dev_entry = registered_plugin_path(DEV_MARKETPLACE, "agent-kb")
        self.assertEqual(dev_path, PLUGIN_ROOT.resolve())
        self.assertEqual(dev_entry["source"]["path"], "./dev/plugins/agent-kb")

    def assert_scaffold_core_files(self, vault):
        for relative in [
            "AGENTS.md",
            ".gitignore",
            "_system/kb-structure.md",
            "_system/routing-rules.md",
            "_system/metadata-schema.md",
            "_system/write-policy.md",
            "_system/promotion-policy.md",
            "_system/indexes/home.md",
            "_system/indexes/knowledge-index.md",
            "_system/templates/capture.md",
            "_agent/logs",
            "_agent/routing-receipts",
            "_agent/source-intake",
            "_agent/source-intake/extracted",
            "_agent/source-intake/receipts",
            "_agent/problem-signals",
            "_agent/lint-reports",
            "_bases/Inbox.base",
            "_bases/Projects.base",
            "_bases/Knowledge.base",
            "_bases/Promotion.base",
            "calendar/daily",
            "personal/ideas",
            "work/meetings",
            "knowledge/index.md",
            "knowledge/log.md",
            f"projects/{PROJECT}/overview.md",
            f"projects/{PROJECT}/current-state.md",
            f"projects/{PROJECT}/architecture.md",
            f"projects/{PROJECT}/decisions.md",
            f"projects/{PROJECT}/open-questions.md",
            f"projects/{PROJECT}/context-pack.md",
            f"projects/{PROJECT}/candidates",
            f"projects/{PROJECT}/proposed-changes/problem-reflections",
            "decisions/adr-0001-use-markdown-as-canonical-kb.md",
            "decisions/adr-0002-use-context-pack.md",
            "playbooks/kb-ingest.md",
            "playbooks/kb-update.md",
            "playbooks/kb-lint.md",
            "playbooks/kb-reflect.md",
            "playbooks/kb-promote.md",
            f"_agent/context-packs/{PROJECT}.md",
            "promotion/candidates",
            "promotion/sanitized",
            "promotion/reviewed",
            "promotion/exported",
            "promotion/rejected",
            "references/articles",
            "assets/images",
        ]:
            self.assertTrue((vault / relative).exists(), relative)

    def assert_no_numbered_roots(self, vault):
        for numbered_root in [
            "00-inbox",
            "01-raw",
            "10-wiki",
            "20-projects",
            "30-research",
            "40-decisions",
            "50-playbooks",
            "60-context-packs",
            "70-agent-logs",
            "80-bases",
            "90-archive",
        ]:
            self.assertFalse((vault / numbered_root).exists(), numbered_root)

    def assert_agent_kb_config(self, repo, vault):
        config = json.loads((repo / ".agent-kb.json").read_text())
        self.assertEqual(Path(config["vault"]).resolve(), vault.resolve())
        self.assertEqual(config["project"], PROJECT)
        self.assertEqual(config["schema_version"], 2)
        self.assertEqual(config["vault_profile"], "personal-first")
        self.assertEqual(config["storage_adapter"], "markdown-filesystem")
        self.assertEqual(config["editor_profile"], "obsidian-compatible-markdown")
        self.assertEqual(config["editor_adapter"], "obsidian-cli")
        self.assertEqual(config["agent_adapter"], "codex")
        self.assertEqual(config["context_pack"], f"projects/{PROJECT}/context-pack.md")
        self.assertEqual(config["index"], "_system/indexes/home.md")
        self.assertEqual(config["knowledge_index"], "_system/indexes/knowledge-index.md")
        self.assertEqual(config["project_index"], "projects/_project-index.md")
        self.assertTrue(config["problem_capture"]["enabled"])
        self.assertTrue(config["problem_capture"]["auto_capture"])
        self.assertTrue(config["problem_capture"]["manual_records"])
        self.assertEqual(config["problem_capture"]["problem_signals"], "_agent/problem-signals")
        self.assertEqual(
            config["problem_capture"]["reflection_drafts"],
            f"projects/{PROJECT}/proposed-changes/problem-reflections",
        )
        self.assertEqual(config["obsidian_cli"]["command"], "obsidian")
        self.assertEqual(
            config["obsidian_cli"]["fallback_command"],
            "/Applications/Obsidian.app/Contents/MacOS/obsidian-cli",
        )
        self.assertFalse((repo / ".codex" / "obsidian-kb.json").exists())

    def assert_agent_kb_instructions(self, vault):
        agents = (vault / "AGENTS.md").read_text()
        self.assertIn("Markdown is the canonical durable storage", agents)
        self.assertIn("Obsidian is an editor profile", agents)
        self.assertIn("Codex is one agent adapter", agents)
        self.assertIn("_system/routing-rules.md", agents)
        self.assertIn("Do not read `personal/` or `archive/`", agents)

    def assert_context_pack_frontmatter(self, vault):
        context_pack = vault / "projects" / PROJECT / "context-pack.md"
        text = context_pack.read_text()
        self.assertTrue(text.startswith("---\n"))
        for required in [
            "type: context-pack",
            f"project: {PROJECT}",
            "confidence: high",
            "agent_readable: true",
        ]:
            self.assertIn(required, text)
        return context_pack, text

    def assert_reflection_promotion_playbooks(self, vault):
        index = (vault / "_system" / "indexes" / "knowledge-index.md").read_text()
        self.assertIn("[[../../playbooks/kb-reflect|KB reflect]]", index)
        self.assertIn("[[../../playbooks/kb-promote|KB promote]]", index)
        reflect_playbook = (vault / "playbooks" / "kb-reflect.md").read_text()
        promote_playbook = (vault / "playbooks" / "kb-promote.md").read_text()
        self.assertIn("generalized lesson", reflect_playbook.lower())
        self.assertIn("prevention mechanism", reflect_playbook.lower())
        self.assertIn("smallest durable destination", promote_playbook.lower())

    def test_scaffold_creates_markdown_canonical_vault_and_agent_config(self):
        repo, vault = self.make_repo_and_vault()

        report = self.scaffold(repo, vault)

        self.assertEqual(report["project"], PROJECT)
        self.assertTrue(report["configured"])
        self.assertGreater(len(report["written"]), 15)
        self.assert_scaffold_core_files(vault)
        self.assert_no_numbered_roots(vault)
        self.assert_agent_kb_config(repo, vault)
        self.assert_agent_kb_instructions(vault)
        context_pack, text = self.assert_context_pack_frontmatter(vault)
        self.assert_reflection_promotion_playbooks(vault)

        context_pack.write_text(text + "\nManual edit that must survive scaffold reruns.\n")
        second = self.scaffold(repo, vault)
        self.assertIn(f"projects/{PROJECT}/context-pack.md", second["skipped"])
        self.assertIn("Manual edit that must survive scaffold reruns.", context_pack.read_text())

    def test_project_cli_enables_status_and_verify_problem_capture(self):
        repo, vault = self.make_repo_and_vault()

        initial = run_json("kb_project.py", "status", "--repo", str(repo), "--json")

        self.assertFalse(initial["configured"], initial)
        self.assertFalse(initial["problem_capture"]["enabled"], initial)

        enabled = run_json(
            "kb_project.py",
            "enable",
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

        self.assertTrue(enabled["configured"], enabled)
        self.assertTrue(enabled["problem_capture"]["enabled"], enabled)
        self.assertTrue((repo / ".agent-kb.json").exists())
        self.assertTrue((vault / "_agent" / "problem-signals").exists())
        self.assertTrue((vault / "projects" / PROJECT / "proposed-changes" / "problem-reflections").exists())

        status = run_json("kb_project.py", "status", "--repo", str(repo), "--json")
        verify = run_json("kb_project.py", "verify", "--repo", str(repo), "--json")
        second = run_json(
            "kb_project.py",
            "enable",
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

        self.assertTrue(status["configured"], status)
        self.assertTrue(status["problem_capture"]["auto_capture"], status)
        self.assertTrue(verify["ok"], verify)
        self.assertEqual([], verify["findings"], verify)
        self.assertIn(".agent-kb.json", second["scaffold"]["skipped"])

    def test_lint_reports_health_and_writes_reviewable_report(self):
        repo, vault = self.make_repo_and_vault()
        self.scaffold(repo, vault)

        clean = run_json("kb_lint.py", "--vault", str(vault), "--project", PROJECT, "--json")

        self.assertTrue(clean["ok"], clean)
        self.assertEqual(clean["blocking_findings"], 0)
        self.assertEqual(clean["finding_count"], 0)
        self.assertTrue(clean["context_pack"].endswith(f"projects/{PROJECT}/context-pack.md"))

        bad_note = vault / "wiki" / "concepts" / "missing-frontmatter.md"
        bad_note.parent.mkdir(parents=True, exist_ok=True)
        bad_note.write_text("# Missing Frontmatter\n")

        report = run_json("kb_lint.py", "--vault", str(vault), "--project", PROJECT, "--write-report", "--json")

        findings = set(map(lambda item: (item["rule"], item["path"]), report["findings"]))
        self.assertIn(("missing-frontmatter", "wiki/concepts/missing-frontmatter.md"), findings)
        report_path = vault / report["report_path"]
        self.assertTrue(report_path.exists(), report)
        self.assertTrue(report["report_path"].startswith(f"projects/{PROJECT}/proposed-changes/"))

    def test_lint_reports_personal_first_backlogs_and_missing_protocol(self):
        repo, vault = self.make_repo_and_vault()
        self.scaffold(repo, vault)
        old_time = 1

        capture = vault / "inbox" / "codex-captures" / "old-capture.md"
        capture.parent.mkdir(parents=True, exist_ok=True)
        capture.write_text("# Old Capture\n")
        promotion = vault / "promotion" / "candidates" / "old-candidate.md"
        promotion.parent.mkdir(parents=True, exist_ok=True)
        promotion.write_text("# Old Candidate\n")
        needs_review = vault / "knowledge" / "concepts" / "needs-review.md"
        needs_review.parent.mkdir(parents=True, exist_ok=True)
        needs_review.write_text(
            "---\n"
            "type: concept\n"
            f"project: {PROJECT}\n"
            "status: active\n"
            "confidence: medium\n"
            "agent_readable: true\n"
            "needs_review: true\n"
            "---\n"
            "# Needs Review\n"
        )
        archive_ref = vault / "knowledge" / "concepts" / "archive-ref.md"
        archive_ref.write_text(
            "---\n"
            "type: concept\n"
            f"project: {PROJECT}\n"
            "status: active\n"
            "confidence: medium\n"
            "agent_readable: true\n"
            "---\n"
            "# Archive Ref\n\nSee [[../../archive/stale-note]].\n"
        )
        os.utime(capture, (old_time, old_time))
        os.utime(promotion, (old_time, old_time))
        routing_rules = vault / "_system" / "routing-rules.md"
        if routing_rules.exists():
            routing_rules.unlink()

        report = run_json("kb_lint.py", "--vault", str(vault), "--project", PROJECT, "--json")

        findings = set(map(lambda item: (item["rule"], item["path"]), report["findings"]))
        self.assertIn(("missing-core-file", "_system/routing-rules.md"), findings)
        self.assertIn(("capture-unprocessed", "inbox/codex-captures/old-capture.md"), findings)
        self.assertIn(("promotion-candidate-stale", "promotion/candidates/old-candidate.md"), findings)
        self.assertIn(("needs-review", "knowledge/concepts/needs-review.md"), findings)
        self.assertIn(("active-archive-reference", "knowledge/concepts/archive-ref.md"), findings)

    def test_source_intake_dry_run_and_apply_preserves_raw_extracts_and_receipts(self):
        repo, vault = self.make_repo_and_vault()
        self.scaffold(repo, vault)
        source = repo / "Research Note.md"
        source.write_text("# Research Note\n\nDurable fact.\n", encoding="utf-8")

        dry = run_json(
            "kb_import.py",
            "--vault",
            str(vault),
            "--project",
            PROJECT,
            "--source",
            str(source),
            "--dry-run",
            "--json",
        )

        self.assertTrue(dry["ok"], dry)
        self.assertTrue(dry["dry_run"], dry)
        self.assertEqual("optional-but-primary", dry["extractor_capabilities"]["markitdown"]["importance"])
        self.assertEqual(1, len(dry["planned"]))
        self.assertFalse((vault / "_agent" / "source-intake" / "sources.jsonl").exists())

        applied = run_json(
            "kb_import.py",
            "--vault",
            str(vault),
            "--project",
            PROJECT,
            "--source",
            str(source),
            "--apply",
            "--json",
        )

        self.assertTrue(applied["ok"], applied)
        self.assertFalse(applied["dry_run"], applied)
        self.assertEqual(1, len(applied["imported"]))
        item = applied["imported"][0]
        for key in ["raw_path", "extracted_path", "summary_path", "receipt_path"]:
            self.assertTrue((vault / item[key]).exists(), (key, item))
        self.assertIn("Durable fact.", (vault / item["extracted_path"]).read_text())
        self.assertIn("needs_review: true", (vault / item["summary_path"]).read_text())
        self.assertIn(item["source_id"], (vault / "_agent/source-intake/sources.jsonl").read_text())
        self.assertIn("Imported source", (vault / "knowledge" / "log.md").read_text())

        duplicate = run_json(
            "kb_import.py",
            "--vault",
            str(vault),
            "--project",
            PROJECT,
            "--source",
            str(source),
            "--apply",
            "--json",
        )

        self.assertEqual(0, len(duplicate["imported"]), duplicate)
        self.assertEqual("duplicate", duplicate["skipped"][0]["reason"])

    def test_source_intake_can_use_configured_external_markitdown_command(self):
        repo, vault = self.make_repo_and_vault()
        self.scaffold(repo, vault)
        source = repo / "External Note.docx"
        source.write_text("raw source placeholder", encoding="utf-8")
        converter = repo / "fake-markitdown"
        converter.write_text(
            "#!/bin/sh\n"
            "printf '# External Note\\n\\nConverted through configured MarkItDown.\\n'\n",
            encoding="utf-8",
        )
        converter.chmod(0o755)

        previous = os.environ.get("AGENT_KB_MARKITDOWN_CMD")
        os.environ["AGENT_KB_MARKITDOWN_CMD"] = str(converter)
        try:
            dry = run_json(
                "kb_import.py",
                "--vault",
                str(vault),
                "--project",
                PROJECT,
                "--source",
                str(source),
                "--dry-run",
                "--json",
            )
            applied = run_json(
                "kb_import.py",
                "--vault",
                str(vault),
                "--project",
                PROJECT,
                "--source",
                str(source),
                "--apply",
                "--json",
            )
        finally:
            if previous is None:
                os.environ.pop("AGENT_KB_MARKITDOWN_CMD", None)
            else:
                os.environ["AGENT_KB_MARKITDOWN_CMD"] = previous

        self.assertTrue(dry["extractor_capabilities"]["markitdown"]["available"], dry)
        imported = applied["imported"][0]
        extracted = (vault / imported["extracted_path"]).read_text(encoding="utf-8")
        self.assertIn("extractor: markitdown", extracted)
        self.assertIn("Converted through configured MarkItDown.", extracted)

    def test_source_intake_optional_binary_extractors_report_unsupported_when_missing(self):
        import agent_kb_extractors

        root = Path(tempfile.mkdtemp(prefix="agent-kb-extractors-"))
        pdf = root / "manual.pdf"
        xlsx = root / "manual.xlsx"
        pdf.write_bytes(b"%PDF-1.4\n%EOF\n")
        xlsx.write_bytes(b"not-a-real-workbook")

        with mock.patch.object(agent_kb_extractors.importlib.util, "find_spec", return_value=None):
            self.assertEqual(".pdf", agent_kb_extractors.extract_pdf(pdf)["error"].split()[-1])
            self.assertEqual(".xlsx", agent_kb_extractors.extract_xlsx(xlsx)["error"].split()[-1])

    def test_source_intake_blocks_unsafe_urls_and_plans_feishu_commands(self):
        repo, vault = self.make_repo_and_vault()
        self.scaffold(repo, vault)

        blocked = run_json(
            "kb_import.py",
            "--vault",
            str(vault),
            "--project",
            PROJECT,
            "--source",
            "ftp://example.com/private.pdf",
            "--dry-run",
            "--json",
        )

        self.assertFalse(blocked["ok"], blocked)
        self.assertEqual("blocked-url-scheme", blocked["warnings"][0]["rule"])

        feishu = run_json(
            "kb_import.py",
            "--vault",
            str(vault),
            "--project",
            PROJECT,
            "--source",
            "https://example.feishu.cn/docx/abc123",
            "--dry-run",
            "--json",
        )

        self.assertTrue(feishu["ok"], feishu)
        self.assertEqual("feishu-doc", feishu["planned"][0]["kind"])
        commands = [" ".join(command) for command in feishu["planned"][0]["commands"]]
        self.assertIn("lark-cli drive +inspect", commands[0])
        self.assertIn("lark-cli docs +fetch --api-version v2", commands[1])

    def test_lint_reports_stale_source_intake_backlog(self):
        repo, vault = self.make_repo_and_vault()
        self.scaffold(repo, vault)
        old_time = 1
        extracted = vault / "_agent" / "source-intake" / "extracted" / "old-source.md"
        receipt = vault / "_agent" / "source-intake" / "receipts" / "old-source.md"
        extracted.parent.mkdir(parents=True, exist_ok=True)
        receipt.parent.mkdir(parents=True, exist_ok=True)
        extracted.write_text("# Old Source\n", encoding="utf-8")
        receipt.write_text("# Old Receipt\n", encoding="utf-8")
        os.utime(extracted, (old_time, old_time))
        os.utime(receipt, (old_time, old_time))

        report = run_json("kb_lint.py", "--vault", str(vault), "--project", PROJECT, "--json")

        findings = set(map(lambda item: (item["rule"], item["path"]), report["findings"]))
        self.assertIn(("source-intake-backlog", "_agent/source-intake/extracted/old-source.md"), findings)

    def test_obsidian_cli_adapter_reports_status_and_runs_whitelisted_commands(self):
        from agent_kb_obsidian_cli import obsidian_cli_status, run_obsidian_cli

        root = Path(tempfile.mkdtemp(prefix="agent-kb-obsidian-cli-"))
        missing = obsidian_cli_status(
            {"command": str(root / "missing"), "fallback_command": str(root / "also-missing")}
        )
        self.assertFalse(missing["available"], missing)
        self.assertIn("fallback_reason", missing)

        fake = root / "obsidian"
        fake.write_text("#!/bin/sh\nprintf 'fake-obsidian:%s\\n' \"$*\"\n", encoding="utf-8")
        fake.chmod(0o755)

        status = obsidian_cli_status({"command": str(fake), "fallback_command": str(fake)})
        self.assertTrue(status["available"], status)
        self.assertEqual(status["used_command"], str(fake))

        result = run_obsidian_cli("search", ["agent-kb"], {"command": str(fake)})
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["used_command"], str(fake))
        self.assertIn("fake-obsidian:search agent-kb", result["stdout"])

        blocked = run_obsidian_cli("delete", ["anything"], {"command": str(fake)})
        self.assertFalse(blocked["ok"], blocked)
        self.assertEqual(blocked["fallback_reason"], "command-not-allowed")

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

    def test_failed_event_hook_writes_sanitized_problem_signal(self):
        repo, vault = self.make_repo_and_vault()
        self.scaffold(repo, vault)
        payload = {
            "cwd": str(repo),
            "prompt": "SECRET_PROMPT_TEXT",
            "tool_name": "Bash",
            "tool_input": {"command": "python3 -m unittest tests/test_example.py token=SECRET_TOKEN"},
            "tool_response": {"exit_code": 1, "output": "SECRET_OUTPUT_BODY\nline2"},
        }

        report = run_json(
            "kb_event_hook.py",
            "--event",
            "post_tool_use",
            "--json",
            input_text=json.dumps(payload),
        )

        self.assertTrue(report["recorded"], report)
        self.assertTrue(report["problem_signal"]["recorded"], report)
        signal_path = vault / report["problem_signal"]["path"]
        signal_raw = signal_path.read_text()
        self.assertNotIn("SECRET_PROMPT_TEXT", signal_raw)
        self.assertNotIn("SECRET_OUTPUT_BODY", signal_raw)
        self.assertNotIn("SECRET_TOKEN", signal_raw)
        signal = json.loads(signal_raw.splitlines()[-1])
        self.assertEqual(signal["status"], "fail")
        self.assertEqual(signal["command_category"], "test")
        self.assertTrue(signal["needs_review"])

        success = run_json(
            "kb_event_hook.py",
            "--event",
            "post_tool_use",
            "--json",
            input_text=json.dumps(
                {
                    "cwd": str(repo),
                    "tool_name": "Bash",
                    "tool_response": {"exit_code": 0, "output": "ok"},
                }
            ),
        )

        self.assertFalse(success["problem_signal"]["recorded"], success)

    def test_manual_problem_record_writes_reviewable_reflection_draft(self):
        repo, vault = self.make_repo_and_vault()
        self.scaffold(repo, vault)

        report = run_json(
            "kb_problem.py",
            "record",
            "--repo",
            str(repo),
            "--incident",
            "Unit tests failed after enabling AgentKB",
            "--evidence",
            "python3 -m unittest exited 1",
            "--root-cause",
            "Missing project problem capture configuration",
            "--lesson",
            "Project knowledge capture needs an explicit enablement check",
            "--prevention",
            "Run kb_project.py verify before relying on hooks",
            "--validation",
            "python3 -m unittest dev/plugins/agent-kb/tests/test_agent_kb.py -v",
            "--residual-risk",
            "Existing vaults may need manual enablement",
            "--json",
        )

        self.assertTrue(report["recorded"], report)
        self.assertTrue(report["needs_review"], report)
        self.assertTrue(report["path"].startswith(f"projects/{PROJECT}/proposed-changes/problem-reflections/"))
        draft = (vault / report["path"]).read_text()
        self.assertIn("Unit tests failed after enabling AgentKB", draft)
        self.assertIn("## Root Cause", draft)
        self.assertIn("## Prevention Mechanism", draft)
        self.assertIn("needs_review: true", draft)

    def test_kb_skills_are_packaged_with_markdown_first_safety_rules(self):
        skill_dirs = filter(lambda path: path.is_dir(), (PLUGIN_ROOT / "skills").iterdir())
        self.assertEqual(KB_SKILLS, set(map(lambda path: path.name, skill_dirs)))
        for skill in KB_SKILLS:
            text = (PLUGIN_ROOT / "skills" / skill / "SKILL.md").read_text()
            self.assertTrue(text.startswith("---\n"), skill)
            self.assertIn(f"name: {skill}", text)
            self.assertIn("context", text)
            self.assertIn("Markdown", text)
            self.assertIn("Git diff", text)

        capture = (PLUGIN_ROOT / "skills" / "kb-capture" / "SKILL.md").read_text()
        self.assertIn("inbox/codex-captures", capture)
        self.assertIn("_system/routing-rules.md", capture)
        self.assertIn("_agent/routing-receipts", capture)
        self.assertIn("personal/", capture)
        self.assertIn("archive/", capture)
        import_skill = (PLUGIN_ROOT / "skills" / "kb-import" / "SKILL.md").read_text()
        self.assertIn("MarkItDown", import_skill)
        self.assertIn("kb-ingest", import_skill)
        self.assertIn("_agent/source-intake", import_skill)
        reflect = (PLUGIN_ROOT / "skills" / "kb-reflect" / "SKILL.md").read_text()
        promote = (PLUGIN_ROOT / "skills" / "kb-promote" / "SKILL.md").read_text()
        enable = (PLUGIN_ROOT / "skills" / "kb-enable-project" / "SKILL.md").read_text()
        self.assertIn("Generalized Lesson", reflect)
        self.assertIn("Prevention Mechanism", reflect)
        self.assertIn("problem signals", reflect)
        self.assertIn("Promotion Thresholds", promote)
        self.assertIn("smallest durable destination", promote.lower())
        self.assertIn("kb_project.py", enable)
        self.assertIn("kb_problem.py", enable)

if __name__ == "__main__":
    unittest.main()
