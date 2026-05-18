# cy-codex-skills

Mirror of the non-system Codex skills currently loaded from `~/.codex/skills`, plus a small set of local terminal config files synchronized across devices.

## Synced skills

- `agents-md-context-manager`
- `agent-reach`
- `develop-web-game`
- `durable-knowledge-maintainer`
- `game-image-asset-pipeline`
- `godot-core`
- `godot-web-cjk-font-fix`
- `godot-web-export`
- `pixi-game-core`
- `pixi-mini-game-readiness`
- `pixi-web-wechat-dual-target`
- `pixi-wechat-black-screen`
- `pixi-wechat-minigame-adapter`
- `playwright`
- `playwright-codex`
- `playwright-interactive`
- `screenshot`
- `self-improving-codex`
- `skill-candidate-harvester`
- `spec-workflow`
- `uninstall-claude-code`

## Development plugins

Development-stage Codex plugins live under `dev/plugins/`.

- `dev/plugins/codex-project-orchestrator`

## Restore on another machine

Clone this repo, then copy or symlink each skill directory into `~/.codex/skills/`, and restart Codex.

For Ghostty, copy `dotfiles/.config/ghostty/config.ghostty` to `~/.config/ghostty/config.ghostty`, then reload Ghostty config or restart the app.

## Synced local configs

- `dotfiles/.config/ghostty/config.ghostty`

## Excluded skills

See `marketplace-skills.txt` for the skills intentionally excluded from this repository.
