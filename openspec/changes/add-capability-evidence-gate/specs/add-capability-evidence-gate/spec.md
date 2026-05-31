# Specification Delta: Add capability evidence gate to research skills

## ADDED Requirements

### Requirement: Capability evidence gate skill

DevFlow SHALL provide a research skill that agents use before implementation when requirements, designs, or answers depend on current, external, platform, plugin, hook, API, or local tool capability.

#### Scenario: Capability-sensitive request

- GIVEN a request depends on a current or external capability
- OR the local repo/cache/config does not obviously match a platform capability
- WHEN DevFlow routes the request
- THEN the agent is instructed to confirm authoritative/current capability
- AND scan local implementation state
- AND compare official capability, local availability, assumptions, and fallback choices
- AND persist the chosen contract before implementation.

#### Scenario: Local absence is not platform absence

- GIVEN local files do not expose a capability
- WHEN the capability can be supplied by the platform, plugin runtime, official CLI, or installed cache
- THEN the agent is instructed to verify authoritative and installed/runtime sources before concluding the capability is unsupported.

### Requirement: Planning artifact evidence surface

OpenSpec templates SHALL provide a durable Capability Evidence section for changes whose behavior depends on capability research.

#### Scenario: New OpenSpec proposal or design

- GIVEN a future DevFlow-generated OpenSpec artifact
- WHEN the artifact is used for a capability-sensitive change
- THEN it contains prompts to record authoritative/current evidence, local scan evidence, comparison, assumptions, and validation contract.

### Requirement: Lightweight AGENTS delegation

Generated AGENTS guidance SHALL route capability-sensitive work to the skill without embedding the full research procedure.

#### Scenario: Generated project guidance

- GIVEN a generated AGENTS file
- WHEN an agent reads the capability research guidance
- THEN the guidance points to `capability-research`
- AND the detailed four-step evidence workflow remains in the skill and OpenSpec artifacts.
