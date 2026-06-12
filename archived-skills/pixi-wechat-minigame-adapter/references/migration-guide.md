# Migration Guide

The bundled starter is guaranteed only for `PixiJS v8 + TypeScript + Vite`.

If your repo is outside that envelope:
1. do not copy the starter blindly
2. use `references/architecture.md` as the invariant contract
3. port the solution layer by layer:
   - generated entry and screen-canvas ownership
   - runtime preparation
   - platform bridge
   - build packaging
   - audit step

Common migration cases:
1. non-Vite bundlers
   - keep the runtime contract
   - replace only the bundler-specific config and output paths

2. non-TypeScript repos
   - port the runtime files carefully
   - preserve the same global keys and ownership rules

3. pre-Pixi-v8 repos
   - do not assume runtime behavior is identical
   - validate text, renderer preference, and unsafe-eval requirements separately
