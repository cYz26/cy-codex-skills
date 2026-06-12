# Pixi WeChat Black Screen Pitfalls

## Symptom: `app-init` and `first-frame` log, but the screen is black

Likely cause:

1. Pixi rendered, but not to the canvas DevTools actually displays

Typical fix:

1. stop runtime canvas rediscovery
2. prebind one screen canvas in `game.js`
3. make platform and runtime prep layers reuse it only

## Symptom: `selected runtime canvas` points to `document.querySelectorAll('canvas')`

Likely cause:

1. platform code is trusting DOM discovery over the prebound global screen canvas

Typical fix:

1. remove document scanning from `WeChatPlatform`
2. resolve only from `globalThis.canvas`, `globalThis.screencanvas`, `GameGlobal.canvas`, or the dedicated internal screen-canvas key

## Symptom: colored probe pixels can be read back, but DevTools still shows black

Likely cause:

1. rendering reached a canvas object, but that object is not the visible screen canvas in DevTools

Typical fix:

1. align generated entry behavior with the WeChat single-screen-canvas contract
2. stop creating fallback display canvases later in boot

## Symptom: `CanvasRenderingContext2D is not defined`

Likely cause:

1. Pixi text or text metrics hit a missing global constructor in WeChat

Typical fix:

1. install a matcher-based `CanvasRenderingContext2D` global in runtime prep
2. keep later `wx.createCanvas()` calls offscreen-only

## Symptom: `Cannot set property document of #<Window> which has only a getter`

Likely cause:

1. the generated entry tries to overwrite a DevTools-provided native `document`

Typical fix:

1. detect and reuse existing `document`
2. do not direct-assign to `window.document`
3. synthesize a document only when none exists

## Symptom: `parent.children.includes is not a function`

Likely cause:

1. code assumed `children` is a mutable array, but DevTools exposed `HTMLCollection`

Typical fix:

1. maintain a private child store for synthetic linkage
2. stop depending on native `children.includes`, `push`, or `splice`

## Symptom: several `wx.createCanvas` logs appear immediately after boot

Interpret carefully:

1. one `screen` canvas is expected
2. additional early `offscreen` canvases may come from text measurement or render helpers

Action:

1. make sure only the first screen canvas is bound to global screen-canvas aliases
2. verify later offscreen canvases never overwrite those aliases
