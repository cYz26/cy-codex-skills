---
name: checkpoint-compact
description: Use when checkpointing or preparing /compact at workflow boundaries.
---

# Checkpoint Compact Gate

Use after durable context is written at a major boundary. Compact protects
recoverability; it should not interrupt otherwise-continuable work solely to ask
for manual `/compact`.

A phase label does not prove terminality. Review, verification, handoff,
new-thread, blank, and placeholder next-stage values continue by default. Use
an explicit no-continuation option only for a real overall stopping point. When
approved work remains, the outcome is `CHECKPOINT_AND_CONTINUE`, not a request
for phase confirmation.

## Procedure

1. Read `AGENTS.md`, `.planning/devflow/STATE.md`, the active OpenSpec change,
   and its execution ledger.
2. Run `scripts/create_checkpoint.py --repo <repo> --boundary <boundary> --next-stage <stage> --json`.
3. Run `scripts/validate_checkpoint.py --repo <repo> --checkpoint <file> --json`.
4. Run `scripts/compact_recommendation.py --repo <repo> --boundary <boundary> --next-stage <stage> --json`.
5. If recommended, prefer `/compact` at a stable boundary. If the runtime can
   auto-compact or the task can continue safely from the checkpoint, continue
   and let PostCompact recovery record completion when it happens.
6. Return to `project-orchestrator` and execute the recorded next action; do not
   end the user request merely because the checkpoint was written.

## Preconditions

Checkpoint only when durable context, next action or stopping-point intent,
risks, and verification are recorded. If checkpoint validation fails, block
continuation until the checkpoint is repaired.

## Status

`pending` means compact is recommended and recoverable; it is an advisory
continuation signal, not a default human-interruption gate. `not_needed` means
the checkpoint is durable and compact is unnecessary; it does not independently
declare overall completion. `failed` or `blocked` means the compact/checkpoint
gate needs action. Skills cannot execute interactive `/compact`.
