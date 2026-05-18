# Compact Policy

Checkpoint saves facts. Compact cleans context.

Use `/compact` only after a checkpoint validates successfully. If `/compact` is unavailable, start a new session and provide the checkpoint file as handoff context.

When an external API or harness compacts context, record the result with `scripts/record_compact_result.py`.
Store the compact payload exactly as returned, then continue from repository files instead of treating the
payload as authoritative state.

Do not treat compacted conversation as the source of truth. Restart from:

- `AGENTS.md`
- `.planning/STATE.md`
- `.planning/checkpoints/<checkpoint>.md`
- `.planning/compact-results/<checkpoint>.json`
- relevant phase files
- relevant OpenSpec change files
