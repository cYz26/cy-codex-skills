# Validation Matrix

The standard command matrix is mandatory for both overlay and skeleton installs.

## Required Commands

1. `make typecheck`
2. `make lint`
3. `make test`
4. `make web`
5. `make wechat`
6. `make wechat-debug`
7. `make audit`

## Evidence Language

Use these labels in notes, PRs, or status docs:
1. `verified`: command or smoke flow completed successfully
2. `partial`: some coverage exists but not the full expected path
3. `pending`: not yet run
4. `blocked`: could not be completed, with reason

Do not mark missing device coverage as `verified`.

## Acceptance

An install is accepted only when:
1. all required commands pass locally
2. DevTools smoke checks are `verified`
3. device smoke checks are recorded as `verified`, `partial`, or `blocked`
4. any remaining risks are written down explicitly

## Template Validation

The canonical solution itself must keep these checks green:
1. `python3 /Users/cY/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/cY/.codex/skills/pixi-wechat-minigame-adapter`
2. `python3 scripts/sync_starter_manifest.py --check`
3. `python3 scripts/validate_solution.py`

## When To Expand Validation

Add or expand tests when a new failure mode changes:
1. screen-canvas ownership
2. DevTools-native DOM reuse
3. offscreen canvas isolation
4. build packaging
5. audit behavior
6. text-module workflows
