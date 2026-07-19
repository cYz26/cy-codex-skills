## Context

DevFlow has a single `git.push_pr` side-effect identifier even though Git transport and GitHub's API/UI control plane use different executables, credentials, and failure modes. Live capability evidence gathered on 2026-07-19 demonstrates the gap: `git ls-remote --heads origin main` succeeded against `git@github.com:cYz26/cy-codex-skills.git` while `gh auth status` exited 1 with no authenticated GitHub host.

The repair must preserve default-deny external-effect authorization. It must not infer permission to push from transport readiness, mutate credentials, perform a push during diagnosis, or add a new top-level continuation outcome.

## Target State

DevFlow determines whether an operation belongs to native Git transport or the GitHub control plane before selecting a tool. For an explicitly authorized push, it performs a bounded, read-only native Git preflight and uses the configured remote regardless of `gh` login state. GitHub API/UI operations remain separately credential-gated. Repeated `gh` recovery cannot consume the execution loop or block an independent Git-only operation.

## Goals / Non-Goals

**Goals:**

- Make the Git/GitHub capability boundary deterministic and testable.
- Expose a machine-readable, read-only Git transport preflight.
- Keep push and GitHub control-plane authorization independent and default-deny.
- Prevent repeated `gh` authentication remediation when the requested effect does not require `gh`.
- Propagate the behavior to generated project guidance and release packaging.

**Non-Goals:**

- Automatically push, commit, create a PR, release, or edit repository settings.
- Install or configure Git, SSH, credential helpers, or GitHub CLI credentials.
- Guarantee push acceptance, fast-forward status, or branch protection from a read-only reachability probe.
- Add a seventh `workflow_continuation` outcome.
- Remove the legacy `git.push_pr` policy ID in this change.

## Skill Routing Ledger

| Field | Status | Reason |
| --- | --- | --- |
| artifact-status | final | The user confirmed the systemic DevFlow optimization and no product choice remains open. |
| capability-research | required/used | Current local Git remote, `git ls-remote`, `gh auth status`, policy, skills, and tests were inspected. |
| decision-resolution | required/used | The user selected adding the proposed separation and fallback rule to DevFlow. |
| decision-grilling | skipped | There are no unresolved scope or behavior questions after the user's confirmation. |
| implementation-planning | required/used | This design defines target state, slices, evidence, rollback, and exact validation. |
| architecture-guidance | skipped | The existing side-effect policy and workflow helper boundaries are sufficient; no architecture alternative remains unresolved. |
| domain-language-modeling | skipped | This change does not introduce domain concepts beyond existing Git and external-effect terminology. |
| openspec-routing | required/used | The change modifies plugin workflow, error handling, and compatibility behavior, so Full OpenSpec is active. |

## Architecture Decisions

### 1. Separate capability and authorization effects before tool selection

Add `git.push` and `github.control_plane_write` to the side-effect policy. `git.push` requires an explicit user request; `github.control_plane_write` additionally requires usable platform credentials. Preserve `git.push_pr` as a compatibility alias, but do not use it in new guidance.

Alternative considered: rename `git.push_pr` in place. Rejected because existing integrations may still submit the legacy effect ID and the behavior can be introduced additively.

### 2. Use a native Git-only preflight

Extend `workflow_git.py` with transport classification, safe remote display, operation routing, and a preflight report. Add `git_transport_preflight.py` as a CLI wrapper. The probe runs `git ls-remote --heads <remote> <branch>` and never calls `gh`.

The report uses stable outcomes `GIT_TRANSPORT_READY` and `GIT_TRANSPORT_BLOCKED`, includes the remote transport and branch tips, states that push was not attempted, and names the still-required authorization. These are effect-level diagnostic statuses inside the existing `READY_FOR_EXTERNAL_EFFECT` workflow outcome.

Alternative considered: call `gh auth status` first for GitHub-hosted remotes. Rejected because it recreates the false dependency this change is removing.

### 3. Fail safely without leaking credentials

Remote URLs exposed in JSON are sanitized. HTTP(S) user information and query or fragment data are redacted, and command errors are scrubbed before reporting. Remote and branch inputs are validated before invoking Git. The implementation uses argument arrays without a shell.

### 4. Bound platform recovery and preserve independent progress

Generated and runtime guidance requires agents to diagnose a GitHub control-plane failure once and attempt at most one applicable remediation. If it remains unavailable, the platform effect stops as `AWAIT_HUMAN` or `READY_FOR_EXTERNAL_EFFECT`; an independently authorized native Git operation continues through its own preflight.

## Completion Contract

- Side-effect policy loads with independent `git.push` and `github.control_plane_write` entries while retaining `git.push_pr` compatibility.
- A local bare-remote fixture proves the preflight can resolve a branch through native Git and reports `requiresGh: false`.
- Missing or unreachable remotes fail closed without a push attempt.
- Credential-bearing remote URLs and errors are redacted.
- Public workflow guidance explicitly says a `gh` authentication failure is not Git transport evidence and enforces the bounded retry rule.
- Focused tests, the complete source-only suite, strict OpenSpec validation, and `git diff --check` pass.
- The resolved release package is evaluated only after the separate release-promotion authorization gate.

## Capability Slices

1. **Contract slice:** add failing tests for independent side effects, Git-only routing, redaction, and public guidance.
2. **Runtime slice:** implement the preflight helper and CLI with no external dependency.
3. **Guidance slice:** update orchestration, verification, root, and generated-project rules.
4. **Verification slice:** run focused and broad source checks, inspect release drift, and perform Plugin Eval at the authorized package boundary.

## Execution Ledger

| Slice | Owner | Write set | Evidence | Human gate |
| --- | --- | --- | --- | --- |
| Contract | main agent | `dev/plugins/dev-flow/tests/test_git_transport_preflight.py`, existing contract tests | Focused tests fail before runtime changes and pass after them | None; approved behavior scope |
| Runtime | main agent | `dev/plugins/dev-flow/scripts/workflow_git.py`, `git_transport_preflight.py`, side-effect policy | Local bare-remote and mocked failure tests | Actual push remains separately authorized |
| Guidance | main agent | DevFlow skills/docs, root and generated `AGENTS.md` | Text contract tests | None; approved behavior scope |
| Verification | main agent | OpenSpec evidence/tasks and read-only reports | Source suite, strict validation, diff check, Plugin Eval | Release promotion, commit, push, PR, and archive remain separately authorized |

## Acceptance Criteria and Validation Commands

```bash
PYTHONDONTWRITEBYTECODE=1 python3.12 dev/plugins/dev-flow/tests/test_git_transport_preflight.py
PYTHONDONTWRITEBYTECODE=1 python3.12 dev/plugins/dev-flow/tests/test_methodology.py
PYTHONDONTWRITEBYTECODE=1 python3.12 dev/plugins/dev-flow/tests/test_project_orchestrator.py
PYTHONDONTWRITEBYTECODE=1 python3.12 dev/plugins/dev-flow/scripts/git_transport_preflight.py \
  --repo . --remote origin --branch main --json
PYTHONDONTWRITEBYTECODE=1 python3.12 dev/scripts/run_devflow_prepromotion_tests.py
openspec validate --all --strict
git diff --check
```

## Risks / Trade-offs

- **A successful read-only probe does not guarantee a later push will satisfy branch protection or fast-forward rules.** The report describes transport readiness only and includes both local and remote tips for later diagnosis.
- **Retaining `git.push_pr` leaves a temporary compatibility surface.** New guidance and tests route only through the separated IDs; removal can occur in a separately approved breaking change.
- **Network probes can time out or trigger normal SSH credential prompts.** The helper uses a finite timeout and reports the failure without switching to `gh` or retrying indefinitely.
- **Release assets can drift from development source.** Read-only drift inspection is part of verification; release promotion remains behind its existing explicit authorization gate.

## Rollback

Revert the new helper/CLI, policy entries, guidance, and tests as one change. Because no credential, repository remote, dependency, continuation schema, or persistent user data changes, rollback requires no migration. The compatibility alias remains available throughout.

## Open Questions

None.
