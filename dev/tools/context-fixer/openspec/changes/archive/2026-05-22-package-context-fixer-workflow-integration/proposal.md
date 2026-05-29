## Why

After the full product features land, Context Fixer needs docs and skill
workflows that describe the official managed collection, dashboard, history,
and remediation flows. Users should not have to infer the workflow from low
level commands.

## What Changes

- Update README with complete Web product workflows.
- Update `skills/context-fixer/SKILL.md` with managed collection, dashboard,
  history, external tool, and remediation guidance.
- Add docs checks so command examples do not drift.
- Keep Context Fixer naming and privacy posture consistent.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `current-system`: update documentation and skill integration for complete
  product workflows.

## Impact

- Affected docs: `README.md`, `skills/context-fixer/SKILL.md`.
- Affected tests: docs command coverage in `tests/test_context_fixer.py`.
- Public CLI: no new CLI beyond the feature changes this docs change describes.
- Privacy: docs must emphasize local-first, managed, sanitized behavior.
