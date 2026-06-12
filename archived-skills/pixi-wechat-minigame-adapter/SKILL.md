---
name: pixi-wechat-minigame-adapter
description: Canonical PixiJS v8 + TypeScript + Vite solution for adding or standardizing a WeChat mini-game target with reusable starter templates, install scripts, validation gates, and maintenance rules.
---

# Pixi WeChat Mini-Game Adapter

Use this skill when a `PixiJS v8 + TypeScript + Vite` project needs a standard WeChat mini-game solution instead of ad hoc runtime shims.

This skill is the canonical source of truth for:
1. the WeChat runtime contract
2. the starter/template assets
3. the install flow
4. the validation matrix
5. the maintenance loop for new failure modes

## Compatibility Envelope

Strong guarantee applies only to:
1. `PixiJS v8`
2. `TypeScript`
3. `Vite`

Other stacks may still reuse the references, but they are migration work, not direct-template installs. Use `references/migration-guide.md` for those cases.

## Modes

The standard solution exposes exactly two install modes:
1. `overlay`: add WeChat support to an existing PixiJS Web repo
2. `skeleton`: create a fresh Web + WeChat starter repo

It also exposes two text-module modes:
1. `none`: default
2. `fixed-copy-glyph`: optional scaffold for packaged fixed-copy text workflows

## Canonical Contract

Every install from this skill must preserve these rules:
1. `game.js` binds exactly one screen canvas before the runtime bundle loads.
2. The screen canvas is published to standard global aliases and an internal screen-canvas key.
3. All later `wx.createCanvas()` calls are offscreen-only.
4. `prepareWeChatRuntime()` only prepares the environment and DOM shim; it never chooses or recreates the display canvas.
5. `WeChatPlatform` only consumes the prebound screen canvas.
6. DevTools native `document` is reused when present.
7. Synthetic DOM uses an internal child store; it never assumes native `children` is an array.
8. WeChat-specific logic stays in `game.js`, `platform/`, and build tooling.

## Install Flow

1. Read `references/install-modes.md` and choose `overlay` or `skeleton`.
2. Run the installer:
   - `python3 scripts/install_starter.py --mode overlay --text-module none --target-repo /path/to/repo`
   - `python3 scripts/install_starter.py --mode skeleton --text-module none --target-repo /path/to/repo`
3. If you need packaged fixed-copy text scaffolding, rerun with `--text-module fixed-copy-glyph`.
4. Adapt only the seams listed in `references/install-modes.md`.
5. Run the commands in `references/validation-matrix.md`.
6. Execute the DevTools and device checks from `references/smoke-checklist.md`.
7. If the game boots but stays black, load [$pixi-wechat-black-screen](/Users/cY/.codex/skills/pixi-wechat-black-screen/SKILL.md).
8. After bootstrap lands, use [$pixi-web-wechat-dual-target](/Users/cY/.codex/skills/pixi-web-wechat-dual-target/SKILL.md) for ongoing work.

## Required Deliverables

An installation is only complete when the target repo has:
1. a stable Web target and WeChat debug/release targets
2. `make web`, `make wechat`, `make wechat-debug`, `make audit`, `make test`, `make lint`, and `make typecheck`
3. a release audit step
4. a smoke checklist for DevTools and device verification
5. a clear record of any remaining `partial`, `pending`, or `blocked` validation

## Maintenance Rule

Fix canonical assets first, then sync the consuming repo. Do not treat a business repo as the starter-template source of truth.

## Resource Map

1. `references/architecture.md`: runtime layers, ownership rules, and adapter boundaries
2. `references/install-modes.md`: overlay vs skeleton expectations and customization seams
3. `references/validation-matrix.md`: required commands, evidence language, and acceptance gates
4. `references/smoke-checklist.md`: DevTools and on-device smoke flows
5. `references/troubleshooting.md`: black-screen, canvas, DOM, and text-related failure modes
6. `references/maintenance.md`: source-of-truth and update workflow
7. `references/migration-guide.md`: guidance for non-Vite or non-Pixi-standard repos
8. `scripts/install_starter.py`: installs the canonical starter into a target repo
9. `scripts/sync_starter_manifest.py`: regenerates the canonical asset manifest
10. `scripts/validate_solution.py`: validates the skill assets and install flow
