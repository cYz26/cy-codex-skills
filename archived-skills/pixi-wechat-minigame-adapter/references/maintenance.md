# Maintenance

This skill is the only source of truth for the canonical PixiJS WeChat mini-game solution.

## Update Order

Always update in this order:
1. canonical skill assets
2. canonical tests and validation scripts
3. references and troubleshooting notes
4. consuming business repos

Do not reverse that order.

## Required Follow-Through For New Failures

When a new failure mode is discovered, update all of:
1. the relevant template asset
2. the related regression test or validation script
3. `references/troubleshooting.md`
4. `references/validation-matrix.md` or `references/smoke-checklist.md` if the acceptance flow changes

## Changelog

### 2026-03-13

1. promoted `pixi-wechat-minigame-adapter` from a bootstrap bundle to the canonical solution
2. standardized single-screen-canvas ownership in generated `game.js`
3. narrowed `prepareWeChatRuntime()` to environment prep only
4. narrowed `WeChatPlatform` to read-only screen-canvas consumption
5. added overlay and skeleton install modes
6. added installer, manifest sync, and solution validation scripts
7. folded DevTools black-screen learnings into the standard troubleshooting path
