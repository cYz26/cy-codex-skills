#!/bin/bash

# Uninstall Claude Code - Complete removal script
# This script removes Claude Code, claude-code-router, and all associated configuration/cache files

set -euo pipefail

echo "🗑️  Starting Claude Code uninstallation..."

NPM_PACKAGES=(
    "@anthropic-ai/claude-code"
    "@musistudio/claude-code-router"
    "claude-code-router"
)

PACKAGE_REMOVED=0
for pkg in "${NPM_PACKAGES[@]}"; do
    if npm ls -g --depth=0 "$pkg" >/dev/null 2>&1; then
        echo "📦 Uninstalling npm package: $pkg"
        npm uninstall -g "$pkg"
        PACKAGE_REMOVED=$((PACKAGE_REMOVED + 1))
    fi
done

if [[ $PACKAGE_REMOVED -eq 0 ]]; then
    echo "✓ No Claude Code related npm packages found"
else
    echo "✓ Removed $PACKAGE_REMOVED npm package(s)"
fi

# Stop claude-code-router process before removing files
PID_FILE="$HOME/.claude-code-router/.claude-code-router.pid"
if [[ -f "$PID_FILE" ]]; then
    ROUTER_PID=$(cat "$PID_FILE" 2>/dev/null || true)
    if [[ -n "$ROUTER_PID" ]] && kill -0 "$ROUTER_PID" 2>/dev/null; then
        echo "🛑 Stopping claude-code-router process (pid=$ROUTER_PID)..."
        kill "$ROUTER_PID" 2>/dev/null || true
        sleep 1
    fi
fi

if pgrep -f "claude-code-router" >/dev/null 2>&1; then
    echo "🛑 Stopping remaining claude-code-router processes..."
    pkill -f "claude-code-router" || true
fi

# Remove configuration and cache files
echo "🧹 Cleaning up configuration and cache files..."

FILES_TO_REMOVE=(
    "$HOME/.claude"
    "$HOME/.claude.json"
    "$HOME/.claude.json.backup.*"
    "$HOME/.claude-code-router"
    "$HOME/.claude-code-router.pid"
    "$HOME/Library/Caches/claude-cli-nodejs"
    "$HOME/.cache/claude-cli-nodejs"
    "$HOME/.local/share/claude"
    "$HOME/Library/Caches/claude-code-router"
    "$HOME/Library/Logs/claude-code-router"
    "$HOME/.cache/claude-code-router"
    "$HOME/.local/share/claude-code-router"
    "$HOME/.config/claude-code-router"
    "$HOME/.vscode/extensions/anthropic.claude-code-*"
)

REMOVED_COUNT=0

for item in "${FILES_TO_REMOVE[@]}"; do
    # Handle glob patterns safely without eval
    if [[ "$item" == *"*"* || "$item" == *"?"* || "$item" == *"["* ]]; then
        MATCHED=0
        while IFS= read -r match; do
            [[ -z "$match" ]] && continue
            rm -rf "$match"
            REMOVED_COUNT=$((REMOVED_COUNT + 1))
            MATCHED=1
        done < <(compgen -G "$item" || true)
        if [[ $MATCHED -eq 1 ]]; then
            echo "  removed pattern: $item"
        fi
    else
        if [[ -e "$item" ]]; then
            rm -rf "$item"
            REMOVED_COUNT=$((REMOVED_COUNT + 1))
            echo "  removed: $item"
        fi
    fi
done

if [[ $REMOVED_COUNT -eq 0 ]]; then
    echo "✓ No configuration or cache files found"
else
    echo "✓ Removed $REMOVED_COUNT configuration/cache items"
fi

# Verify uninstallation
echo ""
echo "🔍 Verifying uninstallation..."

if command -v claude &> /dev/null; then
    echo "⚠️  Warning: 'claude' command is still available"
    echo "   Location: $(which claude)"
else
    echo "✓ 'claude' command successfully removed"
fi

# Check for remaining targeted files
VERIFY_PATTERNS=(
    "$HOME/.claude"
    "$HOME/.claude.json"
    "$HOME/.claude.json.backup.*"
    "$HOME/.claude-code-router"
    "$HOME/.claude-code-router.pid"
    "$HOME/Library/Caches/claude-cli-nodejs"
    "$HOME/.cache/claude-cli-nodejs"
    "$HOME/.local/share/claude"
    "$HOME/Library/Caches/claude-code-router"
    "$HOME/Library/Logs/claude-code-router"
    "$HOME/.cache/claude-code-router"
    "$HOME/.local/share/claude-code-router"
    "$HOME/.config/claude-code-router"
    "$HOME/.vscode/extensions/anthropic.claude-code-*"
)

REMAINING=""
for pattern in "${VERIFY_PATTERNS[@]}"; do
    if [[ "$pattern" == *"*"* || "$pattern" == *"?"* || "$pattern" == *"["* ]]; then
        while IFS= read -r match; do
            [[ -z "$match" ]] && continue
            REMAINING+="$match"$'\n'
        done < <(compgen -G "$pattern" || true)
    elif [[ -e "$pattern" ]]; then
        REMAINING+="$pattern"$'\n'
    fi
done

if [[ -n "$REMAINING" ]]; then
    echo "⚠️  Some Claude Code related files still exist:"
    echo "$REMAINING"
else
    echo "✓ No Claude Code related files found"
fi

echo ""
echo "✅ Claude Code uninstallation complete!"
