---
name: uninstall-claude-code
description: Complete uninstallation of Claude Code including npm package removal and cleanup of all configuration, cache, router, and plugin files. Use when the user wants to uninstall, remove, delete, or clean up Claude Code (also known as @anthropic-ai/claude-code) and related tooling (such as @musistudio/claude-code-router) from their system. Handles removal of npm packages, .claude configuration files, claude-code-router files/plugins, cache directories, and VSCode extensions.
---

# Uninstall Claude Code

## Overview

Completely removes Claude Code from the system, including the npm package and all associated configuration and cache files.

## Quick Start

Run the uninstallation script:

```bash
bash scripts/uninstall.sh
```

The script will:
1. Uninstall the `@anthropic-ai/claude-code` npm package
2. Uninstall related router packages (`@musistudio/claude-code-router`, `claude-code-router`)
3. Stop running `claude-code-router` processes
4. Remove all configuration files (`.claude/`, `.claude.json`, backups)
5. Remove `~/.claude-code-router` and router plugin/log files
6. Delete cache directories (`~/Library/Caches/claude-cli-nodejs/`, `~/Library/Caches/claude-code-router/`, Linux fallback cache paths)
7. Remove VSCode extensions (`~/.vscode/extensions/anthropic.claude-code-*`)
8. Verify the uninstallation

## Manual Uninstallation

If you prefer to uninstall manually or need to customize the process:

### Step 1: Uninstall npm package

```bash
npm uninstall -g @anthropic-ai/claude-code
npm uninstall -g @musistudio/claude-code-router claude-code-router
```

### Step 2: Remove configuration and cache

```bash
rm -rf ~/.claude ~/.claude.json ~/.claude.json.backup.* \
  ~/.claude-code-router ~/.claude-code-router.pid \
  ~/Library/Caches/claude-cli-nodejs ~/Library/Caches/claude-code-router \
  ~/.cache/claude-cli-nodejs ~/.local/share/claude \
  ~/Library/Logs/claude-code-router \
  ~/.cache/claude-code-router ~/.local/share/claude-code-router ~/.config/claude-code-router \
  ~/.vscode/extensions/anthropic.claude-code-*
```

### Step 3: Verify removal

```bash
which claude  # Should return "claude not found"
find ~ -maxdepth 3 -name "*claude*"  # Check for remaining files
```

## What Gets Removed

**npm Package:**
- `@anthropic-ai/claude-code` (installed via npm)
- `@musistudio/claude-code-router` / `claude-code-router` (if installed)

**Configuration files:**
- `~/.claude/` - Configuration directory
- `~/.claude.json` - Main configuration file
- `~/.claude.json.backup.*` - Configuration backups
- `~/.claude-code-router/` - Router config/log/plugin directory
- `~/.claude-code-router.pid` - Router pid file

**Cache directories:**
- `~/Library/Caches/claude-cli-nodejs/` - Application cache (macOS)
- `~/.cache/claude-cli-nodejs/` - Application cache (Linux)
- `~/.local/share/claude/` - Application data (Linux)
- `~/Library/Caches/claude-code-router/` - Router cache (macOS)
- `~/Library/Logs/claude-code-router/` - Router logs (macOS)
- `~/.cache/claude-code-router/` - Router cache (Linux)
- `~/.local/share/claude-code-router/` - Router data (Linux)
- `~/.config/claude-code-router/` - Router config (Linux)

**VSCode extensions:**
- `~/.vscode/extensions/anthropic.claude-code-*` - All versions of the extension

## Platform Notes

**macOS:** The script is designed for macOS. Cache location is `~/Library/Caches/`.

**Linux:** The script also removes `~/.cache/claude-cli-nodejs/`, `~/.local/share/claude/`, and router cache/config paths.

**Windows:** Use PowerShell equivalent and update paths to Windows conventions (`%APPDATA%`, `%LOCALAPPDATA%`).
