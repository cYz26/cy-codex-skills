# Artifact Ownership

DevFlow keeps workflow state in checked-in canonical artifacts.

## Canonical

- OpenSpec: `openspec/changes/<change-id>/`
- GSD: `.planning/phases/*/PLAN.md`
- DevFlow state: `.planning/STATE.md`
- DevFlow evidence: `.planning/verification/*`
- Contract ledger: `TASK_LEDGER.md`
- Engineering policy: `ENGINEERING_POLICY.md`

## Draft Or Method Evidence

- `docs/superpowers/specs/*`
- `docs/superpowers/plans/*`
- Superpowers SDD reports
- Superpowers review notes
- personal Codex memories

Draft or method evidence must be promoted into a canonical target before it can
satisfy verification, archive, or release readiness.
