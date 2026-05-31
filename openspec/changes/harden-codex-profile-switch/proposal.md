## Why

The Codex profile switcher currently works for the narrow happy path, but it rewrites the primary Codex config with broad regexes and can misclassify or remove unrelated custom providers. The DeepSeek/CCX integration should be safe to try, reversible, and verifiable against the current Codex and CCX behavior.

## What Changes

- Simplify daily usage to `codex-profile deepseek` and `codex-profile official`.
- Make the default DeepSeek command generate the CLI overlay and activate the Desktop App base config, because current Codex `--profile` support does not apply to `codex app`.
- Keep `deepseek --cli-only` for overlay-only CLI usage without mutating the base config.
- Add focused regression tests for switching behavior using temporary `CODEX_HOME` directories.
- Keep `model_provider` fixed to the CCX provider id while allowing the requested model alias to vary.
- Make the DeepSeek model catalog schema compatible with the current Codex parser when explicitly loaded.
- Correct CCX example values to current CCX option names and document which values are verified locally.
- Improve status/check commands so users can distinguish official mode, CCX overlay readiness, and proxy health.

## Capabilities

### New Capabilities
- `codex-profile-switch`: Safe local switching between official Codex subscription mode and a DeepSeek API mode routed through CCX.

### Modified Capabilities

## Impact

- Affected files:
  - `dev/tools/codex-profile-switch/switch-profile.sh`
  - `dev/tools/codex-profile-switch/README.md`
  - `dev/tools/codex-profile-switch/profiles/deepseek/*`
  - `dev/tools/codex-profile-switch/ccx/config.example.json`
  - `dev/tools/codex-profile-switch/tests/*`
- No production dependencies are added.
- The DeepSeek switch rewrites the base config only after saving an official snapshot; `--cli-only` preserves the overlay-only workflow.
