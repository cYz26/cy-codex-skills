---
name: verify-and-archive
description: Use when verifying work or gating OpenSpec archive.
---

# Verify And Archive

Use when implementation appears complete or the user asks to finish, archive, or ship.

## Verification

Use `superpowers:verification-before-completion` before claiming work is complete, fixed, passing, ready to commit, or ready for PR. Use `gsd-verify-work` when the completed work belongs to a GSD phase.

Record commands with:

```bash
python3 scripts/record_verification.py --repo <repo> --command "<command>" --result pass --json
```

## Archive Gate

Archive only when spec, plan, implementation, verification, and state gates are clear. Then use `openspec-archive-change`. After verification, archive, or phase ship, create a checkpoint with `checkpoint-compact`.
