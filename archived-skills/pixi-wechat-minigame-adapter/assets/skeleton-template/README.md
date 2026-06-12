# Pixi WeChat Starter

This is the canonical `skeleton` starter for the `$pixi-wechat-minigame-adapter` skill.

## Commands

```bash
npm install
make typecheck
make lint
make test
make web
make wechat-debug
make audit
```

## Structure

1. `src/main.ts`: Web entry
2. `src/wechat-main.ts`: WeChat entry
3. `src/platform/`: platform bridge and WeChat runtime prep
4. `src/boot/`: bootstrap and coordinator
5. `src/scenes/`: starter scene
6. `docs/wechat/`: verification matrix and smoke checklist
