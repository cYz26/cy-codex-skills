# Checkpoint: OpenSpec Planned - add-capability-activity-log

Date: 2026-05-20 20:13:05 CST

## Scope

Add explicit sanitized capability activity reporting to Context Fixer.

## Artifacts

- `openspec/changes/add-capability-activity-log/proposal.md`
- `openspec/changes/add-capability-activity-log/design.md`
- `openspec/changes/add-capability-activity-log/specs/current-system/spec.md`
- `openspec/changes/add-capability-activity-log/tasks.md`

## Verification

- `openspec validate add-capability-activity-log --strict` passed.

## Next Action

Implement with tests first:

- session observed tool calls/results
- trace network activity categories
- request tool inventory
- configured plugin/skill/MCP inventory distinction
- text/HTML/JSON sanitization

## Risks

- Codex logs do not always expose first-class plugin/skill invocation events. The report must distinguish configured inventory from observed calls.
- Trace paths may include query strings; activity output must strip them.
