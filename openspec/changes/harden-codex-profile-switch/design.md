## Context

Codex CLI `0.135.0-alpha.1` supports `--profile <name>` for runtime commands, which layers `$CODEX_HOME/<name>.config.toml` over the primary `$CODEX_HOME/config.toml`. The same help output does not allow `--profile` for `codex app`, so Desktop App usage still needs a controlled base-config activation path. The current switcher edits `config.toml` in place with broad regexes, removes any `[model_providers.*]` section when returning to official mode, and writes `model_provider` from the requested model string. Local validation also showed that the bundled `models_catalog.json` needs the current Codex model catalog fields when loaded through `model_catalog_json`.

The DeepSeek side is routed through CCX on `http://127.0.0.1:3688/v1` with `wire_api = "responses"`. CCX supports Codex compatibility fields including `codexToolCompat`, `codexNativeToolPassthrough`, `normalizeNonstandardChatRoles`, and `passbackThinkingBlocks`.

## Goals / Non-Goals

**Goals:**
- Make the daily workflow two commands: `codex-profile deepseek` and `codex-profile official`.
- Generate `deepseek.config.toml` for CLI runtime commands and activate the base config for Codex Desktop App in the default DeepSeek command.
- Keep a `--cli-only` mode for users who want only the `codex --profile deepseek` overlay without changing the base config.
- Save an official snapshot before touching the base config.
- Preserve plugins, skills, hooks, agents, project trust, desktop settings, and unrelated custom providers.
- Make profile generation idempotent and covered by regression tests.
- Provide explicit validation commands for config parseability, CCX health, and model catalog compatibility.

**Non-Goals:**
- Changing Codex CLI internals or authentication behavior.
- Managing the user's DeepSeek API key beyond providing CCX templates.
- Guaranteeing DeepSeek output quality parity with official OpenAI models.
- Removing the existing backup and restore escape hatches.

## Decisions

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| Make `deepseek` the one-command default switch | Users expect one command to make both CLI and Desktop App use DeepSeek; `codex app` still does not support `--profile`. | Keep separate overlay and App activation commands, which caused confusion and extra manual steps. |
| Keep `--cli-only` for overlay-only usage | It preserves the safe temporary `codex --profile deepseek` workflow for users who do not want to mutate the base config. | Remove overlay-only behavior entirely. |
| Retain `activate-deepseek` as a compatibility alias | Existing users and notes may still refer to it. | Remove the command and force immediate migration. |
| Generate `$CODEX_HOME/deepseek.config.toml` from project templates | Codex expects profile overlays at this location and users can inspect exactly what is applied. | Store overlays only under `$CODEX_HOME/profiles/deepseek`, which Codex does not load directly. |
| Keep `model_provider = "ccx"` fixed | Provider id is the route to CCX; model aliases belong in `model`. | Mirror the model string into `model_provider`, which breaks when model alias is not `ccx`. |
| Make `official` a cleanup/check command, not a destructive mode rewrite | Official mode is simply the base config without a DeepSeek overlay invocation. | Remove all model provider sections to force official mode. |
| Retain backups and restore | Users already have generated backups, and restore remains useful after manual experiments. | Remove backup features entirely. |

## Risks / Trade-offs

- **Users may not want base config mutation** -> The command exposes `--cli-only` and documents that it only generates the overlay.
- **Codex profile schema may drift** -> Tests validate against current CLI help and model catalog parsing where available.
- **CCX option semantics may drift** -> The example uses option names present in the local CCX codebase and docs call out the checked version.
- **Existing generated backups remain on disk** -> The tool does not delete backups automatically; cleanup is left to the user.

## Migration Plan

1. Add tests that demonstrate current destructive behavior and catalog incompatibility.
2. Refactor the switcher to generate and validate `deepseek.config.toml`.
3. Add a targeted base-config activation path for Desktop App and exact official snapshot restore.
4. Update docs to recommend `codex-profile deepseek` and `codex-profile official` for daily use, with `--cli-only` as the opt-in overlay-only mode.
5. Leave `restore` available for prior backup recovery.
6. Validate with shell syntax checks, focused unittest coverage, Codex model catalog parsing, and OpenSpec strict validation.
