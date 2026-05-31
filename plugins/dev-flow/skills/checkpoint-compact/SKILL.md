---
name: checkpoint-compact
description: Use when checkpointing or preparing /compact at workflow boundaries.
---

# Checkpoint Compact Gate

Use after durable context is written at a major boundary. Compact is blocking only when the work will continue in the current thread.

## Procedure

1. Read `AGENTS.md`, `.planning/STATE.md`, relevant phase files, and the active OpenSpec change.
2. Run `scripts/create_checkpoint.py --repo <repo> --boundary <boundary> --next-stage <stage> --json`.
3. Run `scripts/validate_checkpoint.py --repo <repo> --checkpoint <file> --json`.
4. Run `scripts/compact_recommendation.py --repo <repo> --boundary <boundary> --next-stage <stage> --json`.
5. If recommended, ask for `/compact`; otherwise continue with the updated state because compact is optional or not needed.

## Preconditions

Checkpoint only when durable context, next action or stopping-point intent, risks, and verification are recorded. If validation fails, keep compaction blocked.

## Status

`pending` blocks continuation until compact completes or a skip reason is recorded. `not_needed` means the checkpoint is a stable stopping point and state is already updated. Skills cannot execute interactive `/compact`.
