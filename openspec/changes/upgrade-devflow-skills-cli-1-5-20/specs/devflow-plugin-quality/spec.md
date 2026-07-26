## ADDED Requirements

### Requirement: Matt skill installer provenance is current and reproducible

DevFlow development and release provenance SHALL pin the verified `skills`
installer executable to `1.5.20`, SHALL record its Node `>=22.20.0` runtime
requirement, and MUST preserve the approved `mattpocock/skills` `v1.1.0`
source, selected skills, Codex agent target, and non-interactive installation
arguments.

#### Scenario: Development provenance is inspected

- **WHEN** the development dependency provenance is parsed
- **THEN** the methodology install command begins with `npx -y skills@1.5.20 add`
- **AND** its methodology runtime requirement is Node `>=22.20.0`
- **AND** it still selects only the six approved Matt skills for the `codex` agent with `--yes`

#### Scenario: Release provenance is inspected

- **WHEN** the packaged DevFlow dependency provenance is parsed after release promotion
- **THEN** its methodology installer command and runtime requirement exactly match the verified development provenance
- **AND** the pinned Matt repository, release ref, commit, license, adaptations, and content hashes are unchanged

#### Scenario: A newer installer is published

- **WHEN** the npm `latest` tag later differs from `1.5.20`
- **THEN** existing DevFlow installs continue to use the reviewed `1.5.20` command
- **AND** changing the pin requires another explicit dependency review rather than an automatic upgrade
