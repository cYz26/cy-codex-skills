## 1. Contract and Regression Tests

- [x] 1.1 Add failing tests for independent side-effect IDs and legacy compatibility.
- [x] 1.2 Add failing native Git preflight tests for reachable, missing, and credential-bearing remotes.
- [x] 1.3 Add failing public-guidance tests for Git/GitHub separation and bounded recovery.

## 2. Runtime and Policy Implementation

- [x] 2.1 Add native Git operation routing, remote sanitization, and read-only transport preflight helpers.
- [x] 2.2 Add the `git_transport_preflight.py` JSON CLI without push or `gh` execution paths.
- [x] 2.3 Split new side-effect routing into `git.push` and `github.control_plane_write` while preserving `git.push_pr` compatibility.

## 3. Workflow Guidance

- [x] 3.1 Update project orchestration and verification guidance with native-Git-first routing and bounded GitHub recovery.
- [x] 3.2 Update root and generated-project `AGENTS.md` contracts so `gh` authentication failure never implies Git transport failure.

## 4. Verification and Release Boundary

- [x] 4.1 Run focused runtime, policy, and public-guidance tests.
- [x] 4.2 Run the complete source-only DevFlow suite, strict OpenSpec validation, and `git diff --check`.
- [x] 4.3 Inspect release drift and run Plugin Eval on the authoritative package allowed by the current release gate.
- [x] 4.4 Record final evidence, residual risks, and the separately authorized release/commit/push/archive boundaries.
