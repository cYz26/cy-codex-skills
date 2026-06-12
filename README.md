# cy-codex-skills

Repository for maintained Codex plugins, archived legacy standalone skills, and a small set of local terminal config files synchronized across devices.

## Active plugin surfaces

Development-stage Codex plugins live under `dev/plugins/`; release-ready plugins live under `plugins/`. Project-local workflow skills are activated through `.codex/skills/`.

## Development plugins

Development-stage plugin source paths:

- `dev/plugins/agent-kb`
- `dev/plugins/dev-flow`

## Release plugins

- `plugins/agent-kb`
- `plugins/godot-core`
- `plugins/dev-flow`
- `plugins/lark-feishu-ops`

## Archived standalone skills

Legacy standalone skills that previously lived at the repository root are now archived under `archived-skills/`. These are kept for historical reference and compatibility checks, but they are deprecated and not recommended for new use.

- `archived-skills/agents-md-context-manager`
- `archived-skills/agent-reach` (Agent Reach; deprecated and not recommended for new use)
- `archived-skills/develop-web-game`
- `archived-skills/durable-knowledge-maintainer`
- `archived-skills/game-image-asset-pipeline`
- `archived-skills/godot-core`
- `archived-skills/godot-web-cjk-font-fix`
- `archived-skills/godot-web-export`
- `archived-skills/pixi-game-core`
- `archived-skills/pixi-mini-game-readiness`
- `archived-skills/pixi-web-wechat-dual-target`
- `archived-skills/pixi-wechat-black-screen`
- `archived-skills/pixi-wechat-minigame-adapter`
- `archived-skills/playwright`
- `archived-skills/playwright-codex`
- `archived-skills/playwright-interactive`
- `archived-skills/screenshot`
- `archived-skills/self-improving-codex`
- `archived-skills/skill-candidate-harvester`
- `archived-skills/spec-workflow`
- `archived-skills/uninstall-claude-code`

## Development skills

No release-ready standalone skills live at the repository root. If standalone skills are reintroduced, use `dev/skills/` for development-stage work and promote through the same release isolation rules as plugins.

See `docs/release-isolation.md` for the promotion and marketplace isolation rules.

## Restore on another machine

Clone this repo, then install or link the active plugins from `plugins/` or `dev/plugins/` according to the marketplace configuration. Archived standalone skills can still be copied or symlinked from `archived-skills/<name>` into `~/.codex/skills/` for historical compatibility, but prefer the maintained plugin surfaces for new use.

For Ghostty, copy `dotfiles/.config/ghostty/config.ghostty` to `~/.config/ghostty/config.ghostty`, then reload Ghostty config or restart the app.

## Synced local configs

- `dotfiles/.config/ghostty/config.ghostty`

## Excluded skills

See `marketplace-skills.txt` for the skills intentionally excluded from this repository.
