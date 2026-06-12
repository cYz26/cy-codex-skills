# Smoke Checklist

Use this checklist after the command matrix passes.

## WeChat DevTools

1. Import the freshly generated `build/wechatgame-debug` output.
2. Confirm startup reaches the launcher or starter scene.
3. Confirm the screen is visible and not black.
4. Confirm the first interactive scene responds to input.
5. Confirm resize/safe-area layout is sane in the simulator.
6. Confirm debug logs do not show startup failure or repeated canvas rebinding.
7. Record result as `verified`, `partial`, or `blocked`.

## Device

1. Install the latest debug or release build on a real device.
2. Confirm startup reaches the first scene.
3. Confirm the screen is visible and input works.
4. Confirm safe area and status-bar offsets are sane.
5. Confirm first gameplay or scene transition works.
6. Confirm no startup crash or blank screen occurs after resume.
7. Record result as `verified`, `partial`, or `blocked`.

## If Visibility Fails

If logs reach `app-init` or `first-frame` but the screen is black, switch to [$pixi-wechat-black-screen](/Users/cY/.codex/skills/pixi-wechat-black-screen/SKILL.md).
