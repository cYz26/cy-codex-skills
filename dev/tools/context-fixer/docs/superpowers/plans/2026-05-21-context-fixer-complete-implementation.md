# Context Fixer Complete Implementation Plan

> Status: Context Fixer development is temporarily pending. This plan is kept as
> historical reference only; the previously planned or implemented features are
> not recommended for new workflows until a fresh scope and verification plan
> are approved.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the complete Context Fixer product described by `docs/codex-context-requirements.md` and `docs/codex-context-technical-solution.md`, not only the CLI MVP, while preserving the existing Python analysis engine.

**Architecture:** Keep `context_fixer` as the canonical package and `codex_context_lens` as compatibility wrappers. Extend the existing local-first analyzer with focused modules for governance recommendations, hook-event ingestion, adapter imports, SQLite-backed local history, an interactive Web dashboard, and guided governance actions. Every new user-visible behavior gets an OpenSpec change before implementation and every behavior change is test-first.

**Tech Stack:** Python 3.11 standard library, `sqlite3`, `unittest`, OpenSpec, local JSON/JSONL inputs, and a no-dependency local Web dashboard shell. Tauri is explicitly out of scope; the product ships as CLI plus local Web UI. Live proxy capture and silent config mutation remain out of scope.

---

## Current Baseline

Already implemented and verified:

- Static baseline scanning for global/project/nested `AGENTS.md`, skill metadata, Codex config, MCP inventory, hooks, planning state, and OpenSpec config.
- Session JSONL parsing for exact token telemetry, compaction events, timeline growth, message estimates, tool arguments, Bash output, file reads, patch/diff output, web/search output, and MCP output.
- Request trace import for generic Responses-style traces and Codex claude-tap JSONL, including request messages, instructions, tool definitions, tool results, exact usage, and transport metadata.
- Context Lens budget model: `baseline`, `session_growth`, `turn_deltas`, `request_composition`, `top_offenders`, and evidence-backed recommendations.
- CLI commands: `audit`, `sessions`, `inspect`, `report`, `recommend`, `doctor`, `trace import`.
- Text, JSON, Markdown, and self-contained HTML reports.
- Append-only sanitized hook collector entry point: `context-fixer-hook`.
- Tests: 22 unit tests passed in the latest verification pass.

Known workflow state before starting new implementation:

- `complete-context-lens-interfaces` and `refactor-context-attribution-engine` are implemented and verified but not archived.
- Dependency check reports `missing_required` because the global Superpowers plugin is enabled and two project-local Superpowers skill checks are not satisfied, while the external Superpowers skill paths are available.
- The repository has unrelated dirty files outside `tools/context-fixer`; workers must not modify or revert them.

## Scope Fence

This plan implements the full landed product described by the requirement and technical documents in incremental phases, with these constraints:

- Use the product name **Context Fixer** in user-facing docs and CLI text.
- Preserve Python CLI compatibility and existing report keys.
- Keep trace and hook data sanitized: no prompt bodies, chat contents, tool argument bodies, command output bodies, file contents, or trace payload bodies in reports.
- Include a real Web dashboard and local history store; do not build a macOS desktop wrapper.
- Generate configuration and workflow recommendations as patch plans or snippets. Apply changes only through explicit user-invoked dry-run/apply commands with backups.
- Treat external tools as optional adapters or guidance. Context Fixer does not replace abtop, Codex Trace, ccusage, claude-tap, RTK, or OTel.

## Planned File Responsibilities

- `src/context_fixer/analyzer.py`: orchestrates all data sources into one sanitized report.
- `src/context_fixer/budget.py`: maps contributors into Context Lens budget sections.
- `src/context_fixer/static_sources.py`: scans Codex/project static context.
- `src/context_fixer/session.py`: parses Codex session JSONL.
- `src/context_fixer/trace.py`: parses supplied request traces.
- `src/context_fixer/hook.py`: records sanitized hook events.
- `src/context_fixer/render.py`: renders text, Markdown, JSON-ready data, and HTML.
- `src/context_fixer/cli.py`: exposes command surface and compatibility flags.
- Create `src/context_fixer/governance.py`: profile, AGENTS, Skills, MCP, hook, and command-output recommendation engine.
- Create `src/context_fixer/hook_events.py`: reads sanitized hook JSONL records and converts them into contributors/activity events.
- Create `src/context_fixer/adapters.py`: imports optional external evidence from ccusage-style JSON and OTel-style JSONL exports.
- Create `src/context_fixer/store.py`: persists sanitized audit snapshots, sessions, traces, hook summaries, and recommendations in SQLite.
- Create `src/context_fixer/dashboard.py`: builds dashboard-focused report projections for API and HTML use.
- Create `src/context_fixer/web.py`: serves the local Web dashboard and sanitized JSON API.
- Create `web/dashboard/`: no-dependency Web dashboard shell for overview, baseline, sessions, timeline, top offenders, recommendations, and data-source health.
- Create `src/context_fixer/remediation.py`: generates governance plans and applies explicitly approved changes with backups.
- Modify `tests/test_context_fixer.py`: add regression coverage for each new phase.
- Modify `README.md` and `skills/context-fixer/SKILL.md`: document each new command and privacy boundary.
- Modify OpenSpec under `openspec/changes/<change-id>/`: create one approved change per phase before production code changes.
- Modify `.planning/STATE.md` and `.planning/checkpoints/*.md`: record planning and verification boundaries.

## Phase 0: Workflow Stabilization and Approval Gate

**Purpose:** Make the next implementation safe to start from the current verified-but-unarchived state.

**OpenSpec:** No new behavior change yet. This phase is planning and workflow hygiene.

### Task 0.1: Re-validate Current Baseline

**Files:**
- Read: `AGENTS.md`
- Read: `.planning/STATE.md`
- Read: `openspec/config.yaml`
- Read: `docs/codex-context-requirements.md`
- Read: `docs/codex-context-technical-solution.md`

- [ ] **Step 1: Run workflow dependency check**

Run:

```bash
/opt/homebrew/bin/python3.11 /Users/cY/dev/skills/cy-codex-skills/dev/plugins/codex-project-orchestrator/scripts/check_dependencies.py --repo . --json
```

Expected: JSON is produced. If `status` remains `missing_required` only because of global Superpowers activation or project-local Superpowers skill detection, record it as a workflow warning and continue only after user approval.

- [ ] **Step 2: Run current verification suite**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3.11 -m unittest discover -s tests -v
python3.11 -m py_compile src/context_fixer/*.py src/codex_context_lens/*.py
openspec validate refactor-context-attribution-engine --strict
openspec validate complete-context-lens-interfaces --strict
```

Expected: 22 tests pass, py_compile exits 0, both OpenSpec changes are valid.

- [ ] **Step 3: Confirm implementation route with user**

Present these route choices:

```text
Recommended route: complete landed product with Python analysis engine, SQLite history, React Web dashboard, and explicit governance apply flow.
Reduced route: complete CLI product without React Web dashboard, for environments that cannot approve Node dependencies.
Rejected route: Tauri desktop app. The user explicitly does not need a macOS desktop wrapper.
```

Expected: user confirms the recommended route or selects another route before any production code changes.

## Phase 1: OpenSpec Sync for Full Product Completion

**Purpose:** Convert the remaining document requirements into approved OpenSpec artifacts.

**OpenSpec changes to create after user approval:**

- `add-governance-recommendation-engine`
- `ingest-hook-audit-events`
- `add-managed-external-tool-orchestration`
- `add-local-history-store`
- `add-web-dashboard`
- `add-guided-governance-remediation`
- `package-context-fixer-workflow-integration`

### Task 1.1: Create Governance Recommendation OpenSpec Change

**Files:**
- Create: `openspec/changes/add-governance-recommendation-engine/proposal.md`
- Create: `openspec/changes/add-governance-recommendation-engine/design.md`
- Create: `openspec/changes/add-governance-recommendation-engine/tasks.md`
- Create: `openspec/changes/add-governance-recommendation-engine/specs/current-system/spec.md`

- [ ] **Step 1: Scaffold the change**

Run:

```bash
openspec new change add-governance-recommendation-engine
```

Expected: `openspec/changes/add-governance-recommendation-engine/` exists.

- [ ] **Step 2: Write acceptance scenarios**

Include these exact behavior commitments:

```markdown
### Scenario: profile governance recommendations are generated without mutation
- **WHEN** an audit finds heavy MCP inventory or request tool schemas
- **THEN** the report includes profile recommendations with suggested default-disabled servers, research/design profile placement, and allowlist hints
- **AND** no Codex config file is modified

### Scenario: AGENTS and Skills governance recommendations are specific
- **WHEN** project or global instruction files exceed configured thresholds
- **THEN** the report recommends which instruction class should remain in AGENTS and which content class should move to Skills or docs
- **AND** prompt/file bodies remain omitted

### Scenario: command-output recommendations include concrete future commands
- **WHEN** Bash output is a top offender
- **THEN** the report includes tail, failure-only, reporter, or RTK-style command recipes
- **AND** the report does not include raw command output
```

- [ ] **Step 3: Validate the change**

Run:

```bash
openspec validate add-governance-recommendation-engine --strict
```

Expected: `Change 'add-governance-recommendation-engine' is valid`.

### Task 1.2: Create Hook Event Ingestion OpenSpec Change

**Files:**
- Create: `openspec/changes/ingest-hook-audit-events/proposal.md`
- Create: `openspec/changes/ingest-hook-audit-events/design.md`
- Create: `openspec/changes/ingest-hook-audit-events/tasks.md`
- Create: `openspec/changes/ingest-hook-audit-events/specs/current-system/spec.md`

- [ ] **Step 1: Scaffold and specify hook ingestion**

Run:

```bash
openspec new change ingest-hook-audit-events
```

Acceptance scenarios:

```markdown
### Scenario: supplied hook event JSONL contributes to session growth
- **WHEN** `context-fixer audit --hook-events hooks/events.jsonl` is run
- **THEN** sanitized hook event sizes appear in session growth and capability activity
- **AND** raw hook payload bodies do not appear in text, Markdown, JSON, or HTML reports

### Scenario: default hook cache is not silently treated as source of truth
- **WHEN** no `--hook-events` path is supplied
- **THEN** the audit reports hook collector availability as configuration evidence only
- **AND** it does not ingest unrelated cached records from other repositories
```

- [ ] **Step 2: Validate the change**

Run:

```bash
openspec validate ingest-hook-audit-events --strict
```

Expected: change is valid.

### Task 1.3: Create Managed External Tool Orchestration OpenSpec Change

**Files:**
- Create: `openspec/changes/add-managed-external-tool-orchestration/proposal.md`
- Create: `openspec/changes/add-managed-external-tool-orchestration/design.md`
- Create: `openspec/changes/add-managed-external-tool-orchestration/tasks.md`
- Create: `openspec/changes/add-managed-external-tool-orchestration/specs/current-system/spec.md`

- [ ] **Step 1: Scaffold and specify managed tool orchestration**

Run:

```bash
openspec new change add-managed-external-tool-orchestration
```

Acceptance scenarios:

```markdown
### Scenario: official collection flow starts required external tools
- **WHEN** `context-fixer collect --project <repo> --profile full` is run
- **THEN** Context Fixer checks required external tool availability, starts or invokes configured collectors, writes artifacts into the run directory, imports them into the sanitized report, and records tool status
- **AND** the user is not required to manually run each external command

### Scenario: unavailable external tools degrade with explicit status
- **WHEN** a configured external tool is missing, unhealthy, or refuses to start
- **THEN** the run report marks that tool as `missing`, `failed`, or `skipped`
- **AND** Context Fixer continues with available sources unless the selected profile marks the tool as required

### Scenario: sensitive capture tools require an explicit profile
- **WHEN** a flow would start a request payload capture tool such as claude-tap
- **THEN** Context Fixer starts it only in a trace-enabled profile such as `full` or `trace`
- **AND** the report labels trace artifacts as sensitive while still rendering only sanitized attribution

### Scenario: manual imports remain available for advanced use
- **WHEN** `context-fixer usage import ccusage.json --repo <repo>` or `context-fixer otel import codex-otel.jsonl --repo <repo>` is run
- **THEN** supplied artifacts are imported exactly as before
- **AND** manual import is documented as advanced/debug flow, not the official default
```

- [ ] **Step 2: Validate the change**

Run:

```bash
openspec validate add-managed-external-tool-orchestration --strict
```

Expected: change is valid.

### Task 1.4: Create Local History Store OpenSpec Change

**Files:**
- Create: `openspec/changes/add-local-history-store/proposal.md`
- Create: `openspec/changes/add-local-history-store/design.md`
- Create: `openspec/changes/add-local-history-store/tasks.md`
- Create: `openspec/changes/add-local-history-store/specs/current-system/spec.md`

- [ ] **Step 1: Scaffold and specify local history**

Run:

```bash
openspec new change add-local-history-store
```

Acceptance scenarios:

```markdown
### Scenario: audit snapshots can be saved locally
- **WHEN** `context-fixer audit --project <repo> --session-only --save` is run
- **THEN** a sanitized audit snapshot is persisted in the local SQLite store
- **AND** prompt, message, tool argument, command output, file, and trace payload bodies are not stored

### Scenario: history can be queried without re-reading sensitive payloads
- **WHEN** `context-fixer history --project <repo> --format json` is run
- **THEN** saved audit snapshots are listed with timestamps, severity, policy status, source counts, and top offender summaries
- **AND** the command does not require access to original trace payload files
```

- [ ] **Step 2: Validate the change**

Run:

```bash
openspec validate add-local-history-store --strict
```

Expected: change is valid.

### Task 1.5: Create Web Dashboard OpenSpec Change

**Files:**
- Create: `openspec/changes/add-web-dashboard/proposal.md`
- Create: `openspec/changes/add-web-dashboard/design.md`
- Create: `openspec/changes/add-web-dashboard/tasks.md`
- Create: `openspec/changes/add-web-dashboard/specs/current-system/spec.md`

- [ ] **Step 1: Scaffold and specify Web dashboard**

Run:

```bash
openspec new change add-web-dashboard
```

Acceptance scenarios:

```markdown
### Scenario: web dashboard serves sanitized audit data
- **WHEN** `context-fixer dashboard serve --project <repo> --session-only --port 8765` is run
- **THEN** a local Web dashboard is available with overview, baseline, session timeline, top offenders, recommendations, data-source health, and history views
- **AND** every API response is derived from the sanitized report/history schema

### Scenario: static dashboard build can be exported
- **WHEN** `context-fixer dashboard export --project <repo> --session-only --output dashboard.html` is run
- **THEN** a local HTML artifact is written for sharing or archiving
- **AND** the artifact omits all sensitive bodies
```

- [ ] **Step 2: Validate the change**

Run:

```bash
openspec validate add-web-dashboard --strict
```

Expected: change is valid.

### Task 1.6: Create Guided Governance Remediation OpenSpec Change

**Files:**
- Create: `openspec/changes/add-guided-governance-remediation/proposal.md`
- Create: `openspec/changes/add-guided-governance-remediation/design.md`
- Create: `openspec/changes/add-guided-governance-remediation/tasks.md`
- Create: `openspec/changes/add-guided-governance-remediation/specs/current-system/spec.md`

- [ ] **Step 1: Scaffold and specify remediation**

Run:

```bash
openspec new change add-guided-governance-remediation
```

Acceptance scenarios:

```markdown
### Scenario: remediation dry-run creates a reviewable plan
- **WHEN** `context-fixer remediate plan --project <repo> --session-only --output remediation.json` is run
- **THEN** Context Fixer writes a plan containing AGENTS, Skills, MCP profile, hook, and command-output recommendations
- **AND** no repository or Codex configuration file is modified

### Scenario: remediation apply requires explicit input and creates backups
- **WHEN** `context-fixer remediate apply remediation.json --project <repo> --backup-dir .context-fixer/backups` is run
- **THEN** only changes listed in the remediation plan are applied
- **AND** original files are backed up before modification
- **AND** the command refuses to apply a plan that contains unknown operations
```

- [ ] **Step 2: Validate the change**

Run:

```bash
openspec validate add-guided-governance-remediation --strict
```

Expected: change is valid.

### Task 1.7: Create Workflow Integration OpenSpec Change

**Files:**
- Create: `openspec/changes/package-context-fixer-workflow-integration/proposal.md`
- Create: `openspec/changes/package-context-fixer-workflow-integration/design.md`
- Create: `openspec/changes/package-context-fixer-workflow-integration/tasks.md`
- Create: `openspec/changes/package-context-fixer-workflow-integration/specs/current-system/spec.md`

- [ ] **Step 1: Scaffold and specify skill/plugin packaging**

Run:

```bash
openspec new change package-context-fixer-workflow-integration
```

Acceptance scenarios:

```markdown
### Scenario: skill documentation exposes the full workflow
- **WHEN** a user opens `skills/context-fixer/SKILL.md`
- **THEN** it includes audit, report, trace import, hook collector, dashboard, recommendation, and doctor usage

### Scenario: hook template is copy-pasteable and safe
- **WHEN** a user follows the hook setup docs
- **THEN** the hook records only sanitized size/hash metadata
- **AND** the template does not mutate tool output or block commands
```

- [ ] **Step 2: Validate the change**

Run:

```bash
openspec validate package-context-fixer-workflow-integration --strict
```

Expected: change is valid.

## Phase 2: Governance Recommendation Engine

**Purpose:** Satisfy the complete-version requirement to generate profile, AGENTS, Skills, MCP, hooks, and shell-output optimization recommendations.

**Depends on:** `add-governance-recommendation-engine` approved.

### Task 2.1: Add Governance Report Model

**Files:**
- Create: `src/context_fixer/governance.py`
- Modify: `src/context_fixer/analyzer.py`
- Modify: `tests/test_context_fixer.py`

- [ ] **Step 1: Write failing test**

Add a test named:

```python
def test_governance_recommendations_include_profiles_agents_skills_mcp_and_commands(self) -> None:
    repo, codex_home, session = self.fixture()
    trace = self.trace_fixture(repo.parent)
    report = analyze_context(repo=repo, codex_home=codex_home, sessions=[session], traces=[trace])
    governance = report["governance"]
    surfaces = {item["surface"] for item in governance["recommendations"]}
    self.assertIn("profiles", surfaces)
    self.assertIn("agents", surfaces)
    self.assertIn("skills", surfaces)
    self.assertIn("mcp", surfaces)
    self.assertIn("commands", surfaces)
    self.assertTrue(all("action" in item for item in governance["recommendations"]))
    self.assertNotIn("SECRET_TRACE_USER", json.dumps(governance, ensure_ascii=False))
```

- [ ] **Step 2: Verify it fails**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3.11 -m unittest tests.test_context_fixer.ContextFixerTests.test_governance_recommendations_include_profiles_agents_skills_mcp_and_commands -v
```

Expected: fails because `report["governance"]` is missing.

- [ ] **Step 3: Implement `governance.py`**

Implement:

```python
def build_governance(report_inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "advisory",
        "mutates_files": False,
        "recommendations": [...],
        "profile_suggestions": [...],
        "agents_suggestions": [...],
        "skill_suggestions": [...],
        "mcp_suggestions": [...],
        "command_output_suggestions": [...],
    }
```

Rules:

- Recommendations must cite existing sanitized evidence: budget category, offender label, estimated tokens, config inventory, or trace metadata.
- Profile suggestions may include TOML snippets, but snippets must be examples, not applied changes.
- AGENTS suggestions describe content classes, not copied file bodies.
- Command-output suggestions include concrete alternatives such as `tail -n 120`, path-limited `rg`, failure-only test reporters, and RTK-style summarization guidance.

- [ ] **Step 4: Wire analyzer**

In `analyze_context`, add:

```python
governance = build_governance({
    "budget": budget,
    "config_audit": config_audit,
    "activity": activity,
    "data_sources": data_sources,
    "diagnosis": diagnosis,
})
```

Return it as:

```python
"governance": governance
```

- [ ] **Step 5: Verify test passes**

Run the targeted test again.

Expected: passes.

### Task 2.2: Render Governance Recommendations

**Files:**
- Modify: `src/context_fixer/render.py`
- Modify: `tests/test_context_fixer.py`
- Modify: `README.md`

- [ ] **Step 1: Write failing render test**

Add assertions that text, Markdown, and HTML include:

```text
Governance recommendations
Profile suggestions
AGENTS slimming
MCP profile
Command output
```

and omit:

```text
SECRET_TRACE_USER
SECRET_TOOL_ARGUMENT
SECRET_OUTPUT
```

- [ ] **Step 2: Implement render sections**

Add governance sections after budget recommendations in text/Markdown/HTML.

- [ ] **Step 3: Update README usage**

Document:

```bash
context-fixer recommend --project /path/to/repo --session-only --format markdown
context-fixer report --project /path/to/repo --trace .traces/codex-request.jsonl --format html
```

Expected wording: recommendations are advisory and never mutate config.

- [ ] **Step 4: Verify**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3.11 -m unittest discover -s tests -v
```

Expected: all tests pass.

## Phase 3: Hook Event Ingestion

**Purpose:** Move the hook collector from write-only metadata capture to explicit user-supplied report evidence.

**Depends on:** `ingest-hook-audit-events` approved.

### Task 3.1: Parse Sanitized Hook Event JSONL

**Files:**
- Create: `src/context_fixer/hook_events.py`
- Modify: `src/context_fixer/analyzer.py`
- Modify: `src/context_fixer/cli.py`
- Modify: `tests/test_context_fixer.py`

- [ ] **Step 1: Write failing parser test**

Add:

```python
def test_hook_events_file_contributes_sanitized_runtime_evidence(self) -> None:
    repo, codex_home, session = self.fixture()
    events = repo.parent / "hook-events.jsonl"
    events.write_text(json.dumps({
        "event_type": "post-tool-use",
        "cwd": str(repo),
        "tool_name": "Bash",
        "command_preview": "python -m pytest",
        "tool_response_estimated_tokens": 2400,
        "tool_response_hash": "abc123",
    }) + "\n", encoding="utf-8")
    report = analyze_context(repo=repo, codex_home=codex_home, sessions=[session], hook_events=[events])
    categories = {item["category"] for item in report["budget"]["session_growth"]["categories"]}
    self.assertIn("hook_tool_output", categories)
    self.assertNotIn("SECRET_OUTPUT", json.dumps(report, ensure_ascii=False))
```

- [ ] **Step 2: Verify it fails**

Run the targeted test.

Expected: fails because `hook_events` parameter is unsupported.

- [ ] **Step 3: Implement `parse_hook_events`**

Return a small stats object with:

```python
path: Path
events: int
contributors: list[Contributor]
activity_events: list[dict[str, Any]]
```

Contributor rules:

- `tool_response_estimated_tokens` becomes `hook_tool_output`.
- `tool_input_estimated_tokens` becomes `hook_tool_input`.
- Use `command_preview`, `tool_name`, and hashes only as metadata.
- Ignore records whose `cwd` is outside the audited repo unless the user passes `--include-external-hook-events`.

- [ ] **Step 4: Add CLI flags**

Add to analysis args:

```text
--hook-events PATH
--include-external-hook-events
```

- [ ] **Step 5: Verify**

Run targeted test and full suite.

Expected: all tests pass.

### Task 3.2: Document Safe Hook Workflow

**Files:**
- Modify: `README.md`
- Modify: `skills/context-fixer/SKILL.md`

- [ ] **Step 1: Document collector and ingestion separately**

Include:

```bash
context-fixer-hook post-tool-use
context-fixer audit --project /path/to/repo --session-only --hook-events ~/.cache/context-fixer/hooks/events.jsonl
```

- [ ] **Step 2: State privacy boundary**

Required sentence:

```text
Hook ingestion reads only sanitized event records produced by Context Fixer; it does not read raw Codex hook payloads unless the user explicitly passes such a file, and raw payload bodies are never rendered.
```

- [ ] **Step 3: Verify docs smoke**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3.11 -m context_fixer doctor --project . --session-only
```

Expected: command exits 0 and prints Context Fixer Doctor.

## Phase 4: Managed External Tool Orchestration

**Purpose:** Make the formal Context Fixer workflow responsible for checking, starting, collecting from, and shutting down or reusing declared external tools. Users should run one Context Fixer command for the official flow, not manually operate abtop, claude-tap, ccusage, RTK, and OTel one by one.

**Depends on:** `add-managed-external-tool-orchestration` approved.

### Managed External Tool Policy

Context Fixer must treat external tools as declared managed capabilities. Each capability needs an availability check, a start/invoke command, an artifact contract, import logic, health status, timeout behavior, and a privacy boundary.

| Tool | Role | Managed mode | Artifact contract | Privacy boundary |
|---|---|---|---|---|
| abtop | Live context pressure monitor | `collect --profile monitor` checks and starts/attaches when supported, records live pressure status | `external_tools.abtop.status`, optional sampled pressure summary | Do not capture prompt/file bodies |
| Codex Trace | Session history browser companion | `collect` does not need to start it; it verifies session files directly and links manual deep-dive guidance | session JSONL paths already parsed by Context Fixer | No extra data copied |
| claude-tap | Request payload microscope | `collect --profile trace` or `collect --profile full` starts capture into a run directory, waits for Codex activity, then imports captured JSONL | trace JSONL path under `.context-fixer/runs/<run-id>/traces/` | Trace artifact is sensitive; reports remain sanitized |
| ccusage | Long-term usage/cost aggregator | `collect --profile full` invokes ccusage export into the run directory | `ccusage.json` | Import totals/trends only |
| RTK | Command output reducer | `collect` does not rewrite current shell commands; `remediate plan` can generate RTK/tail/failure-only policies | remediation plan operations | No command output bodies stored |
| Codex OTel | Observability export | `collect --profile full` checks configured OTel export files or collector output and imports available JSONL | `otel.jsonl` or configured export path | Summarize event categories and sizes only |

Official profiles:

- `quick`: no external collector startup; local session/static scan only.
- `monitor`: start/attach lightweight pressure monitoring where available; no request payload capture.
- `trace`: start request trace capture and import it; marks run artifacts as sensitive.
- `full`: run static scan, session scan, hook ingestion, trace capture, ccusage export, configured OTel import, SQLite save, and dashboard refresh.

### Task 4.0: Document Managed External Tool Workflow

**Files:**
- Modify: `README.md`
- Modify: `skills/context-fixer/SKILL.md`
- Modify: `tests/test_context_fixer.py`

- [ ] **Step 1: Add managed workflow docs**

Document this command matrix:

```bash
# Official one-command collection profiles
context-fixer collect --project . --profile quick
context-fixer collect --project . --profile monitor
context-fixer collect --project . --profile trace --run-dir .context-fixer/runs/latest
context-fixer collect --project . --profile full --save --store .context-fixer/context-fixer.db

# Inspect managed tool status
context-fixer tools doctor --project . --format markdown
context-fixer tools list --format json

# Advanced/manual imports remain available
context-fixer trace import /path/to/trace.jsonl --repo . --format markdown
context-fixer usage import ccusage.json --repo . --format markdown
context-fixer otel import codex-otel.jsonl --repo . --format json
```

- [ ] **Step 2: Add docs verification test**

Add assertions:

```python
self.assertIn("context-fixer collect --project . --profile full", readme)
self.assertIn("context-fixer tools doctor", readme)
self.assertIn("abtop", readme)
self.assertIn("claude-tap", readme)
self.assertIn("ccusage", readme)
self.assertIn("context-fixer otel import", readme)
self.assertIn("RTK", readme)
self.assertIn("Managed external tool workflow", skill)
```

- [ ] **Step 3: Verify**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3.11 -m unittest discover -s tests -v
```

Expected: all tests pass.

### Task 4.1: Add Managed Tool Registry and Runner

**Files:**
- Create: `src/context_fixer/tools.py`
- Create: `src/context_fixer/adapters.py`
- Modify: `src/context_fixer/analyzer.py`
- Modify: `src/context_fixer/cli.py`
- Modify: `tests/test_context_fixer.py`

- [ ] **Step 1: Write failing tool registry test**

Add:

```python
def test_managed_tool_registry_reports_required_tool_status(self) -> None:
    from context_fixer.tools import build_tool_registry
    registry = build_tool_registry()
    names = {tool.name for tool in registry}
    self.assertIn("abtop", names)
    self.assertIn("claude-tap", names)
    self.assertIn("ccusage", names)
    self.assertIn("otel", names)
    self.assertIn("rtk", names)
```

- [ ] **Step 2: Write failing collect profile test**

Use mocks so tests do not start real external tools:

```python
def test_collect_full_profile_invokes_managed_tools_and_imports_artifacts(self) -> None:
    repo, codex_home, session = self.fixture()
    run_dir = repo.parent / "run"
    with patch("context_fixer.tools.ManagedToolRunner.run_profile") as runner:
        runner.return_value = {
            "run_id": "test-run",
            "artifacts": {
                "ccusage": str(repo.parent / "ccusage.json"),
                "otel": str(repo.parent / "otel.jsonl"),
            },
            "tools": {
                "ccusage": {"status": "ok"},
                "otel": {"status": "ok"},
            },
        }
        status, output = self.run_cli_capture(
            [
                "collect",
                "--project", str(repo),
                "--codex-home", str(codex_home),
                "--session", str(session),
                "--profile", "full",
                "--run-dir", str(run_dir),
                "--format", "json",
            ],
            cache_home=repo.parent / "cache",
            claude_tap_path=None,
        )
    data = json.loads(output)
    self.assertEqual(status, 0)
    self.assertEqual(data["external_tools"]["profile"], "full")
    self.assertIn("ccusage", data["external_tools"]["tools"])
```

- [ ] **Step 3: Write failing ccusage test**

Use fixture JSON:

```json
{
  "sessions": [
    {"session_id": "s1", "input_tokens": 12000, "output_tokens": 900, "cost": 0.42},
    {"session_id": "s2", "input_tokens": 18000, "output_tokens": 1300, "cost": 0.61}
  ]
}
```

Expected imported report:

```python
self.assertEqual(report["usage"]["ccusage"]["sessions"], 2)
self.assertEqual(report["usage"]["ccusage"]["input_tokens"], 30000)
self.assertEqual(report["usage"]["ccusage"]["source"], "imported_json")
```

- [ ] **Step 4: Write failing OTel test**

Use JSONL events with attributes for `input_tokens`, `tool_name`, and `prompt_length`.

Expected report:

```python
self.assertIn("otel", report["usage"])
self.assertGreater(report["usage"]["otel"]["events"], 0)
self.assertNotIn("SECRET_PROMPT", json.dumps(report, ensure_ascii=False))
```

- [ ] **Step 5: Implement managed tool registry**

Implement:

```python
@dataclass
class ManagedTool:
    name: str
    profiles: set[str]
    required_for: set[str]
    executable_candidates: list[str]
    artifact_kind: str
    sensitive: bool

class ManagedToolRunner:
    def doctor(self) -> dict[str, Any]: ...
    def run_profile(self, profile: str, repo: Path, run_dir: Path, timeout_seconds: int) -> dict[str, Any]: ...
```

Runner behavior:

- Resolve executables with `shutil.which`.
- Create `.context-fixer/runs/<run-id>/`.
- Start long-running collectors with `subprocess.Popen` and terminate owned processes at the end of the run.
- Invoke one-shot exporters with `subprocess.run`.
- Record stdout/stderr only as byte counts and hashes, not bodies.
- Mark tools as `ok`, `missing`, `failed`, `skipped`, or `not_applicable`.
- Continue when optional tools fail; fail only when selected profile marks a missing tool as required.

- [ ] **Step 6: Implement adapter parsing**

Implement:

```python
def parse_ccusage_json(path: Path) -> dict[str, Any]
def parse_otel_jsonl(path: Path) -> dict[str, Any]
```

Both functions summarize numeric usage and event categories only.

- [ ] **Step 7: Add CLI commands**

Add:

```bash
context-fixer collect --project /path/to/repo --profile full --run-dir .context-fixer/runs/latest --format json
context-fixer tools doctor --project /path/to/repo --format markdown
context-fixer tools list --format json
context-fixer usage import ccusage.json --repo /path/to/repo --format json
context-fixer otel import codex-otel.jsonl --repo /path/to/repo --format json
```

- [ ] **Step 8: Verify**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3.11 -m unittest discover -s tests -v
```

Expected: all tests pass.

## Phase 5: Local History Store

**Purpose:** Persist sanitized audit results so the complete product can show history, trends, and cross-session comparisons without re-reading sensitive payload files.

**Depends on:** `add-local-history-store` approved.

### Task 5.1: Add SQLite Store

**Files:**
- Create: `src/context_fixer/store.py`
- Modify: `src/context_fixer/analyzer.py`
- Modify: `src/context_fixer/cli.py`
- Modify: `tests/test_context_fixer.py`

- [ ] **Step 1: Write failing store test**

Add:

```python
def test_audit_save_persists_sanitized_history_snapshot(self) -> None:
    repo, codex_home, session = self.fixture()
    store = repo.parent / "context-fixer.db"
    status, output = self.run_cli_capture(
        [
            "audit",
            "--project", str(repo),
            "--codex-home", str(codex_home),
            "--session", str(session),
            "--session-only",
            "--save",
            "--store", str(store),
            "--format", "json",
        ],
        cache_home=repo.parent / "cache",
        claude_tap_path=None,
    )
    self.assertEqual(status, 0)
    self.assertTrue(store.exists())
    history_status, history_output = self.run_cli_capture(
        ["history", "--project", str(repo), "--store", str(store), "--format", "json"],
        cache_home=repo.parent / "cache",
        claude_tap_path=None,
    )
    data = json.loads(history_output)
    self.assertEqual(history_status, 0)
    self.assertEqual(len(data["snapshots"]), 1)
    self.assertIn("top_offenders", data["snapshots"][0])
    self.assertNotIn("SECRET_USER_PROMPT", history_output)
```

- [ ] **Step 2: Verify it fails**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3.11 -m unittest tests.test_context_fixer.ContextFixerTests.test_audit_save_persists_sanitized_history_snapshot -v
```

Expected: fails because `--save`, `--store`, and `history` are missing.

- [ ] **Step 3: Implement `store.py`**

Implement these functions:

```python
def default_store_path() -> Path
def init_store(path: Path) -> None
def save_snapshot(path: Path, report: dict[str, Any]) -> str
def list_snapshots(path: Path, repo: str | None = None, limit: int = 50) -> list[dict[str, Any]]
def load_snapshot(path: Path, snapshot_id: str) -> dict[str, Any]
```

Schema requirements:

- `snapshots(id, generated_at, repo, severity, policy_status, source_of_truth, max_input_tokens, max_context_pct, report_json)`.
- `report_json` stores the already sanitized report object only.
- Schema includes `schema_version`.
- No table stores prompt bodies, tool args, command output, file contents, or trace payload bodies.

- [ ] **Step 4: Add CLI flags and command**

Add:

```bash
context-fixer audit --project /path/to/repo --session-only --save --store .context-fixer/context-fixer.db
context-fixer history --project /path/to/repo --store .context-fixer/context-fixer.db --format json
```

- [ ] **Step 5: Verify**

Run targeted test and full suite.

Expected: all tests pass.

## Phase 6: Interactive Web Dashboard

**Purpose:** Deliver the full Web version the user requested: an interactive local browser dashboard, not a desktop app and not just an MVP static report.

**Depends on:** `add-web-dashboard` approved and dependency approval for React/Vite package installation.

### Task 6.1: Add Dashboard API Projection

**Files:**
- Create: `src/context_fixer/dashboard.py`
- Create: `src/context_fixer/web.py`
- Modify: `src/context_fixer/cli.py`
- Modify: `tests/test_context_fixer.py`

- [ ] **Step 1: Write failing dashboard projection test**

Add:

```python
def test_dashboard_projection_contains_complete_web_sections(self) -> None:
    repo, codex_home, session = self.fixture()
    report = analyze_context(repo=repo, codex_home=codex_home, sessions=[session])
    from context_fixer.dashboard import build_dashboard
    dashboard = build_dashboard(report, history=[])
    self.assertIn("overview", dashboard)
    self.assertIn("baseline", dashboard)
    self.assertIn("session_growth", dashboard)
    self.assertIn("timeline", dashboard)
    self.assertIn("top_offenders", dashboard)
    self.assertIn("recommendations", dashboard)
    self.assertIn("history", dashboard)
    self.assertTrue(dashboard["privacy"]["bodies_omitted"])
    self.assertNotIn("SECRET_USER_PROMPT", json.dumps(dashboard, ensure_ascii=False))
```

- [ ] **Step 2: Implement `build_dashboard`**

`build_dashboard(report)` returns:

```python
{
    "overview": {...},
    "baseline": {...},
    "session_growth": {...},
    "timeline": {...},
    "top_offenders": [...],
    "recommendations": [...],
    "data_sources": {...},
    "history": [...],
    "privacy": {"bodies_omitted": True},
}
```

- [ ] **Step 3: Add local dashboard server**

Implement `context_fixer.web` with:

```python
def serve_dashboard(repo: Path, store: Path | None, host: str, port: int, open_browser: bool) -> int
```

Server endpoints:

- `GET /` serves the built Web dashboard shell.
- `GET /api/dashboard` returns sanitized dashboard JSON.
- `GET /api/history` returns sanitized history snapshots.
- `GET /api/snapshot/<id>` returns a saved sanitized report snapshot.

- [ ] **Step 4: Add CLI commands**

Add:

```bash
context-fixer dashboard serve --project /path/to/repo --session-only --port 8765
context-fixer dashboard export --project /path/to/repo --session-only --output dashboard.html
context-fixer dashboard data --project /path/to/repo --session-only --format json
```

- [ ] **Step 5: Verify Python side**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3.11 -m context_fixer dashboard data --project . --session-only --latest-sessions 1 --format json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3.11 -m context_fixer dashboard export --project . --session-only --latest-sessions 1 --output /tmp/context-fixer-dashboard.html
test -s /tmp/context-fixer-dashboard.html
```

Expected: JSON contains dashboard sections and HTML file exists.

### Task 6.2: Build React Web Dashboard

**Files:**
- Create: `web/dashboard/package.json`
- Create: `web/dashboard/index.html`
- Create: `web/dashboard/src/main.tsx`
- Create: `web/dashboard/src/App.tsx`
- Create: `web/dashboard/src/api.ts`
- Create: `web/dashboard/src/styles.css`
- Modify: `src/context_fixer/web.py`
- Modify: `tests/test_context_fixer.py`

- [ ] **Step 1: Dependency approval checkpoint**

Before creating or installing packages, ask the user to approve these development dependencies:

```json
{
  "@vitejs/plugin-react": "current stable",
  "vite": "current stable",
  "typescript": "current stable",
  "react": "current stable",
  "react-dom": "current stable",
  "lucide-react": "current stable"
}
```

Expected: user approves Web dashboard dependencies. If not approved, fall back to a no-dependency HTML/JS dashboard and record the deviation.

- [ ] **Step 2: Scaffold Web dashboard**

Create a React app under `web/dashboard/` with these views:

- Overview: severity, policy status, peak context, source of truth, data-source health.
- Baseline: AGENTS, Skills, MCP, hooks, workflow context.
- Sessions: saved snapshots and latest session telemetry.
- Timeline: growth events, compactions, request trace events.
- Top Offenders: sortable offender table.
- Recommendations: governance and budget actions.
- Settings: local paths, store path, privacy note.

- [ ] **Step 3: Add frontend tests or build verification**

Run:

```bash
cd web/dashboard
npm install
npm run build
```

Expected: production build succeeds and emits static assets.

- [ ] **Step 4: Wire built assets into Python server**

`context_fixer.web` serves `web/dashboard/dist` in development checkout. If assets are missing, it prints a clear build instruction and exits non-zero for `dashboard serve`.

- [ ] **Step 5: Verify with CLI smoke**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3.11 -m context_fixer dashboard serve --project . --session-only --latest-sessions 1 --port 8765 --no-open
```

Expected: server starts and logs local URL. Stop it after confirming startup.

## Phase 7: Guided Governance Remediation

**Purpose:** Complete the governance loop by generating reviewable plans and applying only explicitly approved config changes with backups.

**Depends on:** `add-guided-governance-remediation` approved.

### Task 7.1: Generate Remediation Plans

**Files:**
- Create: `src/context_fixer/remediation.py`
- Modify: `src/context_fixer/cli.py`
- Modify: `tests/test_context_fixer.py`

- [ ] **Step 1: Write failing remediation plan test**

Add:

```python
def test_remediation_plan_is_dry_run_and_sanitized(self) -> None:
    repo, codex_home, session = self.fixture()
    output = repo.parent / "remediation.json"
    status, text = self.run_cli_capture(
        [
            "remediate", "plan",
            "--project", str(repo),
            "--codex-home", str(codex_home),
            "--session", str(session),
            "--session-only",
            "--output", str(output),
        ],
        cache_home=repo.parent / "cache",
        claude_tap_path=None,
    )
    self.assertEqual(status, 0)
    plan = json.loads(output.read_text(encoding="utf-8"))
    self.assertEqual(plan["mode"], "dry_run")
    self.assertFalse(plan["mutates_files"])
    self.assertIn("operations", plan)
    self.assertNotIn("SECRET_USER_PROMPT", json.dumps(plan, ensure_ascii=False))
```

- [ ] **Step 2: Implement plan generation**

Operations may include:

- `agents_extract_section`: move long workflow prose suggestion into a skill/doc target.
- `mcp_profile_toggle`: propose `enabled=false` or profile placement for heavy MCP servers.
- `skill_locality`: propose moving low-frequency global skill guidance to project-local docs.
- `hook_install`: propose safe hook collector TOML.
- `command_policy`: propose shell output limiting recipes.

No operation writes files during `plan`.

- [ ] **Step 3: Add CLI command**

Add:

```bash
context-fixer remediate plan --project /path/to/repo --session-only --output remediation.json
```

- [ ] **Step 4: Verify**

Run targeted test and full suite.

Expected: all tests pass.

### Task 7.2: Apply Explicit Remediation Plans

**Files:**
- Modify: `src/context_fixer/remediation.py`
- Modify: `src/context_fixer/cli.py`
- Modify: `tests/test_context_fixer.py`

- [ ] **Step 1: Write failing apply test**

Add:

```python
def test_remediation_apply_requires_known_operations_and_creates_backups(self) -> None:
    repo, codex_home, _session = self.fixture()
    plan = repo.parent / "remediation.json"
    backup_dir = repo / ".context-fixer" / "backups"
    plan.write_text(json.dumps({
        "version": 1,
        "mode": "dry_run",
        "operations": [
            {
                "id": "hook-collector",
                "type": "hook_install",
                "target": ".codex/config.toml",
                "content": "[[hooks.PostToolUse]]\nmatcher = \"^Bash$\"\n",
            }
        ],
    }), encoding="utf-8")
    status, _ = self.run_cli_capture(
        ["remediate", "apply", str(plan), "--project", str(repo), "--backup-dir", str(backup_dir)],
        cache_home=repo.parent / "cache",
        claude_tap_path=None,
    )
    self.assertEqual(status, 0)
    self.assertTrue((repo / ".codex" / "config.toml").exists())
    self.assertTrue(backup_dir.exists())
```

- [ ] **Step 2: Implement safe apply**

Rules:

- Refuse unknown operation types.
- Refuse absolute paths outside the project or Codex home.
- Create backups before each file write.
- Print a changed-file summary.
- Never apply raw prompt, trace, file, or command-output bodies.

- [ ] **Step 3: Add CLI command**

Add:

```bash
context-fixer remediate apply remediation.json --project /path/to/repo --backup-dir .context-fixer/backups
```

- [ ] **Step 4: Verify**

Run full suite and a dry-run/apply smoke on a temporary fixture project.

Expected: tests pass and backups are created.

## Phase 8: Workflow Integration and Packaging Polish

**Purpose:** Make the full workflow easy to use from Codex, package scripts, and project-local docs.

**Depends on:** `package-context-fixer-workflow-integration` approved.

### Task 8.1: Update Skill and README Workflows

**Files:**
- Modify: `README.md`
- Modify: `skills/context-fixer/SKILL.md`
- Modify: `pyproject.toml` only if new console scripts are needed
- Modify: `tests/test_context_fixer.py`

- [ ] **Step 1: Update command matrix**

Document:

```bash
context-fixer audit --project . --trace .traces/codex-request.jsonl
context-fixer audit --project . --session-only --hook-events ~/.cache/context-fixer/hooks/events.jsonl
context-fixer audit --project . --session-only --save --store .context-fixer/context-fixer.db
context-fixer history --project . --store .context-fixer/context-fixer.db
context-fixer dashboard serve --project . --session-only --store .context-fixer/context-fixer.db --port 8765
context-fixer dashboard export --project . --session-only --output .context-fixer/dashboard.html
context-fixer usage import ccusage.json --repo . --format markdown
context-fixer otel import codex-otel.jsonl --repo . --format json
context-fixer remediate plan --project . --session-only --output remediation.json
context-fixer remediate apply remediation.json --project . --backup-dir .context-fixer/backups
context-fixer recommend --project . --session-only --format markdown
context-fixer doctor --project .
context-fixer-hook post-tool-use
```

- [ ] **Step 2: Add docs verification test**

Add a test that reads README and skill docs and asserts the command names are present:

```python
self.assertIn("context-fixer dashboard serve", readme)
self.assertIn("context-fixer history", readme)
self.assertIn("context-fixer remediate plan", readme)
self.assertIn("context-fixer usage import", readme)
self.assertIn("context-fixer-hook post-tool-use", skill)
```

- [ ] **Step 3: Verify**

Run full suite.

Expected: all tests pass.

### Task 8.2: Final Verification and Checkpoint

**Files:**
- Modify: `.planning/STATE.md`
- Create: `.planning/checkpoints/YYYY-MM-DD-verification_passed-full-context-fixer-plan.md`
- Update: relevant `openspec/changes/*/tasks.md`

- [ ] **Step 1: Run full verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3.11 -m unittest discover -s tests -v
python3.11 -m py_compile src/context_fixer/*.py src/codex_context_lens/*.py
openspec validate add-governance-recommendation-engine --strict
openspec validate ingest-hook-audit-events --strict
openspec validate add-managed-external-tool-orchestration --strict
openspec validate add-local-history-store --strict
openspec validate add-web-dashboard --strict
openspec validate add-guided-governance-remediation --strict
openspec validate package-context-fixer-workflow-integration --strict
```

Expected: tests pass, compile passes, all OpenSpec changes valid.

- [ ] **Step 2: Run CLI smoke checks**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3.11 -m context_fixer audit --project . --session-only --latest-sessions 1
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3.11 -m context_fixer audit --project . --session-only --latest-sessions 1 --save --store /tmp/context-fixer.db
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3.11 -m context_fixer history --project . --store /tmp/context-fixer.db --format json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3.11 -m context_fixer report --project . --session-only --latest-sessions 1 --format markdown --output /tmp/context-fixer-report.md
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3.11 -m context_fixer dashboard data --project . --session-only --latest-sessions 1 --format json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3.11 -m context_fixer dashboard export --project . --session-only --latest-sessions 1 --output /tmp/context-fixer-dashboard.html
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3.11 -m context_fixer remediate plan --project . --session-only --latest-sessions 1 --output /tmp/context-fixer-remediation.json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3.11 -m context_fixer recommend --project . --session-only
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3.11 -m context_fixer doctor --project .
```

Expected: every command exits 0 and reports are written where requested.

- [ ] **Step 3: Record checkpoint**

Checkpoint must include:

- changed files summary;
- commands and results;
- unresolved risks;
- next action;
- whether `/compact` is recommended.

## Out of Scope

These items are not part of the complete Web product route:

- TypeScript/Node rewrite of the analysis engine.
- Tauri desktop app.
- Live proxy or automatic claude-tap capture.
- Silent or implicit edits to `AGENTS.md`, Skills, MCP config, hooks, or Codex profiles.
- Running unmanaged background collectors outside a user-selected `context-fixer collect --profile ...` flow.

SQLite persistence, React Web dashboard, and explicit remediation apply are included in this complete route. If Tauri or live capture is requested later, create a separate OpenSpec change with a dependency, migration, and privacy review.

## Self-Review

- Spec coverage: FR-1 through FR-8 are covered by current baseline plus Phases 2-8. Complete-version success criteria are covered by governance recommendations, hook ingestion, SQLite history, Web dashboard, adapter imports, guided remediation, and skill/plugin workflow docs.
- Placeholder scan: no unresolved placeholders are present in the implementation tasks.
- Type consistency: planned report keys are `governance`, `usage`, existing `budget`, existing `activity`, and existing `data_sources`; planned CLI additions are `history`, `dashboard serve/export/data`, `usage import`, `otel import`, `remediate plan/apply`, and `--hook-events`.
- Privacy check: every phase keeps body omission as a test requirement.
- OpenSpec check: every user-visible behavior phase has a named OpenSpec change before implementation.

## Execution Gate

Do not start implementation until the user confirms this revised complete Web product plan:

1. **Complete Web Product:** implement phases in order, one OpenSpec change at a time, including SQLite history, React Web dashboard, and explicit remediation.
2. **Complete Without Node:** implement the full Python backend, SQLite history, and no-dependency Web dashboard if React/Vite dependencies are not approved.
3. **Pause:** archive current verified changes before starting the complete product route.
