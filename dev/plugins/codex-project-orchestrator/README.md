# codex-project-orchestrator

Local Codex plugin for setting up and maintaining a Codex-first development workflow.

It combines:

- GSD-style roadmap, phase, and milestone planning.
- OpenSpec-style change proposal, requirements, tasks, and archive gates.
- Superpowers-style engineering discipline for clarification, planning, TDD, review, and verification.
- Soft hook warnings for unplanned edits, incomplete verification, and checkpoint compact gates.

## Install

The release plugin is registered in:

```bash
/path/to/cy-codex-skills/.agents/plugins/marketplace.json
```

The release plugin root is:

```bash
/path/to/cy-codex-skills/plugins/codex-project-orchestrator
```

The development plugin root is:

```bash
/path/to/cy-codex-skills/dev/plugins/codex-project-orchestrator
```

Use `.agents/plugins/marketplace.dev.json` when local testing needs the development copy.

## Usage

Check required dependencies before use:

```bash
python3 scripts/check_dependencies.py \
  --plugin-root /path/to/cy-codex-skills/plugins/codex-project-orchestrator \
  --repo /path/to/repo \
  --json
```

Required:

- Python runtime and Codex CLI available.
- `superpowers` is not globally enabled.
- GSD, OpenSpec, and Superpowers skills are not globally active.
- Superpowers is installed in the Codex plugin cache, with `brainstorming`, `writing-plans`, `test-driven-development`, and `verification-before-completion`.
- Target repo has GSD local Codex skills and agents under `.codex/`.
- Target repo has OpenSpec local Codex skills under `.codex/`.
- Target repo has project-local Superpowers skills under `.codex/skills/`.
- Target repo has project-local orchestrator skills under `.codex/skills/`.

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
This keeps Superpowers, GSD, and OpenSpec out of the global default context while making them available inside repos that opt into this orchestrator.

Codex currently resolves project-local skills reliably, while project-local plugin enable sections are not treated as runtime plugin activation. For that reason the activation script does not rely on `.codex/config.toml` plugin sections for dependency visibility.

After activation, open or reload Codex from the target repo so the project-local skills are included in the session prompt.

Recommended for development:

- `plugin-eval@openai-curated` enabled, with `evaluate-plugin`

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
- Hooks default to `warn`; set `.codex-project-orchestrator.json` in the target repo to opt into `off` or `block`.

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
python3 -m unittest discover -s /path/to/cy-codex-skills/dev/plugins/codex-project-orchestrator/tests
```

Run release preflight:

```bash
python3 /path/to/cy-codex-skills/plugins/codex-project-orchestrator/scripts/codex_plugin_preflight.py \
  --plugin-root /path/to/cy-codex-skills/plugins/codex-project-orchestrator \
  --marketplace /path/to/cy-codex-skills/.agents/plugins/marketplace.json \
  --repo /path/to/repo \
  --codex-home /path/to/codex-home \
  --config /path/to/codex-home/config.toml \
  --json
```
