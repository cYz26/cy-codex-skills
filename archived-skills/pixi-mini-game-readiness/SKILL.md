---
name: pixi-mini-game-readiness
description: Prepare or review a PixiJS project for future WeChat or Douyin mini-game adaptation without implementing runtime adapters yet. Use when Codex needs to audit browser-only coupling, define platform boundaries, set mini-game-safe rules before implementation, or produce a readiness gap checklist before mini-game migration.
---

# Pixi Mini-Game Readiness

Use this skill when the project is still Web-first today but must avoid architecture choices that will block future WeChat or Douyin mini-game support.

This skill does not implement `wx` or `tt` adapters. It defines what must stay abstract, which rules must be locked during audit, and what constraints must hand off into future dual-target development.

If the repository already maintains both Web and WeChat outputs, use `$pixi-web-wechat-dual-target` alongside this skill. Use this skill for audit and readiness work, not as the only ongoing-dev guardrail.

## 1) Audit First and Set Rules Before Code Changes

Before proposing refactors, identify where browser-only coupling already exists and turn that audit into no-regression constraints.

Treat these as migration risks when they appear outside a dedicated platform boundary:
1. direct `window`, `document`, or `navigator` access
2. direct `localStorage`, `sessionStorage`, or IndexedDB usage
3. raw `fetch` or `XMLHttpRequest` calls in gameplay logic
4. browser-only audio or media APIs
5. gameplay-critical HTML or CSS overlays
6. resize, focus, visibility, or lifecycle logic wired directly to DOM events
7. hardcoded asset roots such as `/assets/...`
8. platform branches spread through scenes or systems

Document every finding as:
1. `blocker`
2. `high-risk`
3. `watch`

Also document:
1. which directories may contain platform-specific code
2. which layers must stay platform-neutral
3. which validation commands must stay green after readiness refactors

## 2) Refactor Readiness Without Writing Vendor Adapters

Keep these contracts explicit even if they initially have only Web implementations:
1. `RuntimeTarget = 'web' | 'wechat-minigame' | 'douyin-minigame'`
2. `GameBootConfig`
3. `PlatformBridge`
4. `AssetResolver`
5. `StorageBridge`
6. `InputAdapter`
7. `SceneContract`

Reserve interfaces for:
1. launch parameters
2. pause and resume lifecycle
3. persistence
4. share
5. vibration or haptics
6. open data context or leaderboard bridges

Do not implement vendor details in v1 unless the user explicitly asks for real mini-game integration.

## 3) Hand Off Explicit Constraints for Dual-Target Development

The readiness output must not stop at "this is adaptable." It must leave behind constraints that future Web work cannot violate.

Hand off:
1. current readiness level
2. blocker and high-risk list
3. contracts that must exist now
4. safe temporary Web-only code that may remain isolated
5. validation commands that future contributors must run
6. official documents that must be re-verified when real `wx` or `tt` work starts

## Resource Map

1. `references/readiness.md`: audit workflow, severity model, and deliverable template
2. `references/platform-abstraction-contract.md`: recommended future-proof interfaces
3. `references/dual-target-red-lines.md`: rules that should be locked during audit and kept during future development
4. `references/wechat.md`: WeChat mini-game verification notes and official links
5. `references/douyin.md`: Douyin mini-game verification notes and official links
