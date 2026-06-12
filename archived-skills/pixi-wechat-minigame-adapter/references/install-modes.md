# Install Modes

Use the installer with one of these modes:

## Overlay

Use `overlay` when the target repo already has a working PixiJS Web game and you are adding WeChat support.

Command:

```bash
python3 scripts/install_starter.py --mode overlay --text-module none --target-repo /path/to/repo
```

Overlay installs:
1. `src/wechat-main.ts`
2. `src/platform/prepareWeChatRuntime.ts`
3. `src/platform/WeChatPlatform.ts`
4. `src/platform/wechatWebGLCompat.ts`
5. `src/platform/wechatDebug.ts`
6. `src/platform/wechatStartupTrace.ts`
7. `src/platform/wechat-env.d.ts`
8. `src/platform/wechat-modules.d.ts`
9. `vite.wechat.config.ts`
10. `tools/build-wechat.mjs`
11. `tools/audit-wechat-build.mjs`
12. WeChat runtime/build regression tests
13. `docs/wechat/verification-matrix.md`
14. `docs/wechat/smoke-checklist.md`
15. standard `package.json` and `Makefile` fragments

Overlay customization seams:
1. wire `bootstrapWeChatGame()` into your existing boot sequence
2. ensure the target repo exposes a shared `RuntimePlatform` contract at `src/shared/contracts.ts`, or adapt the imports once during bootstrap
3. ensure `src/shared/config/gameConfig.ts` exposes the background color/config seam used by the platform layer, or adapt the import once during bootstrap
4. keep your gameplay scenes and systems platform-neutral

Use `--force` if you intentionally want to overwrite conflicting target files.

## Skeleton

Use `skeleton` when you want a fresh dual-target Pixi starter.

Command:

```bash
python3 scripts/install_starter.py --mode skeleton --text-module none --target-repo /path/to/repo
```

Skeleton installs:
1. everything in `overlay`
2. a minimal Web + WeChat project root
3. boot, platform, shared, scenes, and UI starter structure
4. a starter scene and generic coordinator
5. a ready-to-run `package.json`, `Makefile`, `index.html`, and lint/typecheck setup

Skeleton is designed to build out of the box after installing dependencies.

## Optional Text Module

Use `--text-module fixed-copy-glyph` to install the packaged fixed-copy text scaffold.

This module:
1. is optional
2. does not wire itself into gameplay automatically
3. gives you a place to keep fixed-copy strings and a generation script scaffold
4. should be adopted when mini-game text must be deterministic and runtime text generation is not acceptable
