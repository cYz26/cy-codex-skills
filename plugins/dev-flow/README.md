# DevFlow

Local Codex plugin for setting up and maintaining a Codex-first development workflow.

It combines:

- GSD-style roadmap, phase, and milestone planning.
- OpenSpec-style change proposal, requirements, tasks, and archive gates.
- Superpowers-style engineering discipline for clarification, planning, TDD, review, and verification.
- AI-native Target State, Capability Slice, Execution Ledger, Completion Contract, and validation-loop planning.
- Runtime context-health checks for repeated failures, diff spread, stale validation, stale goals, and subagent handoff recommendations.
- Soft hook warnings for unplanned edits, incomplete verification, context health, and checkpoint compact gates.

## Install

The release plugin is registered in:

```bash
/path/to/cy-codex-skills/.agents/plugins/marketplace.json
```

The release plugin root is:

```bash
/path/to/cy-codex-skills/plugins/dev-flow
```

The development plugin root is:

```bash
/path/to/cy-codex-skills/dev/plugins/dev-flow
```

Use `.agents/plugins/marketplace.dev.json` when local testing needs the development copy.

## Usage

Check required dependencies before use:

```bash
python3 scripts/check_dependencies.py \
  --plugin-root /path/to/cy-codex-skills/plugins/dev-flow \
  --repo /path/to/repo \
  --json
```

Required:

- Python runtime and Codex CLI available.
- GSD, legacy OpenSpec, and Superpowers skills are not globally active.
- Superpowers is installed in the Codex plugin cache, with `brainstorming`, `writing-plans`, `test-driven-development`, and `verification-before-completion`.
- Target repo has GSD local Codex skills and agents under `.codex/`.
- Target repo has OpenSpec project setup (`openspec/config.yaml`) from `openspec init --tools codex`; legacy project-local OpenSpec skills are reported only as optional diagnostics.
- Target repo has project-local Superpowers skills under `.codex/skills/`.
- Target repo has project-local orchestrator skills under `.codex/skills/`.

Recommended:

- Keep `superpowers` disabled as a global plugin so project-local workflow rules stay obvious. DevFlow reports global Superpowers activation as a warning, not a blocking dependency failure.

Activate dependencies in one target repo:

```bash
python3 scripts/activate_project_dependencies.py --repo /path/to/repo --json
```

That command uses the official local installers:

```bash
openspec init --tools codex /path/to/repo --force
npx -y get-shit-done-cc@latest --codex --local --profile=standard
```

It also links or copies the required Superpowers skills and this plugin's skills into `/path/to/repo/.codex/skills/`.
This keeps the required workflow skills available inside repos that opt into this orchestrator while avoiding reliance on global skill installation.

Codex currently resolves project-local skills reliably, while project-local plugin enable sections are not treated as runtime plugin activation. For that reason the activation script does not rely on `.codex/config.toml` plugin sections for dependency visibility.

After activation, open or reload Codex from the target repo so the project-local skills are included in the session prompt.

Recommended for development:

- `plugin-eval@openai-curated` enabled, with `evaluate-plugin`

## AI-native Planning

Use `ai-native-tech-plan` when creating technical plans, implementation plans, architecture plans, Codex execution plans, workflow plans, or plans intended to prevent partial delivery.

The skill defaults to complete Target State delivery unless the user explicitly asks for a prototype, demo, POC, MVP, or partial target. It combines existing dependencies this way:

- Superpowers: brainstorming, writing plans, TDD, and verification-before-completion.
- OpenSpec: behavior-level proposal, design, specs, tasks, and archive gates.
- GSD: roadmap and workflow sequencing. GSD phases are governance containers, not technical completion boundaries.

Generated plans should include Target State, Completion Contract, Capability Slices, Execution Ledger, Acceptance Criteria, Validation Commands, Goal Mode Prompt, Continue Prompt, and Review Checklist sections.

Lint a generated plan:

```bash
python3 scripts/lint_ai_plan.py .ai/tasks/example.md
```

Policy documents that intentionally discuss human-style planning terms can include:

```md
<!-- ai-native-plan-lint: allow-human-planning-terms -->
```

## Context Tool Audit

As a skill, invoke `context-tool-audit` when you want Codex to run the audit workflow, explain the report, and ask before applying selected actions.

Audit globally enabled plugins, global skills, project-local skills, installed plugin-cache skills, and project-relevant tool recommendations:

```bash
/opt/homebrew/bin/python3.11 scripts/audit_context_tools.py \
  --repo /path/to/repo \
  --codex-home /path/to/codex-home \
  --json > audit-report.json
```

The report is read-only. It includes `findings`, `recommendations`, and stable `actions` that can be reviewed before anything changes.

Preview selected actions without changing files:

```bash
/opt/homebrew/bin/python3.11 scripts/apply_context_tool_actions.py \
  --plan audit-report.json \
  --action disable-global-plugin-superpowers-openai-curated \
  --json
```

Apply selected actions after review:

```bash
/opt/homebrew/bin/python3.11 scripts/apply_context_tool_actions.py \
  --plan audit-report.json \
  --action disable-global-plugin-superpowers-openai-curated \
  --apply \
  --json
```

Apply operations create timestamped backups before editing `config.toml`. First-version cleanup disables global config entries or installs known cached skills into the project; it does not delete global skill files or plugin cache directories.

## Context Health Check

Use `context-health-check` when a long-running task may be drifting, repeating failed commands, expanding diff scope, missing validation evidence, or approaching a checkpoint/compact boundary.

DevFlow records sanitized runtime metadata through hooks under:

```text
.dev-flow/context-health/events.jsonl
```

The event log is runtime telemetry and should not be committed. Durable derived reports are written under:

```text
.planning/context-health/reports/
```

Run an immediate check:

```bash
python3 scripts/context_health_check.py --repo /path/to/repo --write-report --json
```

Import older Codex local history on a best-effort basis:

```bash
python3 scripts/context_health_import_codex_sessions.py \
  --repo /path/to/repo \
  --codex-home ~/.codex \
  --json
```

Summarize collected history:

```bash
python3 scripts/context_health_history.py --repo /path/to/repo --json
```

Reports include risk, confidence, decision, runtime signals, repo truth, workflow truth, Goal Mode Prompt guidance, subagent recommendations, and minimal next context. Missing runtime-only metrics are marked `unknown` and lower confidence instead of being treated as healthy.

DevFlow does not execute `/goal` or spawn subagents from scripts or hooks. It generates Goal Mode prompts and scoped subagent delegation prompts for the active Codex agent or user to apply when supported.

## AgentKB

The Markdown-first knowledge-base workflow is packaged separately as the `agent-kb` plugin. DevFlow can be used alongside it for planning and verification, but DevFlow no longer owns KB scripts, skills, or hook behavior.

Use `agent-kb` when a project should maintain a Git-reviewable Markdown knowledge base. Obsidian is supported there as the `obsidian-compatible-markdown` editor profile, and Codex is one packaged agent adapter.

Set up a repository:

```bash
python3 scripts/activate_project_dependencies.py --repo /path/to/repo --json
python3 scripts/scaffold_workflow.py --repo /path/to/repo --json
```

Detect project mode:

```bash
python3 scripts/detect_project_mode.py --repo /path/to/repo --json
```

Create a change:

```bash
python3 scripts/create_change.py --repo /path/to/repo --change-id add-search --title "Add search" --type new-feature --json
```

Validate workflow state:

```bash
python3 scripts/validate_workflow_state.py --repo /path/to/repo --json
```

Record verification:

```bash
python3 scripts/record_verification.py --repo /path/to/repo --command "python3 -m pytest" --result pass --json
```

Run workflow doctor:

```bash
python3 scripts/doctor_workflow.py --repo /path/to/repo --write-report --json
```

Maintain local Codex plugins and skills:

```bash
python3 scripts/codex_auto_update_plugins_skills.py --apply --json
```

Dry-run mode omits `--apply`. The updater refreshes clean Git mirrors,
OpenAI curated plugin caches, OpenAI curated skills, and known external
tooling such as Agent Reach, Lark, GSD, and OpenSpec. It skips local copies
that differ from their previous upstream mirror instead of overwriting them.

## Safety

- Existing `AGENTS.md` is not overwritten by default. The scaffold writes `AGENTS.md.generated` instead.
- Setup scripts do not edit production code.
- OpenSpec archive is never automatic.
- Hooks default to `warn`; set `.dev-flow.json` in the target repo to opt into `off` or `block`.
- Existing `.codex-project-orchestrator.json` hook config files are still read as a legacy fallback when `.dev-flow.json` is absent.

```json
{
  "hook": {
    "mode": "warn"
  }
}
```

## Checkpoint Compact Gate

Create durable checkpoints at major workflow boundaries and recommend context compaction before continuing.

The sequence is:

1. Persist project state to `.planning/` and `openspec/`.
2. Create a checkpoint under `.planning/checkpoints/`.
3. Validate that decisions, risks, verification results, and next action are recorded.
4. Recommend `/compact` in Codex CLI, or use API compaction in external orchestration.
5. Continue by rereading repo files, not relying on chat memory.

Create a checkpoint:

```bash
python3 scripts/create_checkpoint.py --repo /path/to/repo \
  --boundary project_setup_completed \
  --next-stage feature_intake \
  --current-goal "Initialize workflow" \
  --completed-work "Created workflow scaffold" \
  --risk "No validation baseline yet" \
  --json
```

Validate it:

```bash
python3 scripts/validate_checkpoint.py --repo /path/to/repo \
  --checkpoint .planning/checkpoints/<checkpoint>.md --json
```

Check compact policy:

```bash
python3 scripts/compact_recommendation.py --repo /path/to/repo \
  --boundary project_setup_completed --next-stage feature_intake --json
```

Record compact completion from an external API or harness:

```bash
python3 scripts/record_compact_result.py --repo /path/to/repo \
  --checkpoint .planning/checkpoints/<checkpoint>.md \
  --status completed \
  --source responses_api \
  --raw-result '<compacted context payload>' \
  --json
```

Record an explicit skip:

```bash
python3 scripts/record_compact_result.py --repo /path/to/repo \
  --status skipped \
  --skip-reason "Context remained small after checkpoint validation." \
  --json
```

The script stores compact records under `.planning/compact-results/` and updates `.planning/STATE.md`.
If a harness calls `/responses/compact`, pass the returned compact payload through `--raw-result` or
`--result-file`; the plugin stores that payload as-is instead of treating it as a source of truth.

Compaction is never a substitute for durable state files.

## Development

Run tests:

```bash
python3 -m unittest discover -s /path/to/cy-codex-skills/dev/plugins/dev-flow/tests
```

Run release preflight:

```bash
python3 /path/to/cy-codex-skills/plugins/dev-flow/scripts/codex_plugin_preflight.py \
  --plugin-root /path/to/cy-codex-skills/plugins/dev-flow \
  --marketplace /path/to/cy-codex-skills/.agents/plugins/marketplace.json \
  --repo /path/to/repo \
  --codex-home /path/to/codex-home \
  --config /path/to/codex-home/config.toml \
  --json
```
