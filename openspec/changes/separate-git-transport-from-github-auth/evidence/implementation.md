# Implementation Evidence

## Capability Evidence

- Date: 2026-07-19
- `origin`: `git@github.com:cYz26/cy-codex-skills.git`
- `git ls-remote --heads origin main`: exit 0, resolved `621b205a2227609ffeeb448bee24a2624202f65e`
- `gh auth status`: exit 1, no authenticated GitHub hosts
- Conclusion: native Git SSH transport and GitHub CLI authentication are observably independent on the current machine.

## TDD Evidence

RED was observed before implementation:

- `test_git_transport_preflight.py`: five failing/erroring tests because the runtime helpers and CLI did not exist.
- `test_methodology.py ...test_git_push_and_github_control_plane_have_independent_authorization`: failed because only `git.push_pr` existed.
- `test_project_orchestrator.py ...test_git_transport_and_github_control_plane_guidance_are_independent`: failed across all four required guidance surfaces.
- The malformed credential URL guard initially raised `ValueError` while parsing a non-numeric port.

GREEN after implementation:

```text
test_git_transport_preflight.py: 7 tests passed
test_methodology.py: 33 tests passed
test_project_orchestrator.py: 44 tests passed
py_compile workflow_git.py git_transport_preflight.py: passed
```

The live preflight reported `GIT_TRANSPORT_READY`, transport `ssh`,
`requiresGh: false`, and `pushAttempted: false` while `gh auth status` remained
unavailable.

## Broad Verification

- `PYTHONDONTWRITEBYTECODE=1 python3.12 dev/scripts/run_devflow_prepromotion_tests.py`: 335 tests across 21 source modules passed.
- Post-promotion source discovery: 369 tests passed.
- Authoritative release-package discovery: 5 tests passed.
- `python3 -B plugins/dev-flow/scripts/verify_release_runtime.py --plugin-root plugins/dev-flow --json`: `ok: true`, runtime manifest and packaged archive verified.
- `openspec validate --all --strict`: 42 items passed, 0 failed.
- `git diff --check`: passed.
- Plugin Eval development diagnostic: 68/100 (D). The development root scans 153 Python files and reports pre-existing whole-tree token-budget, complexity, and coverage warnings; the new preflight was refactored from 149 lines to a 74-line coordinator with bounded helpers.
- Plugin Eval authoritative release package: 86/100 (B), 0 failures and three static token-budget warnings for trigger, invoke, and deferred guidance. The warnings are bounded residual optimization work and do not indicate a functional or packaging failure.
- Release promotion completed and a fresh release-gate check reports `status: current`, with no changed, stale, or missing managed files or outputs.
- Guidance compaction reduced the development active-budget estimate from 13,261 to 12,921 tokens without weakening the public contract tests.

## Authorization Boundaries

The user explicitly authorized release promotion, a direct native-Git push to
`main`, and a local DevFlow cache/project-skill refresh. Release promotion has
completed; commit, push, and local refresh are the next separately observable
effects. No pull request, archive, legacy cleanup, unrelated-plugin refresh,
or credential mutation is authorized. Native Git SSH transport is the push
route; GitHub CLI authentication is not required.

## Residual Risks

- Plugin Eval retains three non-blocking static token-budget warnings in the
  release package.
- The preflight proves remote reachability without mutating the remote; the
  actual push can still be rejected if `origin/main` advances after preflight.
- The pre-existing local `TASK_LEDGER.md` change is outside this change set and
  must remain unstaged and uncommitted.
