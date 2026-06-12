---
name: pixi-wechat-black-screen
description: Diagnose and fix PixiJS WeChat mini-game black screens caused by startup/runtime adapter issues, unstable screen-canvas ownership, DevTools DOM quirks, or canvas/display mismatches. Use when a PixiJS mini-game boots in WeChat DevTools or on device but stays black, when logs reach app init or first frame without visible output, or when adapting browser-oriented Pixi boot code to the WeChat single-screen-canvas contract.
---

# Pixi WeChat Black Screen

Use this skill when the game is already entering the WeChat mini-game runtime, but visibility is wrong or unstable. Focus on proving whether the failure is in entry execution, runtime preparation, canvas ownership, or actual rendering.

## Workflow

1. Classify the failure before editing.
   - If `game.js` or `wechat-main` never logs, treat it as an entry failure.
   - If `app-init` or `first-frame` logs appear but the screen is black, treat it as a screen-canvas contract failure first, not a scene-content failure.
   - If the game renders on Web but not in WeChat, isolate all fixes to the generated entry, `platform/`, and build layers.

2. Enforce a single screen-canvas owner.
   - Create exactly one screen canvas in generated `game.js` before loading the WeChat runtime bundle.
   - Bind that canvas to `globalThis.canvas`, `globalThis.screencanvas`, `GameGlobal.canvas`, and `GameGlobal.screencanvas`.
   - Treat every later `wx.createCanvas()` call as offscreen-only.
   - Do not let runtime code rediscover, rescore, or replace the screen canvas.

3. Keep runtime prep narrow.
   - `prepareWeChatRuntime()` must assert a prebound screen canvas exists.
   - Use runtime prep only for environment polyfills and DOM shims that Pixi actually needs.
   - Do not scan `document` to choose a display canvas.
   - Do not create a fallback display canvas during runtime prep.

4. Keep the platform layer read-only with respect to canvas ownership.
   - `WeChatPlatform` should only consume the prebound screen canvas.
   - Do not call `wx.createCanvas()` in the platform layer.
   - Do not scan `document.querySelectorAll('canvas')` in the platform layer.

5. Respect DevTools native DOM behavior.
   - If a native `document` already exists in DevTools, reuse it instead of replacing it.
   - Do not assign directly to a getter-only `window.document`.
   - Do not assume `body.children` is an array; native DOM may expose `HTMLCollection`.
   - Maintain an internal child store for synthetic linkage instead of mutating native `children`.

6. Use temporary evidence, then remove it.
   - In debug builds only, temporary probe graphics or pixel readback are acceptable to prove the screen canvas is visible.
   - Once visibility is confirmed, remove the probes so they do not pollute normal debugging.

7. Validate both structure and outcome.
   - Run the repo's typecheck, lint, tests, debug package build, and WeChat audit commands.
   - Re-test in WeChat DevTools with the fresh debug package.
   - If possible, verify on device after DevTools is green.

## Guardrails

1. Do not spread WeChat-specific canvas logic into shared scenes or gameplay systems.
2. Do not keep multiple canvas-selection code paths alive at once.
3. Do not trust `document.querySelector('canvas')` as the source of truth in WeChat DevTools.
4. Do not mark the issue fixed until you have visual proof in DevTools or on device.
5. Do not leave temporary probe overlays in release output.

## Resource Map

1. `references/workflow.md`: step-by-step diagnosis and fix flow
2. `references/pitfalls.md`: symptom-to-cause mapping and concrete failure patterns
