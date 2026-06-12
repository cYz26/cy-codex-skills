# Pixi WeChat Black Screen Workflow

## 1. Prove where the boot stops

Collect logs in this order:

1. `game.js` prelude
2. `wx.createCanvas`
3. `selected primary canvas`
4. `selected runtime canvas`
5. `app-init`
6. `first-frame`

Interpretation:

1. Missing `game.js` logs: generated entry or packaging problem
2. `game.js` logs present but no `selected primary canvas`: runtime prep problem
3. `app-init` and `first-frame` present but black screen: display canvas mismatch or DevTools DOM bridge problem

## 2. Lock screen-canvas ownership

Apply these invariants:

1. Generate one screen canvas before `require('./js/wechat-main.js')`
2. Bind it to all global screen-canvas aliases
3. Wrap later `wx.createCanvas()` calls so they create offscreen canvases only
4. Keep the platform layer and runtime prep layer from reselecting canvas

Good evidence:

1. `selected primary canvas` points to the prebound screen-canvas alias
2. `selected runtime canvas` points to the same canvas
3. No later logs show a document-discovered canvas replacing it

## 3. Minimize runtime prep

`prepareWeChatRuntime()` should:

1. assert the screen canvas is already bound
2. install only missing global shims and matchers
3. expose only the DOM APIs Pixi actually consumes

It should not:

1. call `wx.createCanvas()` to create a new display canvas
2. score DOM canvases
3. crawl `document` subtrees to find a "better" canvas

## 4. Treat DevTools as a special DOM host

When DevTools already provides a `document`:

1. keep the native `document`
2. avoid direct reassignment to `window.document`
3. avoid assuming `children` is writable or array-like enough for `includes` and `push`

When no `document` exists:

1. create a minimal synthetic document
2. make `querySelector('canvas')`, `querySelectorAll('canvas')`, `getElementsByTagName('canvas')`, and `getElementById()` return the prebound screen canvas
3. keep synthetic DOM state in your own child store

## 5. Use temporary probe evidence only when blocked

If logs suggest rendering is happening but the screen is still black:

1. add obvious debug-only probe graphics
2. optionally read back a few pixels from the current canvas
3. remove both after visibility is confirmed

Interpretation:

1. Correct probe colors in readback plus black screen means pixels reached a canvas that did not make it to the display layer
2. No probe pixels means renderer output is not reaching the inspected canvas

## 6. Validate after every structural change

Minimum validation set:

1. typecheck
2. lint
3. tests covering runtime prep, platform behavior, and build output
4. debug WeChat package build
5. packaged output audit if the repo has one

Prefer adding regression tests for:

1. getter-only `document`
2. native `HTMLCollection`-style `children`
3. prebound screen-canvas assertions
4. offscreen canvas creation that never overwrites screen-canvas globals
