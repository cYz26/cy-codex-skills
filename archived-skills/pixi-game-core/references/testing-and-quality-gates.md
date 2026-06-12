# Testing and Quality Gates

Use this reference after any behavior-impacting PixiJS change.

## Default Command Chain

Run the nearest equivalent of:
1. `pnpm lint`
2. `pnpm typecheck`
3. `pnpm build`
4. `pnpm test`

If the repository packages generated text assets such as glyph atlases or bitmap fonts, regenerate them when copy changes before running the build chain.

If automated tests are absent, state that gap and run a manual smoke flow.

## Dual-Target Command Matrix

If the repository maintains both Web and WeChat mini-game outputs, prefer:
1. `pnpm lint`
2. `pnpm typecheck`
3. `pnpm build:web`
4. `pnpm build:wechat`
5. `pnpm test`

Use the single `pnpm build` path only when the project truly has one build target or one wrapper command that already covers both targets.

## Minimum Smoke Flow

Verify:
1. cold start reaches the first interactive scene
2. critical assets load without console errors
3. at least one scene transition works
4. pause and resume do not corrupt UI or state
5. destroy and reload do not duplicate listeners
6. pointer or touch interaction works on desktop and mobile emulation

## What to Report

After validation, report:
1. commands run
2. pass or fail summary
3. manual coverage
4. remaining risks

## Review Checklist

Check:
1. scene code avoids raw asset paths
2. systems are not tied to Pixi display objects without a good reason
3. input handling is normalized before gameplay
4. DOM or browser globals are isolated behind platform boundaries
5. resizing and scaling policy is defined once, not copied per scene

If future mini-game migration matters but the project is still pre-adaptation, also run the readiness checklist from `$pixi-mini-game-readiness`.

If the repository is already developing Web and WeChat outputs in parallel, also load `$pixi-web-wechat-dual-target`.
