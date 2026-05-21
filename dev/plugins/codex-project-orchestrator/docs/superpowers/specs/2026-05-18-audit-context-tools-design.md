# Audit Context Tools Design

## Goal

Add an orchestrator feature that audits long-lived Codex plugin and skill context, explains cleanup opportunities, recommends project-relevant tools, and can execute selected cleanup or installation actions only after user authorization.

## User Experience

The first command is read-only:

```bash
/opt/homebrew/bin/python3.11 scripts/audit_context_tools.py \
  --repo /path/to/repo \
  --codex-home /path/to/codex-home \
  --json
```

It returns a report with inventory, project signals, findings, recommendations, and action proposals. The second command consumes a saved report:

```bash
/opt/homebrew/bin/python3.11 scripts/apply_context_tool_actions.py \
  --plan audit-report.json \
  --action disable-global-plugin-superpowers-openai-curated \
  --apply \
  --json
```

Without `--apply`, the apply command is a dry-run. With `--apply`, it creates backups before changing global config and only executes the selected actions.

## Architecture

Create `scripts/workflow_context_tools.py` as the single implementation module. It owns inventory scanning, project signal detection, recommendation generation, and action application helpers. Add two CLI wrappers that only parse arguments and render JSON or text.

The audit is advisory and separate from the existing dependency gate. This keeps current preflight return codes stable while giving users a deeper context hygiene report when they ask for it.

## Data Model

The report has these top-level fields:

- `ok`: true unless an unexpected fatal error prevents the audit.
- `contextPressure`: `low`, `medium`, or `high`.
- `codexHome`, `config`, `repo`: paths used for the audit.
- `inventory`: global plugins, global skills, project skills, installed cache skills, and source catalog tools.
- `projectSignals`: language, framework, and platform hints from local files.
- `findings`: human-readable issues or notes.
- `recommendations`: explanation records grouped by cleanup, install, or discovery.
- `actions`: stable executable proposals.

Action records include:

- `id`
- `type`
- `title`
- `reason`
- `safety`
- `requiresAuthorization`
- `payload`

## Safety

The first version never deletes plugin cache directories or global skill files. Cleanup means setting config entries to disabled. Installation means copying a known installed skill into `<repo>/.codex/skills/<skill>`. Unsupported marketplace plugin installation remains a recommendation, not an executable action.

## Testing

Use temporary Codex homes and repos. Tests should verify inventory, project-relevant install recommendations, dry-run behavior, authorized config updates with backup creation, and selected project-local skill installation.
