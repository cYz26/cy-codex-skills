## ADDED Requirements

### Requirement: Packaged Hooks start without the standard-library TOML parser

DevFlow Hook entrypoints SHALL remain executable when the host resolves the
manifest's `python3` command to a Python runtime that does not provide
`tomllib`.

#### Scenario: Migration reminder starts without tomllib

- **WHEN** the packaged migration reminder Hook starts with `tomllib`
  unavailable
- **THEN** it exits without an import traceback
- **AND** any model-visible output uses the Codex UserPromptSubmit schema.

#### Scenario: Aggregate Stop Hook starts without tomllib

- **WHEN** the packaged aggregate Stop Hook starts with `tomllib` unavailable
- **THEN** it exits without an import traceback
- **AND** any model-visible output uses the Codex Stop schema.

#### Scenario: Modern Python behavior remains unchanged

- **WHEN** the same Hook entrypoint runs with the standard-library TOML parser
  available
- **THEN** its exit status and response schema remain compatible with the
  existing Hook contract.

### Requirement: Legacy TOML inspection fails closed without a parser

DevFlow SHALL NOT infer automatic legacy-workflow cleanup ownership from TOML
configuration when no standards-compliant TOML parser is available.

#### Scenario: GSD configuration needs parser-backed ownership proof

- **GIVEN** a project contains a `.codex/config.toml` that references GSD
- **AND** no standards-compliant TOML parser is available
- **WHEN** DevFlow inspects legacy workflow uninstall candidates
- **THEN** `.codex/config.toml` is not classified as an automatic cleanup
  candidate
- **AND** the report requires manual review for that exact path.

#### Scenario: Unrelated configuration does not create a false blocker

- **GIVEN** a project contains a `.codex/config.toml` with no GSD reference
- **AND** no standards-compliant TOML parser is available
- **WHEN** DevFlow inspects legacy workflow uninstall candidates
- **THEN** that configuration creates neither a cleanup candidate nor a manual
  legacy-workflow action.

### Requirement: Python 3.9 Hook repair is published as an immutable patch

DevFlow SHALL publish runtime bytes that differ from immutable `0.4.0` as
successor version `0.4.1` with one exact tag-bound asset set.

#### Scenario: Patch release identity is coherent

- **WHEN** the repaired runtime is promoted for publication
- **THEN** source and generated plugin manifests report `0.4.1`
- **AND** the release policy, expected manifest, release notes, workflow tag,
  and seven declared assets all use `dev-flow-v0.4.1`
- **AND** `dev-flow-v0.4.0` is not moved, overwritten, or reused.

#### Scenario: Publication is proven before activation

- **WHEN** `dev-flow-v0.4.1` is pushed
- **THEN** the immutable tag targets the reviewed `main` commit
- **AND** the GitHub Release is published, non-draft, and non-prerelease
- **AND** every declared asset name, size, and SHA-256 matches the frozen
  expectation before cache refresh.

### Requirement: Internal cache activation preserves target scope

DevFlow SHALL activate the patch only in the explicitly named internal cache
and SHALL verify the original Python 3.9 failure seam after refresh.

#### Scenario: Named cache is refreshed

- **WHEN** publication readback passes
- **THEN** only internal `dev-flow@cy-codex-skills` is refreshed
- **AND** source, generated release, and cache identify version `0.4.1` and
  refresh revision 12
- **AND** the installed migration and Stop Hooks exit without traceback under
  `/usr/bin/python3` 3.9.6.

#### Scenario: Consumer projects remain unchanged

- **WHEN** the internal cache refresh completes
- **THEN** no consumer-project migration, configuration rewrite, or legacy
  cleanup is performed.
