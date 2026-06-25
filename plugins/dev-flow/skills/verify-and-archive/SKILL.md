---
name: verify-and-archive
description: Use when verifying work or gating OpenSpec archive.
---

# Verify And Archive

Use when implementation appears complete or the user asks to finish, archive, or ship.

## Verification

Use `superpowers:verification-before-completion` before claiming work is complete, fixed, passing, ready to commit, or ready for PR. Use `gsd-verify-work` when the completed work belongs to a GSD phase.

Before completion claims, verify:

- Target State is implemented.
- Completion Contract is checked.
- Capability Slices are done or blocked with reasons.
- Execution Ledger is updated.
- Acceptance Criteria and Validation Commands have recorded evidence.
- `TASK_LEDGER.md`, `EVIDENCE_TEMPLATE.md`, and `REVIEW_CHECKLIST.md` have
  evidence, review, and knowledge-update decisions for contract-first work.
- Superpowers specs, plans, SDD reports, and review notes have been promoted to
  canonical OpenSpec, GSD, DevFlow ledger, or verification artifacts when they
  are used as completion evidence.

Record commands with:

```bash
python3 scripts/record_verification.py --repo <repo> --command "<command>" --result pass --json
```

## Archive Gate

Archive only when spec, plan, implementation, verification, and state gates are
clear. DevFlow separates archive readiness from approval:

```bash
python3 scripts/archive_status.py --repo <repo> --change <change> --json
```

Default policy is `confirm-on-risk`. If the user explicitly asked to archive and
the status report is ready with no risks, proceed with `openspec-archive-change`.
If the report lists risks such as incomplete tasks, dirty unrelated paths,
missing artifacts, failed gates, or spec sync uncertainty, summarize them and
ask for confirmation before archive.

After verification, archive, or phase ship, create a checkpoint with
`checkpoint-compact`.
