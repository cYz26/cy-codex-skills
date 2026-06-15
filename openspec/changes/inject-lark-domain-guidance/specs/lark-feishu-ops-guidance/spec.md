## ADDED Requirements

### Requirement: FeishuOps handoff resolves domain guidance sources
The Lark Feishu Ops plugin SHALL resolve Lark domain guidance sources before a request is dispatched to a fresh FeishuOps subagent.

#### Scenario: Common action maps to domain guidance
- **WHEN** the parent prepares a FeishuOps handoff for `docs.fetch`
- **THEN** the prepared request includes `guidance_sources`
- **AND** the guidance candidates include `lark-doc`
- **AND** the handoff records whether the matching `SKILL.md` file is available

#### Scenario: Cross-domain action includes multiple guidance candidates
- **WHEN** the parent prepares a FeishuOps handoff for a request that combines document fetch with embedded sheet expansion
- **THEN** the prepared request includes guidance candidates for Docs and Sheets
- **AND** the requested expansion remains bounded by the parent request

### Requirement: Missing official skills fall back to CLI guidance
The Lark Feishu Ops plugin SHALL NOT require official `lark-*` skills to be globally registered or installed before FeishuOps can operate.

#### Scenario: Domain skill file is missing
- **WHEN** the resolver cannot find an official `lark-*` skill file for the requested domain
- **THEN** it records the skill source as missing
- **AND** it includes a `lark-cli <domain> --help` fallback when the domain can be inferred
- **AND** it does not claim the missing skill was loaded

#### Scenario: Unsupported domain has no CLI fallback
- **WHEN** the requested domain has no available skill file and no supported CLI help fallback
- **THEN** the prepared handoff marks the guidance state as blocked or requires explicit raw OpenAPI fallback
- **AND** FeishuOps must return a blocker unless the parent request explicitly authorizes raw OpenAPI exploration

### Requirement: FeishuOps reports guidance provenance
FeishuOps results SHALL report which domain guidance sources were used or considered.

#### Scenario: Subagent returns evidence pack
- **WHEN** FeishuOps returns a structured result for a delegated Lark operation
- **THEN** the result includes `guidance_sources`
- **AND** each source records the type, domain, name or command, and status

### Requirement: Main-agent context remains bounded
The Lark Feishu Ops plugin SHALL keep official Lark domain guidance out of the main agent context unless the user explicitly requests global/project skill activation.

#### Scenario: Parent dispatches FeishuOps work
- **WHEN** the main agent chooses FeishuOps for a request
- **THEN** the parent passes only the compact request, selected guidance metadata, and required context capsule
- **AND** it does not globally activate every official `lark-*` skill
- **AND** it keeps final business judgment in the parent thread
