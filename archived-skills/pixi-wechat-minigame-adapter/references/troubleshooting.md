# Troubleshooting

Use this reference when the standard install still misbehaves.

## Failure Classes

1. Entry failure
   - `game.js` or `wechat-main` never logs
   - inspect packaging and generated entry first

2. Runtime-prep failure
   - startup reaches `runtime-prep-start` then throws
   - usually missing globals, illegal DOM mutation, or incompatible native `document` assumptions

3. Screen-canvas ownership failure
   - logs reach `app-init` or `first-frame`
   - rendered pixels exist
   - display is still black
   - usually means the runtime is rendering into a canvas the host is not presenting

4. DevTools DOM mismatch
   - `document.querySelector('canvas')`, `body.contains(canvas)`, and `ownerDocument` do not agree with the real screen canvas
   - do not replace native `document`; reuse it and patch only missing APIs

5. Offscreen canvas pollution
   - later `wx.createCanvas()` calls overwrite global screen-canvas aliases
   - all post-entry canvases must stay offscreen-only

6. Text or render-texture side effects
   - startup adds extra canvases or fails during Pixi text generation
   - keep critical startup free of unnecessary render-texture work
   - prefer packaged text for deterministic mini-game copy when needed

## Proven Fixes

1. bind the screen canvas once in generated `game.js`
2. keep `prepareWeChatRuntime()` read-only with respect to canvas ownership
3. keep `WeChatPlatform` read-only with respect to canvas ownership
4. reuse DevTools native `document`
5. avoid direct assignment to getter-only globals like `window.document`
6. keep an internal child store instead of mutating native `children`
7. verify offscreen canvas creation never rewrites screen globals

## Escalation Path

1. confirm the generated entry created exactly one screen canvas
2. confirm later `wx.createCanvas()` calls are tagged offscreen
3. confirm startup reaches `app-init` and `first-frame`
4. if still black, use [$pixi-wechat-black-screen](/Users/cY/.codex/skills/pixi-wechat-black-screen/SKILL.md)
