# Douyin Mini-Game Future Target Notes

This file is intentionally high-level. Use it to shape architecture now, not to implement a Douyin adapter today.

## Working Assumptions

Assume future Douyin mini-game support means:
1. a non-browser runtime boundary
2. vendor APIs exposed through `tt`
3. entry, lifecycle, storage, and rendering details that differ from normal Web builds
4. platform-specific release and packaging constraints that must be checked at implementation time

## What to Preserve Today

Keep these abstract:
1. launch context parsing
2. pause and resume hooks
3. storage services
4. share or social hooks
5. haptics or vibration hooks
6. open-data or leaderboard bridges

## What Not to Freeze in v1

Do not hardcode:
1. current package size limits
2. exact subpackage behavior
3. exact open-data flow
4. exact release review rules

Re-verify those with official docs when actual implementation starts.

## Official Sources to Re-Check Later

1. Douyin mini-game guide: `https://developer.open-douyin.com/m/docs/resource/zh-CN/mini-game/develop/guide/bytedance-mini-game`
2. Douyin open-data docs: `https://developer.open-douyin.com/docs/resource/zh-CN/mini-game/develop/guide/open-ability/open-data-base`
3. Douyin `tt.createImage`: `https://developer.open-douyin.com/docs/resource/zh-CN/mini-game/develop/api/drawing/picture/tt-create-image/`
