## ADDED Requirements

### Requirement: Deterministic tag-bound releases prefer repository Actions
DevFlow SHALL prefer a validated repository GitHub Actions workflow over local
GitHub CLI authentication when publishing a deterministic release from an
immutable tag.

#### Scenario: Eligible repository workflow is available
- **GIVEN** the reviewed trigger commit contains the release workflow
- **AND** repository policy permits the workflow and required token permission
- **WHEN** DevFlow selects a release publication path
- **THEN** it selects `github_actions` before `github_cli`
- **AND** it reports that local `gh` authentication is not required
- **AND** it preserves separate authorization for `git.push` and `github.control_plane_write`

#### Scenario: Operation is not a deterministic release
- **WHEN** DevFlow selects a path for a pull request or repository setting
- **THEN** it does not apply the Actions-first release route
- **AND** it preserves the existing GitHub control-plane behavior

### Requirement: Actions publication fails closed before trigger mutation
DevFlow SHALL require reviewed workflow identity and least-privilege
publication controls before an Actions-triggering tag push.

#### Scenario: Workflow is absent from the trigger commit
- **WHEN** the proposed tag target does not contain the reviewed publication workflow
- **THEN** DevFlow blocks the Actions path before tag push
- **AND** it does not infer that a workflow on another branch can publish the tag safely

#### Scenario: Publication inputs or permissions are not verified
- **WHEN** release identity, conflict checks, reviewed notes, or required workflow permissions are unresolved
- **THEN** DevFlow blocks the Actions path
- **AND** it reports the missing publication prerequisite

### Requirement: Direct GitHub fallbacks are ordered and bounded
DevFlow SHALL use authenticated GitHub CLI only after an eligible Actions path
is unavailable and SHALL use a named-human web operation only when automated
control-plane paths remain unavailable.

#### Scenario: Actions is unavailable and GitHub CLI is authenticated
- **WHEN** the deterministic Actions path is not eligible
- **AND** direct GitHub credentials are already usable
- **THEN** DevFlow may select `github_cli`
- **AND** it retains the existing release authorization and readback requirements

#### Scenario: Automated control-plane paths are unavailable
- **GIVEN** Actions is not eligible
- **AND** one diagnosis and at most one applicable GitHub CLI remediation have failed
- **WHEN** publication still requires a GitHub control-plane write
- **THEN** DevFlow stops automated retries
- **AND** it records a named-human web action as the explicit remaining gate

### Requirement: Publication readback gates local promotion
DevFlow SHALL not treat tag transport or workflow dispatch as proof that a
Release was published.

#### Scenario: Machine-readable Release readback succeeds
- **WHEN** DevFlow can read the resulting Release through an authenticated control-plane path
- **THEN** it verifies the expected tag and target
- **AND** it verifies that the Release is published, non-draft, and non-prerelease
- **AND** only then may separately authorized local promotion begin

#### Scenario: Private repository readback requires a human
- **GIVEN** the repository is private
- **AND** no usable authenticated read path is available
- **WHEN** the workflow has run
- **THEN** DevFlow records an explicit named-human confirmation gate for the successful run and published Release
- **AND** local promotion remains blocked until that confirmation is recorded

### Requirement: Failed publication preserves immutable Git identity
DevFlow SHALL preserve a pushed immutable release tag when the corresponding
GitHub Actions publication fails.

#### Scenario: Tag push succeeds but the workflow fails
- **WHEN** the immutable tag exists remotely and the publication workflow fails or cannot be read back
- **THEN** DevFlow does not delete or retarget the tag automatically
- **AND** it stops local promotion
- **AND** it routes recovery against the same reviewed tag identity
