## Context

The completed `separate-git-transport-from-github-auth` change established that
`git.push` and `github.control_plane_write` are independent effects. It also
bounded local GitHub CLI authentication recovery. The remaining gap is path
selection inside `github.control_plane_write`: a release operation currently
has no durable rule preferring an already-reviewed repository workflow over a
new local `gh auth` flow.

The Game Design Workshop `v0.1.1` publication demonstrated the target route:
SSH pushed an annotated tag, the tagged source contained a least-privilege
release workflow, the repository `GITHUB_TOKEN` created and read back the
Release, and local plugin promotion waited for remote confirmation.

### Capability Evidence

- GitHub documents tag filters for `push` workflow triggers in Workflow Syntax:
  `https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax`.
- GitHub documents repository workflow authentication through `GITHUB_TOKEN`:
  `https://docs.github.com/en/actions/tutorials/authenticate-with-github_token`.
- GitHub recommends least-privilege workflow token permissions:
  `https://docs.github.com/en/actions/reference/security/secure-use`.
- Local DevFlow already provides native Git preflight, separate
  `git.push`/`github.control_plane_write` authorization, and one diagnosis plus
  one remediation limit for direct GitHub control-plane recovery.

## Goals / Non-Goals

**Goals:**

- Prefer SSH/native Git for the immutable tag transport when it is configured
  and reachable.
- Prefer a validated repository GitHub Actions workflow for deterministic,
  tag-bound release publication.
- Keep release authorization separate from tag-push authorization.
- Make direct `gh` a bounded fallback instead of the first mandatory path.
- Require publication readback before local install, cache, deployment, or
  other promotion work.
- Encode the route in machine-readable source behavior and public guidance.

**Non-Goals:**

- Automatically create or edit a GitHub Actions workflow.
- Generalize Actions-first routing to pull requests or repository settings.
- Authenticate GitHub CLI, install credentials, or change repository settings.
- Authorize commit, tag, push, release, local promotion, archive, or cleanup.
- Promote `dev/plugins/dev-flow` into `plugins/dev-flow`, refresh an installed
  cache, or alter the current Skills CLI release gate.

## Skill Routing Ledger

| Field | Status | Reason |
| --- | --- | --- |
| artifact-status | final | The user selected the Actions-first strategy and no product decision remains open. |
| capability-research | required/used | Official GitHub workflow, token, and least-privilege guidance plus current DevFlow code were inspected. |
| decision-resolution | required/used | Scope is limited to deterministic tag-bound release publication and bounded fallbacks. |
| decision-grilling | skipped | No unresolved tradeoff remains after the explicit user direction. |
| implementation-planning | required/used | This design defines behavior, slices, tests, rollback, and external-effect boundaries. |
| architecture-guidance | skipped | The existing Git workflow helper, policy, skills, and test seams are sufficient. |
| domain-language-modeling | skipped | No new business-domain model is introduced. |
| openspec-routing | required/used | This changes public workflow and fallback behavior, so Full OpenSpec applies. |

## Decisions

### 1. Model Actions as an execution path, not new authority

The existing `github.control_plane_write` effect remains the publication
authorization. A tag-triggered route additionally requires explicit
`git.push` authorization because pushing the trigger is a separate external
effect. Machine-readable route metadata will expose both required effects.

Alternative: add a `github.actions.release` side-effect ID. Rejected because it
would duplicate publication authority and weaken the existing default-deny
model.

### 2. Apply Actions-first only to deterministic tag-bound releases

The release operation will advertise this order:

1. `github_actions`
2. `github_cli`
3. `human_web`

Pull requests and repository settings retain their existing direct GitHub
control-plane routes. Actions is eligible only when a reviewed workflow exists
in the immutable trigger commit and repository policy permits it.

Alternative: prefer Actions for every GitHub write. Rejected because PR and
settings operations often require interactive context, different permissions,
or organization policy that a release workflow does not satisfy.

### 3. Fail closed before pushing the trigger

The Actions path requires:

- workflow bytes present in the commit that the tag will reference;
- an immutable reviewed tag target and expected release identity;
- versioned release notes or equivalent reviewed release input;
- explicit, least-privilege workflow permissions;
- conflict checks that reject an existing incompatible tag or Release;
- post-create readback of tag, target, draft/prerelease state, and publication
  identity.

The workflow may use the repository `GITHUB_TOKEN`; local `gh` authentication
is not a prerequisite for this path.

### 4. Bound fallbacks and preserve the trigger

If the Actions path is unavailable before tag push, DevFlow may use an already
authenticated direct `gh` path or stop for a named-human web action. Direct
GitHub recovery retains the existing one-diagnosis, one-remediation limit.

If the tag push succeeds but the workflow fails, DevFlow preserves the tag and
stops publication recovery against that immutable identity. It must not delete
or retarget the tag automatically.

### 5. Separate publication readback from local promotion

Action completion is not inferred from a successful tag push. DevFlow requires
machine-readable Release readback when credentials allow it. For a private
repository without a usable read API, a named human may confirm the successful
workflow run and non-draft Release as an explicit gate. Local promotion remains
blocked until that readback is recorded.

## Completion Contract

- Release route metadata prefers `github_actions`, then `github_cli`, then
  `human_web`, while preserving separate `git.push` and
  `github.control_plane_write` effects.
- Non-release GitHub operations do not gain Actions-first behavior.
- Public guidance requires workflow-in-trigger-commit, least privilege,
  conflict checks, immutable tag preservation, publication readback, and a
  local-promotion gate.
- Focused route and guidance tests pass.
- The complete source-only DevFlow suite, strict OpenSpec validation, workflow
  validation, and `git diff --check` pass.
- Existing unrelated worktree changes remain untouched.

## Capability Slices

1. **Planning slice:** add the new capability contract and strict validation.
2. **Contract slice:** add RED route and public-guidance tests.
3. **Runtime slice:** add Actions-first release metadata without changing
   authorization effects or non-release routes.
4. **Guidance slice:** update the Git routing reference, orchestration,
   verification, root, and generated project contracts.
5. **Verification slice:** run focused and complete source checks and record
   release drift without promoting generated assets.

## Execution Ledger

| Slice | Owner | Write set | Evidence | Human gate |
| --- | --- | --- | --- | --- |
| Planning | main agent | this OpenSpec change | strict change validation | none |
| Contract | main agent | focused DevFlow source tests | observed RED then GREEN | none |
| Runtime | main agent | `dev/plugins/dev-flow/scripts/workflow_git.py` | focused route tests | no external effect |
| Guidance | main agent | dev docs/skills, root/generated AGENTS | public-surface tests | none |
| Verification | main agent | change evidence/tasks only | source suite, strict OpenSpec, workflow, diff | release promotion remains separate |

## Acceptance Criteria and Validation Commands

```bash
PYTHONDONTWRITEBYTECODE=1 python3.12 dev/plugins/dev-flow/tests/test_git_transport_preflight.py
PYTHONDONTWRITEBYTECODE=1 python3.12 dev/plugins/dev-flow/tests/test_project_orchestrator.py
PYTHONDONTWRITEBYTECODE=1 python3.12 dev/scripts/run_devflow_prepromotion_tests.py
openspec validate prefer-github-actions-for-release-publication --type change --strict
openspec validate --all --strict
PYTHONDONTWRITEBYTECODE=1 python3.12 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo . --json
git diff --check
```

## Critical Path

Plan and validate the change, add RED tests, implement route metadata and
guidance, run focused and broad source verification, and stop before release
promotion or Git effects.

## Incidental Finding Budget

Only one bounded test or documentation guard required for this contract may be
added. Existing Skills CLI promotion work, generated release drift, installed
cache state, and unrelated findings remain outside this change.

## Escalation Triggers

Stop for a new dependency, side-effect ID, workflow writer, credential
mutation, GitHub setting change, release promotion, overlapping user edits, or
any requirement to alter the current Skills CLI release gate.

## Risks / Trade-offs

- **A repository workflow may be disabled or permission-restricted.** -> Check
  current repository capability before tag mutation and fall back without an
  authentication loop.
- **A green workflow can still publish the wrong identity if it lacks
  readback.** -> Require exact tag, target, and Release state verification.
- **A tag-triggered workflow couples push and publication timing.** -> Require
  both external effects to be authorized and preserve the tag on failure.
- **Current generated release assets will drift.** -> Report drift only;
  promotion remains behind the existing release gate.

## Rollback

Revert the new route metadata, guidance, tests, and this change. No migration,
credential, repository setting, remote Git state, or user data is changed.

## Open Questions

None.
