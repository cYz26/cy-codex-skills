# Implementation Evidence

## TDD Evidence

RED was observed before implementation:

- `test_git_transport_preflight.py`: 9 tests ran with one expected failure
  because the release route still required local `gh`.
- `test_project_orchestrator.py`: 45 tests ran with five expected guidance
  failures across the routing reference, project orchestration,
  verification, root guidance, and generated guidance.

GREEN after implementation:

```text
test_git_transport_preflight.py: 9 tests passed
test_project_orchestrator.py: 45 tests passed
```

The release route now reports `github_actions`, `github_cli`, and `human_web`
in order, keeps `git.push` separate from `github.control_plane_write`, and does
not add a side-effect ID or change pull-request and repository-settings routes.

## Source Verification

- `PYTHONDONTWRITEBYTECODE=1 python3.12
  dev/scripts/run_devflow_prepromotion_tests.py`: 338 tests across 21 source
  modules passed with no skips.
- `openspec validate prefer-github-actions-for-release-publication --type
  change --strict`: passed.
- `openspec validate --all --strict`: 56/56 repository items passed.
- `PYTHONDONTWRITEBYTECODE=1 python3.12
  dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo . --json`:
  passed with no issues or warnings. The existing Skills CLI release gate
  remains the active state and was not altered.
- `git diff --check`: passed.
- Completion capability diagnosis reported `change-review` and
  `completion-proof` ready.

## Plugin Eval

- Authoritative release counterpart `plugins/dev-flow`: 86/100, grade B,
  medium risk, 0 failures, 3 token-budget warnings.
- Development-source diagnostic `dev/plugins/dev-flow`: 68/100, grade D,
  high risk. Its failure and warnings come from the pre-existing full
  development-tree scan: 153 Python files, excessive deferred tokens, and
  whole-tree complexity/readability findings. The two changed skills remain
  within the evaluator's good line-count range.
- Optimization decision: keep the bounded release-routing guidance in the
  existing sections. Broader token-budget and source-tree complexity work is
  outside this change and is not required for the Actions-first contract.

## Release Drift

The explicitly authorized release promotion synchronized this change together
with the verified Skills CLI update. The immediate read-only release sync
returned `status: current` with no changed, missing, deleted, or stale files or
outputs.

Post-promotion verification passed:

- complete development discovery: 372/372;
- packaged release discovery: 5/5;
- runtime archive verification: `ok: true`, archive SHA-256
  `4f7d695c922eb97f94d037b06b01fd74a93ca7f45ac2a951bda01f1f5a45b600`;
- release-target Plugin Eval: 86/100, grade B, 0 failures and three bounded
  plugin-wide token-budget warnings.

## Scope And Authorization Boundaries

This change updates development-source route metadata, guidance, tests, and
OpenSpec evidence only. These pre-existing unrelated modifications were left
untouched:

- `dev/plugins/dev-flow/docs/dependency-provenance.json`
- `dev/plugins/dev-flow/tests/test_dependencies.py`
- `dev/plugins/dev-flow/tests/test_packaged_runtime.py`
- `openspec/changes/separate-git-transport-from-github-auth/evidence/implementation.md`

The user separately authorized release promotion, direct-main commit, SSH push,
and targeted local DevFlow refresh. Project migration, archive, tag creation,
GitHub Release publication, pull request creation, credential mutation,
unrelated plugin refresh, and cleanup remain unauthorized.

## Residual Risks

- Repository Actions eligibility still depends on the target repository
  containing and permitting a reviewed least-privilege release workflow.
- A successful tag push does not prove publication; publication readback or a
  named-human private-repository confirmation remains mandatory.
- The repository's historical `openspec/changes/` ignore rule requires this
  change to be included explicitly at the authorized commit boundary.
