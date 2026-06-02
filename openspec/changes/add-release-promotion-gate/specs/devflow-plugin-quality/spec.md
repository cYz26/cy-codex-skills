## ADDED Requirements

### Requirement: Release promotion sync runs at verified boundaries
DevFlow SHALL promote dev plugin and standalone skill runtime assets to release
counterparts only after development verification has been recorded.

#### Scenario: Verification has not passed
- **WHEN** the release promotion gate runs before `.planning/STATE.md` records `gates.verification_passed: true`
- **THEN** it performs no release sync
- **AND** it reports that promotion is not applicable yet

#### Scenario: Verification has passed
- **WHEN** the release promotion gate runs after `.planning/STATE.md` records `gates.verification_passed: true`
- **THEN** it syncs allowlisted runtime assets from `dev/plugins/<name>` to `plugins/<name>` when a release counterpart exists
- **AND** it syncs allowlisted runtime assets from `dev/skills/<name>` to `<name>` when a release counterpart exists
- **AND** it prompts for release validation before commit readiness

### Requirement: Release sync excludes dev-only artifacts
Release sync SHALL use allowlists and excludes so development-only artifacts do
not become part of release packages.

#### Scenario: Plugin runtime files are promoted
- **WHEN** release sync applies a dev plugin to its release counterpart
- **THEN** runtime files such as `.codex-plugin/`, `skills/`, `hooks.json`, `scripts/`, `assets/`, `agents/`, README, changelog, and license files are eligible for promotion
- **AND** `tests/`, `fixtures/`, `log/`, caches, generated reports, and scratch files are excluded unless explicitly shipped

#### Scenario: Asset metadata defines custom packaging
- **WHEN** an asset declares release sync metadata with excludes, build commands, or managed outputs
- **THEN** release sync honors those settings
- **AND** DevFlow uses metadata to generate packaged runtime outputs instead of copying raw script modules into release

### Requirement: Plugin Eval resolves release targets first
Plugin Eval readiness checks SHALL prefer release counterparts when they exist.

#### Scenario: Development plugin path is evaluated
- **WHEN** a caller asks for the Plugin Eval target of `dev/plugins/<name>`
- **THEN** DevFlow returns `plugins/<name>` when that release plugin exists
- **AND** it marks the target as release-preferred

#### Scenario: Development skill path is evaluated
- **WHEN** a caller asks for the Plugin Eval target of `dev/skills/<name>`
- **THEN** DevFlow returns `<name>` when that release skill exists
- **AND** direct dev-path evaluation remains diagnostic rather than the primary release readiness signal
