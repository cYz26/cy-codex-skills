# Architecture

The canonical PixiJS WeChat mini-game solution is intentionally narrow. It fixes canvas ownership at entry time and keeps platform differences out of shared gameplay code.

## Layering

1. `game.js` is the ownership layer.
   - It creates exactly one screen canvas.
   - It binds that canvas to standard globals before the runtime bundle loads.
   - It exposes later `wx.createCanvas()` calls as offscreen factories only.

2. `prepareWeChatRuntime()` is the environment layer.
   - It asserts a prebound screen canvas already exists.
   - It installs only the runtime polyfills and DOM shims Pixi actually needs.
   - It reuses native `document` in DevTools when present.
   - It never chooses, rescans, or recreates the display canvas.

3. `WeChatPlatform` is the consumer layer.
   - It reads the prebound screen canvas.
   - It translates system info, safe area, resize, and renderer preference into the shared platform contract.
   - It does not create canvases or scan DOM state.

4. Shared gameplay code stays platform-neutral.
   - Scenes, systems, and game logic do not reach into `wx`.
   - Web and WeChat differences live in boot entrypoints, `platform/`, and build tooling.

## Canvas Contract

1. Screen canvas:
   - created once in generated `game.js`
   - published to `globalThis.canvas`, `globalThis.screencanvas`, `GameGlobal.canvas`, `GameGlobal.screencanvas`, and the internal screen-canvas key
   - never replaced after startup

2. Offscreen canvas:
   - created only through the bundled offscreen factory
   - used for Pixi text, render textures, measurement, or caching
   - never written back into the screen-canvas globals

## DOM Contract

1. DevTools native `document` wins when it already exists.
2. Synthetic DOM only fills missing capabilities.
3. DOM linkage uses an internal child store because native `children` may be `HTMLCollection` or otherwise immutable.
4. `document.querySelector('canvas')`, `querySelectorAll`, `getElementsByTagName`, `getElementById`, and `body.contains()` must all stabilize on the same screen canvas.

## Build Contract

1. Web build and WeChat build remain separate.
2. WeChat runtime bundle is built with `vite.wechat.config.ts`.
3. Packaging is handled by `tools/build-wechat.mjs`.
4. Release inspection is handled by `tools/audit-wechat-build.mjs`.
5. The generated WeChat project config defaults to compatibility-first DevTools settings.

## Debug Contract

1. Runtime startup tracing is allowed in debug builds.
2. Temporary visibility probes are allowed only while diagnosing rendering.
3. Once visibility is proven, probes must be removed.
