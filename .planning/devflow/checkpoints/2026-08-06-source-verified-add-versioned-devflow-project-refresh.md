# Checkpoint: Versioned DevFlow Project Refresh Source Verified

- Timestamp: `2026-08-06T16:51:30+08:00`
- Change: `add-versioned-devflow-project-refresh`
- Stage: `awaiting_human`
- Progress: `31/37` tasks
- Boundary: source implementation verified; generated release not synchronized

## Verified Outcome

DevFlow now has a versioned project-refresh contract and one deterministic
project writer. The `dev-flow-refresh` Skill remains the global-first
orchestrator; the existing `plugin_project_migration.py` CLI owns sealed plan,
explicit apply, fresh verify, and receipt-bound rollback. Supported legacy
configuration moves through project schema `0 -> 1` while unrelated settings,
historical data, active AGENTS guidance, custom Skills, and ambiguous content
remain protected.

Future project-facing changes are covered by an executable Project Refresh
Impact gate. The live result is `changed_covered`; refresh revision is `1` and
the tracked-input SHA-256 is
`6a6e6a4afcc4896e41d0311708be997da4c59e68b727574fb788484f2e207c22`.

## Verification Receipt

- Focused project/compatibility/legacy/orchestrator tests: `113/113`.
- Focused release-impact/packaged-runtime/smoke tests: `79/79`.
- Complete DevFlow development tests: `499/499`.
- Project Refresh schema/impact matrix: `9/9`.
- Both changed Skills pass quick validation.
- AI-native plan lint passes.
- Workflow-state validation passes with no issues or warnings.
- Strict current-change validation passes.
- Strict validation of all OpenSpec artifacts: `60 passed, 0 failed`.
- `git diff --check` passes.
- Independent review findings on receipt forgery, current-state sync, retained
  recovery, symlink ancestry, stable JSON, central tree writes, and release
  impact were resolved and regression-covered.

Detailed commands and outputs are recorded in
`openspec/changes/add-versioned-devflow-project-refresh/evidence/verification.md`.

## Scope and Integrity

All task-owned source edits are inside the approved development write set. The
pre-existing unrelated diff in
`openspec/changes/separate-git-transport-from-github-auth/evidence/implementation.md`
remains untouched with digest
`156697b2fda831afd5ac23a2e5ce8ffc98d18836f345535915bded204d812ba6`.

No checked-in release, installed cache, consumer project, active AGENTS file,
legacy path, dependency, archive, Git history, remote, or publication surface
was changed.

## Generated Release Gate

The read-only release plan is `pending` with no selection error. Its exact
source-copy drift and complete build-owned output declaration are recorded in
the verification evidence. The separately authorized promotion command is:

```bash
PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -B \
  dev/plugins/dev-flow/scripts/release_promotion_gate.py \
  --repo . --target dev-flow --apply --json
```

`current_stage` and `current_change.status` are both `awaiting_human`;
`release_allowed` remains `false`. Do not run the command until the user
explicitly authorizes generated release sync. Cache refresh, consumer-project
apply, AGENTS merge, cleanup, archive, commit, push, PR, and publication retain
their independent gates.

## Next Action

Ask one concrete question: may Codex authorize and execute the generated
`plugins/dev-flow/**` release synchronization above, then continue through
release parity, release-target Plugin Eval, and final verification without
refreshing caches or migrating consumer projects?
