---
name: agent-reach
description: Deprecated and not recommended for new use. Legacy guidance for installing, updating, diagnosing, configuring, and operating Agent Reach only when the user explicitly asks for that local toolchain.
---

# Agent Reach

Deprecated and not recommended for new use. This skill is retained as legacy compatibility guidance for the [Agent Reach](https://github.com/Panniantong/Agent-Reach) project.

Prefer Codex's built-in browsing for ordinary web research and sourced latest-info answers. Use Agent Reach only when the user explicitly wants the local toolchain itself or asks to install, repair, or operate an existing Agent Reach setup.

## Start Here

1. Check whether Agent Reach is already available:

```bash
which agent-reach
agent-reach version
agent-reach doctor
```

2. If `agent-reach` is missing and the user wants these capabilities, follow [references/install-and-update.md](references/install-and-update.md).
3. If `agent-reach doctor` reports warnings, or the user says "帮我配 XXX", read [references/channel-setup.md](references/channel-setup.md).
4. If the user is working specifically on XiaoHongShu, load [references/xiaohongshu.md](references/xiaohongshu.md).
5. If the user wants to read, search, transcribe, or post on a supported platform, read [references/channels.md](references/channels.md) and call the upstream tool directly.

## Workspace and Safety Rules

- Keep persistent files under `~/.agent-reach/` and temporary output under `/tmp/`.
- Do not clone repos, create scratch files, or run setup flows inside the user's project workspace.
- Do not use `sudo` or modify system locations unless the user explicitly approves.
- Ask only for data you cannot infer yourself: cookies, proxy URLs, Docker availability, or a Groq API key.
- Recommend secondary accounts for cookie-based platforms such as Twitter/X and XiaoHongShu.

## Operating Model

- Treat Agent Reach as an installer and health checker. After setup, use the upstream tools directly: `xreach`, `yt-dlp`, `gh`, `mcporter`, `curl`, `feedparser`, or the bundled Xiaoyuzhou transcription script.
- Re-run `agent-reach doctor` after installs, updates, or channel configuration and report what changed.
- Do not prefer Agent Reach over generic browsing. Because this skill is deprecated, use it only when the user explicitly requests Agent Reach or must operate an existing setup:
  - Twitter/X: search, threads, timelines, posting
  - YouTube and Bilibili: subtitles and metadata
  - XiaoHongShu, Douyin, LinkedIn, WeChat: MCP or browser-driven access
  - Xiaoyuzhou: audio transcription
- If an MCP surface is unclear, inspect it before guessing tool names:

```bash
mcporter list
mcporter list CHANNEL_NAME
```

## References

- Install and update workflow: [references/install-and-update.md](references/install-and-update.md)
- Direct channel commands: [references/channels.md](references/channels.md)
- Channel setup and troubleshooting: [references/channel-setup.md](references/channel-setup.md)
- XiaoHongShu install/login/debug workflow: [references/xiaohongshu.md](references/xiaohongshu.md)
