# Dual-Target Validation Gates

Use the nearest matching gate set after a change.

## Pure Shared Logic

Run:
1. `pnpm lint`
2. `pnpm typecheck`
3. `pnpm test`

Add both builds if contracts or serialization touched runtime startup or persistence.

## Shared Runtime, Scene, or Asset Policy Changes

Run:
1. `pnpm lint`
2. `pnpm typecheck`
3. `pnpm build:web`
4. `pnpm build:wechat`
5. `pnpm test`

Also run Web smoke. Add WeChat smoke if layout, lifecycle, assets, text rendering, or input behavior changed.

## Asset, Font, Text, or Packaging Changes

Run:
1. regenerate any packaged glyph atlas, bitmap font, or other text asset the repo uses
2. `pnpm lint`
3. `pnpm typecheck`
4. `pnpm build:web`
5. `pnpm build:wechat`
6. `pnpm test`

Run Web smoke and WeChat smoke if visible copy, asset loading, or startup packaging changed.
If the project uses a fixed-copy glyph atlas, include a test or explicit check that source copy and packaged glyph coverage still match after the rebuild.

## Platform Bridge or Build Changes

Run:
1. `pnpm lint`
2. `pnpm typecheck`
3. `pnpm build:web`
4. `pnpm build:wechat`
5. `pnpm test`

Run WeChat smoke. Re-run Web smoke if shared contracts or boot flow changed.

## Documentation-Only Rule Changes

Run:
1. any skill validation affected by the change
2. manual consistency check across AGENTS, current-state, and project-specific rules

No app build is required unless commands, boundaries, or examples were updated from stale assumptions.
