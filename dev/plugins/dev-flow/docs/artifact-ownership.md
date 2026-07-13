# Artifact Ownership

DevFlow keeps canonical behavior and evidence separate from optional
methodology-provider drafts. Git tracking is reported independently; ignored
planning artifacts must not be described as checked in.

## Canonical

- OpenSpec: `openspec/changes/<change-id>/`
- DevFlow state and support artifacts: `.planning/devflow/**`
- DevFlow evidence: `.planning/devflow/verification/**`
- GSD, only when selected: root `.planning/STATE.md`, `PROJECT.md`,
  `ROADMAP.md`, `config.json`, `phases/**`, `milestones/**`, `todos/**`, and
  root `codebase/**`
- Contract ledger: `TASK_LEDGER.md`
- Engineering policy: `ENGINEERING_POLICY.md`

## Provider Draft Or Method Evidence

- `docs/superpowers/specs/*`
- `docs/superpowers/plans/*`
- Superpowers SDD reports
- Superpowers review notes
- Matt grilling, diagnosis, architecture, and review notes outside an approved
  canonical write set
- personal Codex memories

Draft or method evidence must be promoted into a canonical target before it can
satisfy verification, archive, or release readiness.

Provider availability or skill invocation never satisfies canonical evidence
by itself. Only the approved DevFlow/OpenSpec promoter may write canonical
planning or review output; provider routing remains subject to the
machine-readable side-effect policy and the outer user/project authority.
