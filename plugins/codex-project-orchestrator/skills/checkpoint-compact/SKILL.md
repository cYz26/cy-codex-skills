---
name: checkpoint-compact
description: Use when creating a durable checkpoint or preparing /compact at a workflow boundary.
---

# Checkpoint Compact Gate

Use after durable context is written and before another major stage.

## Procedure

1. Read `AGENTS.md`, `.planning/STATE.md`, relevant phase files, and the active OpenSpec change.
2. Run `scripts/create_checkpoint.py --repo <repo> --boundary <boundary> --next-stage <stage> --json`.
3. Run `scripts/validate_checkpoint.py --repo <repo> --checkpoint <file> --json`.
4. Run `scripts/compact_recommendation.py --repo <repo> --boundary <boundary> --next-stage <stage> --json`.
5. If recommended, ask for `/compact`; otherwise record completed/skipped status.

## Preconditions

Checkpoint only when durable context, next action, risks, and verification are recorded. If validation fails, keep compaction blocked.

## Status

`pending` blocks the next major stage until compact completes or a skip reason is recorded. Skills cannot execute interactive `/compact`.
