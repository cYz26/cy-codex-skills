---
name: pixi-game-core
description: Build, refactor, or review PixiJS v8 games using TypeScript, pnpm, and Vite. Use when Codex needs to start a new PixiJS game, standardize an existing Pixi project, define scene and system architecture, organize asset loading, normalize input handling, or enforce rendering and quality gates for AI coding workflows.
---

# Pixi Game Core

Use this skill for day-to-day PixiJS game engineering.

Respect repository-locked tooling first. For new setups, default to `TypeScript + pnpm + Vite + PixiJS v8`.

## 1) Read Official Pixi Sources in the Right Order

Before making API decisions, load:
1. `references/pixi-llm-docs-policy.md`
2. `references/architecture.md`
3. `references/assets-and-rendering.md`
4. `references/testing-and-quality-gates.md`

Use Pixi's official LLM docs as the primary source for API facts. Use guides and performance docs as the secondary source for engineering tradeoffs.

## 2) Lock the Project Boundaries Early

Structure the project around these directories unless the repo already has a stronger pattern:
1. `boot/`: startup, app creation, preload orchestration, scene registration
2. `scenes/`: gameplay scenes and transitions
3. `systems/`: non-visual domain services
4. `ui/`: HUD, overlays, reusable UI widgets
5. `assets/`: manifests, loaders, asset metadata
6. `platform/`: runtime boundary for browser or future mini-game adaptation
7. `shared/`: types, constants, math, utilities with no platform side effects

Keep gameplay logic out of `platform/`. Keep Pixi display concerns out of `systems/`.

## 3) Use Stable Runtime and Scene Contracts

Keep these contracts explicit:
1. `RuntimeTarget = 'web' | 'wechat-minigame' | 'douyin-minigame'`
2. `GameBootConfig`
3. `SceneContract`
4. `AssetResolver`
5. `InputAdapter`

Separate:
1. boot
2. preload
3. first interactive scene
4. pause and resume
5. teardown and destroy

Do not let scene code directly own browser globals, resource URL policy, or persistence details.

## 4) Keep Assets and Input Migration-Safe

Require manifest-driven assets. Do not scatter raw image or audio paths across gameplay code.

Require input normalization. Gameplay should consume semantic actions or a unified pointer adapter, not raw DOM events.

Default to canvas-first rendering. Allow HTML overlays only for debug shells, launcher chrome, or non-gameplay operations.

If the project may later target WeChat or Douyin mini-games, also load `$pixi-mini-game-readiness` for audit and readiness work.

If the project already maintains both Web and WeChat outputs, also load `$pixi-web-wechat-dual-target` for ongoing development, review, and regression rules.

## 5) Run Quality Gates After Behavior Changes

For new or refactored behavior, run the nearest equivalent of:
1. `pnpm lint`
2. `pnpm typecheck`
3. `pnpm build`
4. `pnpm test`
5. If no automated tests exist, run a documented smoke flow

If the repository has separate Web and WeChat outputs, prefer the explicit matrix:
1. `pnpm lint`
2. `pnpm typecheck`
3. `pnpm build:web`
4. `pnpm build:wechat`
5. `pnpm test`

Always report:
1. architecture or boundary changes
2. validation commands run
3. manual smoke coverage
4. remaining risks

## Resource Map

1. `references/pixi-llm-docs-policy.md`: source-of-truth order for Pixi docs
2. `references/architecture.md`: recommended module boundaries and contracts
3. `references/assets-and-rendering.md`: asset, rendering, and input rules
4. `references/testing-and-quality-gates.md`: validation chain and smoke checklist
5. `assets/templates/docs/constraints.md`: drop-in project constraints template
