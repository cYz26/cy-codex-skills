---
name: context-tool-audit
description: Use when auditing context-heavy skills/plugins or project tool cleanup.
---

# Context Tool Audit

Use this skill when the user wants to inspect, reduce, or rebalance Codex plugin/skill context for a repo.

## Read-Only Audit

Generate a report first:

```bash
python3 scripts/audit_context_tools.py \
  --repo <repo> \
  --codex-home <codex-home> \
  --json > audit-report.json
```

Optional discovery sources:

```bash
--source-catalog /path/to/marketplace.json
--source-url https://example.com/marketplace.json
```

Review:

- `contextPressure`
- `findings`
- `recommendations`
- `actions`

## Apply After Authorization

Preview selected actions:

```bash
python3 scripts/apply_context_tool_actions.py \
  --plan audit-report.json \
  --action <action-id> \
  --json
```

Apply only after the user confirms the selected action ids:

```bash
python3 scripts/apply_context_tool_actions.py \
  --plan audit-report.json \
  --action <action-id> \
  --apply \
  --json
```

Use `--all-safe` only after showing the user the selected safe actions.

## Safety

- Default to read-only reports and dry-runs.
- Do not apply cleanup/install actions without explicit user authorization.
- Cleanup disables global config entries or global skill activation; it does not delete plugin caches or skill files.
- Installation copies known cached skills into `<repo>/.agents/skills/`.
