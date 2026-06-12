# 05-plan-first.md - Plan-First Workflow

Apply this workflow before editing files when a task touches multiple systems.

## Read-Only Scan Checklist

1. Identify Godot version lock from `project.godot`, README, CI, or repository conventions.
2. Locate entry scene and main gameplay loop scripts.
3. Inspect `export_presets.cfg` to see active targets (`Web`, `Android`, `iOS`, `Windows`, and others).
4. Discover quality commands from `Makefile`, scripts, or CI.
5. Identify constraints: platform, resolution, performance budget, package size, and input mode.

## Plan Template

Use this structure before coding:

1. Goal (one sentence)
2. Scope (`In` / `Out`)
3. Planned edits (files/scenes/scripts)
4. Validation commands (`fmt`, `lint`, `test` or `smoke`, export checks)
5. Risks and rollback strategy
