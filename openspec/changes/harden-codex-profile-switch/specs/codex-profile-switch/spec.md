## ADDED Requirements

### Requirement: Simplified DeepSeek switching
The profile switcher SHALL switch Codex CLI and Codex Desktop App to DeepSeek/CCX mode with one default command, while retaining a CLI-only overlay mode for users who do not want to mutate the primary `config.toml`.

#### Scenario: Switch to DeepSeek mode
- **WHEN** the user runs the default DeepSeek switch command with a valid `CODEX_HOME`
- **THEN** `$CODEX_HOME/deepseek.config.toml` exists
- **AND** it contains `model_provider = "ccx"`
- **AND** it contains `[model_providers.ccx]`
- **AND** `$CODEX_HOME/config.toml` contains `model_provider = "ccx"`
- **AND** unrelated custom provider tables remain present
- **AND** the previous official config is saved as `$CODEX_HOME/profiles/official/config.toml`

#### Scenario: Generate CLI-only DeepSeek overlay
- **WHEN** the user runs the DeepSeek switch command with `--cli-only`
- **THEN** `$CODEX_HOME/deepseek.config.toml` exists
- **AND** it contains `model_provider = "ccx"`
- **AND** `$CODEX_HOME/config.toml` remains byte-for-byte unchanged

#### Scenario: Generate DeepSeek overlay with alternate model alias
- **WHEN** the user requests a DeepSeek model alias such as `gpt-5.5`
- **THEN** the overlay contains `model = "gpt-5.5"`
- **AND** the overlay still contains `model_provider = "ccx"`
- **AND** the primary config still contains `model_provider = "ccx"`

### Requirement: Official mode preservation
The profile switcher SHALL preserve official subscription configuration and unrelated custom providers.

#### Scenario: Official mode check does not remove custom providers
- **WHEN** the primary config contains an unrelated `[model_providers.local]` table
- **AND** the user runs the official command
- **THEN** the unrelated provider table remains present
- **AND** the resulting TOML remains parseable

#### Scenario: Official reasoning effort is preserved
- **WHEN** the primary config contains `model_reasoning_effort = "medium"`
- **AND** the user generates a DeepSeek overlay and returns to official mode
- **THEN** the primary config still contains `model_reasoning_effort = "medium"`

### Requirement: Compatibility activation with exact restore
The profile switcher SHALL preserve the old explicit DeepSeek activation command as a compatibility alias without losing the previous official config.

#### Scenario: Activate DeepSeek through compatibility command
- **WHEN** the user runs the compatibility activation command with model alias `gpt-5.5`
- **THEN** the primary config contains `model = "gpt-5.5"`
- **AND** it contains `model_provider = "ccx"`
- **AND** it contains `[model_providers.ccx]`
- **AND** unrelated custom provider tables remain present

#### Scenario: Restore official config after DeepSeek activation
- **WHEN** the primary config was activated for DeepSeek through the default or compatibility command
- **AND** the user runs the official command
- **THEN** the primary config is restored from the official snapshot
- **AND** the pre-activation reasoning effort and custom providers are preserved

### Requirement: Current Codex model catalog compatibility
The DeepSeek model catalog template SHALL be parseable by the current Codex model catalog loader when explicitly configured.

#### Scenario: Model catalog parses through Codex CLI
- **WHEN** `codex debug models` is run with `model_catalog_json` pointing at the DeepSeek catalog template
- **THEN** Codex exits successfully
- **AND** the rendered catalog includes the `ccx` model slug

### Requirement: CCX compatibility defaults
The CCX example configuration SHALL use option names and values supported by the local CCX implementation.

#### Scenario: CCX example uses supported reasoning style
- **WHEN** the CCX example config is inspected
- **THEN** `reasoningParamStyle` is one of `reasoning`, `reasoning_effort`, or `thinking`
- **AND** `passbackThinkingBlocks` is `false`
- **AND** Codex compatibility is explicitly enabled
