---
name: "playwright-codex"
description: "Configure and use Playwright in Codex with a CLI-first workflow and MCP fallback."
---

# Playwright Codex Skill

Use this skill when the task is about configuring Playwright for Codex, deciding between CLI and MCP, or running browser automation in a Codex-friendly workflow.

This skill is a Codex-specific companion to the upstream `playwright` skill. It does not replace `$playwright` for ordinary browser interaction tasks.

## Default mode

Use Playwright in Codex with a CLI-first workflow:

```bash
/Users/cY/.codex/bin/pwcli-codex open https://playwright.dev --headed
/Users/cY/.codex/bin/pwcli-codex snapshot
/Users/cY/.codex/bin/pwcli-codex screenshot
```

Keep MCP enabled as a fallback for tasks that need tool-native persistent context or richer page introspection inside Codex.

Keep CLI session names short. Overly long `--session` values can exceed the local socket path limit used by `playwright-cli`.

## Decision tree

1. If the task is regular browser automation during coding work, use the CLI launcher.
2. If the task needs a persistent browser tool loop inside Codex, use MCP.
3. Do not default to `@playwright/test` or new test specs unless the user explicitly asks for tests.

## Headed vs headless

Default to `--headed` for:

- initial UI debugging
- visual verification
- animation, hover, focus, overlay, scrolling, drag, and responsive issues

Use headless for:

- smoke checks
- fixed command sequences
- console, network, cookie, or storage inspection
- screenshot, pdf, trace, or video capture where a live window is not needed

Headless can still verify UI through screenshots and traces, but it does not provide a live window. When a headless result is unclear, re-run it in `--headed` mode before adding custom scripting.

## Artifact policy

- Prefer `output/playwright/<label>/` when the repository already uses that convention.
- Otherwise use `/tmp/codex-playwright/<label>/`.
- Always capture artifacts when they help with debugging: `screenshot`, `console`, `network`, and `tracing`.

## Snapshot rules

Always run `snapshot` before using element refs.

Run `snapshot` again after:

- navigation
- clicks that change the UI
- modal or menu open and close
- tab switches
- any stale ref error

## References

Open only what you need:

- Codex playbook: `references/codex-playbook.md`
- Upstream browser CLI skill: `/Users/cY/.codex/skills/playwright/SKILL.md`
