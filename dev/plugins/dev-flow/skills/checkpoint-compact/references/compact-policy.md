# Compact Policy

Checkpoint saves facts. Compact cleans context.

Use `/compact` only after a checkpoint validates successfully and the checkpoint is a continuation gate. If the task is at a stable stopping point, review/archive boundary, or handoff boundary, state is already updated and compact is optional before any future thread.

When an external API or harness compacts context for a pending continuation gate, record the result with `scripts/record_compact_result.py`.
Store the compact payload exactly as returned, then continue from repository files instead of treating the
payload as authoritative state.

Do not treat compacted conversation as the source of truth. Restart from:

- `AGENTS.md`
- `.planning/devflow/STATE.md`
- `.planning/devflow/checkpoints/<checkpoint>.md`
- `.planning/devflow/compact-results/<checkpoint>.json` when compact was required or externally recorded
- relevant phase files
- relevant OpenSpec change files
