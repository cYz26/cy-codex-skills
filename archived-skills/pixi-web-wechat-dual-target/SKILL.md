---
name: pixi-web-wechat-dual-target
description: Develop, refactor, or review a PixiJS project that must keep both Web and WeChat mini-game outputs healthy. Use when Codex needs ongoing dual-target guardrails, validation gates, regression review, or smoke checklists after readiness work is already in place.
---

# Pixi Web WeChat Dual Target

Use this skill when a PixiJS codebase is already maintaining both Web and WeChat mini-game outputs, or when the user explicitly wants to keep Web work from breaking future or current WeChat delivery.

This skill is not a readiness-audit replacement. If the platform boundary is still undefined, load `$pixi-mini-game-readiness` first or alongside this skill.

## 1) When to Trigger

Use this skill for:
1. continuing Web feature work without breaking WeChat output
2. refactoring boot, platform, asset, storage, or lifecycle code in a dual-target repo
3. code review where Web-only assumptions may regress mini-game compatibility
4. deciding which validation commands and smoke flows are required after a change

## 2) Boundary Rules and Forbidden Patterns

Keep platform differences inside:
1. target entrypoints
2. `platform/` wrappers
3. boot-time lifecycle wiring
4. target-specific build config

Treat these as regression risks unless isolated:
1. browser globals outside platform modules
2. hardcoded asset roots in shared runtime code
3. direct storage access outside a storage bridge
4. platform-specific branches spread through scenes or systems
5. gameplay-critical HTML or CSS layers

## 3) Development and Refactor Workflow

Classify the change before coding:
1. pure shared logic
2. shared runtime or scene composition
3. platform bridge or lifecycle change
4. asset, font, text-rendering, or packaging change

Then:
1. keep shared logic platform-neutral
2. keep WeChat-specific fixes inside platform or build layers
3. satisfy DevTools- or packager-specific asset path expectations in packaging instead of leaking them into shared runtime code
4. prefer packaged glyph or bitmap strategies over runtime CJK font assumptions when mini-game Chinese copy must be reliable
5. if the project uses a fixed-copy glyph atlas or similar packaged text asset, make sure normal build commands regenerate it automatically instead of relying on manual operator memory
6. add or maintain a regression test that compares current source copy against atlas coverage so new Chinese UI strings fail fast when the packaged text asset is stale
7. keep debug and release build paths packaging the same latest text assets; do not let one path silently lag behind the other
8. choose validation from `references/gates.md`
9. update durable project rules if the boundary or command matrix changed

## 4) Review and Regression Output

When reviewing or shipping a change, report:
1. which targets were affected
2. which commands were run
3. which smoke flows were covered
4. which target remains unverified
5. any dual-target regression risk still open

## Resource Map

1. `references/workflow.md`: how to move from readiness to daily dual-target development
2. `references/gates.md`: command matrix by change type
3. `references/pitfalls.md`: common Web/WeChat dual-target pitfalls
4. `references/smoke-checklist.md`: Web and WeChat smoke expectations
