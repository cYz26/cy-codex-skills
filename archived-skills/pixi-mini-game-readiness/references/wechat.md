# WeChat Mini-Game Future Target Notes

This file is intentionally high-level. Use it to avoid bad architecture now, not to implement a WeChat adapter today.

## Working Assumptions

Assume future WeChat mini-game support means:
1. a non-browser runtime boundary
2. vendor APIs exposed through `wx`
3. game entry and packaging rules that differ from normal Web builds
4. lifecycle, storage, networking, and open-data capabilities that require platform wrappers

## What to Preserve Today

Keep these abstract:
1. app launch parameters
2. pause and resume lifecycle
3. storage access
4. network access
5. share hooks
6. leaderboard or open-data hooks

## What Not to Freeze in v1

Do not hardcode:
1. current package size numbers
2. exact subpackage policy
3. exact open-data integration flow
4. exact domain whitelist or release review requirements

Re-verify those with official docs when actual implementation starts.

## Official Sources to Re-Check Later

1. WeChat mini-game docs: `https://developers.weixin.qq.com/minigame/dev/`
2. Official examples: `https://github.com/wechat-miniprogram/minigame-demo`
3. Official typings: `https://github.com/wechat-miniprogram/minigame-api-typings`
