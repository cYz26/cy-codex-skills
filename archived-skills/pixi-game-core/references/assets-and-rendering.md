# Assets and Rendering Rules

Use this reference when the task touches assets, loading, rendering, input, or UI composition.

## Asset Policy

Require manifest-driven assets.

Rules:
1. Give every asset a stable alias.
2. Keep aliases in one manifest or bundle registry.
3. Separate critical boot assets from lazy scene assets.
4. Do not hardcode relative asset URLs inside gameplay code.
5. Keep versioning or CDN policy outside scene logic.

Good ownership split:
1. `assets/manifest/`: aliases, bundles, metadata
2. `assets/loaders/`: preload orchestration
3. `scenes/`: request named bundles, not raw paths

## Rendering Policy

Default to canvas-first rendering for core gameplay.

Allow HTML overlays only for:
1. debug panels
2. launcher chrome
3. account or payment shells outside gameplay

Do not make combat, puzzle, or timing-critical UI depend on DOM layout.

## Resolution and Layout

Set a clear design resolution and scaling rule in `GameBootConfig`.

Track:
1. design width and height
2. safe-area handling policy
3. resize policy
4. texture scale policy

Avoid ad hoc per-scene resize math.

## Input Policy

Normalize browser input before it reaches gameplay code.

Prefer:
1. semantic game actions
2. pointer abstraction that can map mouse and touch
3. one source of truth for hit-testing and gesture policy

Avoid:
1. reading DOM events directly inside scene logic
2. separate mouse and touch code paths for the same interaction
3. coupling gesture state to HTML element listeners

## Performance Bias

Before micro-optimizing, check:
1. asset size and count
2. overdraw from layered UI
3. unnecessary filters or masks
4. texture churn during scene transitions
5. repeated object creation in hot loops

Use Pixi official performance docs for API-specific tuning decisions.
