## ADDED Requirements

### Requirement: Native Git transport and GitHub control plane are independent
DevFlow SHALL classify native Git remote operations separately from GitHub API or UI control-plane operations before selecting a tool or evaluating credentials.

#### Scenario: GitHub CLI is unauthenticated but SSH remote is reachable
- **GIVEN** `gh` has no authenticated GitHub host
- **AND** the configured Git remote is reachable through SSH
- **WHEN** DevFlow evaluates an explicitly authorized push
- **THEN** it uses native Git transport readiness rather than `gh` authentication state
- **AND** it does not route the push through GitHub CLI

#### Scenario: GitHub control-plane write is requested
- **WHEN** DevFlow needs to create a pull request, release, or repository setting through the GitHub control plane
- **THEN** it evaluates the dedicated GitHub control-plane authorization and credentials
- **AND** it does not infer that authorization from native Git transport readiness

### Requirement: Git transport preflight is read-only and fail-closed
DevFlow SHALL provide a machine-readable preflight that inspects the selected repository, remote, and branch through native Git without mutating local or remote Git state.

#### Scenario: Remote branch is reachable
- **WHEN** `git ls-remote` resolves the selected remote and branch
- **THEN** the preflight reports `GIT_TRANSPORT_READY`
- **AND** it reports `requiresGh` as false
- **AND** it reports that no push was attempted
- **AND** it preserves the separate explicit authorization requirement for push

#### Scenario: Remote is missing or unreachable
- **WHEN** the selected remote is not configured or the native Git probe fails
- **THEN** the preflight reports `GIT_TRANSPORT_BLOCKED`
- **AND** it exposes a sanitized diagnostic
- **AND** it does not call `gh` or attempt a push

#### Scenario: Remote contains credential material
- **WHEN** the configured remote URL contains HTTP user information, a query, or a fragment
- **THEN** the preflight redacts those values from all machine-readable output and diagnostics

### Requirement: GitHub authentication recovery is bounded
DevFlow SHALL prevent repeated GitHub CLI authentication recovery from blocking or replacing an independently available native Git route.

#### Scenario: GitHub control-plane authentication remains unavailable
- **GIVEN** one GitHub control-plane diagnosis and at most one applicable remediation attempt have failed
- **WHEN** the requested GitHub platform effect still requires credentials
- **THEN** DevFlow stops retrying that platform path
- **AND** it reports the exact remaining external-effect gate
- **AND** any separately authorized native Git operation continues through native Git preflight

### Requirement: Legacy combined side-effect ID remains compatible
DevFlow SHALL retain the legacy `git.push_pr` side-effect policy entry while new workflow routing uses `git.push` and `github.control_plane_write`.

#### Scenario: Existing caller submits the legacy effect
- **WHEN** side-effect authorization evaluates `git.push_pr`
- **THEN** the policy continues to return an explicit-user-request decision
- **AND** new DevFlow guidance does not use the legacy effect for native Git or GitHub control-plane routing
