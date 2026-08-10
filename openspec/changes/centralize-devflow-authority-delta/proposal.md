## Why

DevFlow currently treats several ordinary technical failures and every external-effect boundary as if they necessarily require a new human decision. That fragments authority across continuation, Stop, side-effect, cleanup, guidance, and release paths, causing long-running approved work to stop repeatedly even when no permission or material-risk delta exists.

## What Changes

- Introduce one fail-closed authority-delta resolver that distinguishes missing authority from deterministic repair, evidence drift, an active owner, approved `AUTO_CLEAN`, and a bounded `CONTINUE_WITH_MINIMAL_GUARD`.
- Permit local, reversible, semantics-preserving work within an approved Goal/OpenSpec/write set to continue automatically, while requiring every genuine `AWAIT_HUMAN` decision to name concrete missing authority and atomically keep both workflow state markers aligned.
- Add standing Goal execution authority for predeclared model/provider/task/credential-policy/cost-policy boundaries, while treating run ids, attempt receipts, evidence refresh, refreeze, and same-authority retry as technical execution identity rather than one-use human permission.
- Add a Goal/OpenSpec-bound Milestone External Effects Contract that can grant standing authority once for an exact verified milestone instead of reopening gates for commit, push, publish, cache refresh, and current-project refresh.
- Add a recoverable, idempotent milestone state machine for candidate freeze, exact stage/commit, fast-forward-only push/readback, deterministic tag-bound publication/readback, and named refresh with source/release/published/cache/project identity proof.
- Establish a canonical stable DevFlow release policy and tag-bound GitHub Actions publication path. This non-breaking capability release deterministically advances the plugin from the `0.3.x` line to `0.4.0`, uses tag `dev-flow-v0.4.0`, publishes only declared assets, and never overwrites a conflicting tag or Release.
- Consolidate Stop/orchestrator/doctor/hook, skill, template, root policy, generated-project, side-effect, and release guidance around the resolver and standing-contract model without making hooks or doctors mutating writers.
- Add a regression matrix covering ordinary continuation, minimal guard, approved non-blocking deferral, standing model execution, exact task-owned cleanup, drift and ambiguity, real authority deltas, repeated-gate suppression, invalidation, remote and release failures, idempotent recovery, unnamed-consumer rejection, and a dependency-ordered long-run simulation with more than ten steps and zero false Human Gates.
- Advance the Project Refresh Impact contract for changed guidance and packaged runtime bytes without changing `.dev-flow.json`, project schema, historical files, or existing-project authority. Projects with no standing milestone contract remain default-deny.

## Capabilities

### New Capabilities

- `authority-delta-resolution`: A single executable policy for determining whether approved work continues, uses a minimal guard, performs exact `AUTO_CLEAN`, fails closed for repair, or requires concrete new human authority.
- `milestone-external-effects`: A sealed, recoverable standing-authority contract and state machine for exact commit, fast-forward-only push, deterministic publication, readback, and named post-publication refresh.

### Modified Capabilities

- `incidental-finding-lifecycle`: External, destructive, migration, dependency, and deviation labels no longer imply a Human Gate by themselves; escalation depends on a material authority or risk delta, while exact task-owned generated cleanup remains governed by its sealed lifecycle.

## Impact

- Affected development source: DevFlow policy, continuation, Git, release, refresh, validation, doctor/hook, CLI, schemas, fixtures, tests, skills, docs, root control-plane guidance, and project templates under `dev/plugins/dev-flow/` plus release-generation scripts.
- Affected generated release: `plugins/dev-flow/`, deterministic runtime artifacts, DevFlow manifest version, and the release marketplace entry already pointing at `plugins/dev-flow`.
- Affected repository release control plane: a new tag-bound GitHub Actions workflow and stable DevFlow release notes/assets for `0.4.0`.
- Compatibility: no production dependency, no workflow-mode variant, no project configuration key, no silent authorization widening, no historical-file cleanup, and no automatic refresh of any unnamed plugin or consumer project. Project Refresh Impact advances only because generated guidance and packaged resolver behavior change.
- External effects for this change are permitted only after the exact milestone contract, all validators, release-target Plugin Eval, independent P0/P1 review, candidate-manifest, index, divergence, and readback gates pass. PR, merge, force-push, OpenSpec archive, unrelated publication, and unnamed refresh remain excluded.
