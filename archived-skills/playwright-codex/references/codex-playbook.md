# Playwright in Codex

This playbook defines the default Playwright workflow for Codex on this machine.

## Primary choice

- Default to the CLI launcher: `/Users/cY/.codex/bin/pwcli-codex`
- Keep MCP as a fallback when Codex needs built-in browser tools and persistent page context

## Standard setup

```bash
export PLAYWRIGHT_LABEL=smoke-check
mkdir -p "/tmp/codex-playwright/$PLAYWRIGHT_LABEL"
cd "/tmp/codex-playwright/$PLAYWRIGHT_LABEL"
```

If the repository already uses `output/playwright/`, prefer that instead of `/tmp/codex-playwright/`.

## Headed template

Use for first-pass UI debugging and visual inspection:

```bash
/Users/cY/.codex/bin/pwcli-codex open https://example.com --headed
/Users/cY/.codex/bin/pwcli-codex snapshot
/Users/cY/.codex/bin/pwcli-codex screenshot
```

## Headless smoke template

Use for repeatable automation and artifact capture:

```bash
/Users/cY/.codex/bin/pwcli-codex open https://example.com
/Users/cY/.codex/bin/pwcli-codex snapshot
/Users/cY/.codex/bin/pwcli-codex console warning
/Users/cY/.codex/bin/pwcli-codex network
/Users/cY/.codex/bin/pwcli-codex screenshot
```

If a headless run is hard to interpret, repeat it with `--headed` before adding custom script logic.

## Session naming

- Prefer `<project>-<task>` or `<repo>-<feature>`
- Keep the slug short. Long session names can fail because `playwright-cli` uses a local Unix socket path.
- Reuse `PLAYWRIGHT_CLI_SESSION` for multi-step flows
- Use distinct sessions when switching between unrelated pages or environments

Example:

```bash
export PLAYWRIGHT_CLI_SESSION=skills-playwright-smoke
/Users/cY/.codex/bin/pwcli-codex open https://playwright.dev --headed
```

## When to switch to MCP

Switch from CLI to MCP only when the task benefits from Codex-native browser tools, such as:

- long-lived exploratory automation
- repeated structural introspection of the page tree
- self-healing or iterative browser reasoning loops
- workflows where keeping browser state inside the Codex tool layer is more useful than minimizing tokens

For ordinary coding work, keep browser automation in CLI commands and artifacts.
