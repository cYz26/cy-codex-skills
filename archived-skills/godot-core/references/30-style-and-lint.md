# 30-style-and-lint.md - GDScript Style and Automation

## Style Rules (Required)

1. Follow official Godot GDScript style guidance for naming, layout, and structure.
2. Keep scripts readable and typed for public APIs.

## Automation (Required)

Standard quality chain:
1. `make fmt` -> `gdformat .`
2. `make lint` -> `gdlint .`

If repository uses different commands, run their equivalent formatter/lint tools and report mapping.

## Pre-commit (Recommended)

If team uses Git hooks, enable `.pre-commit-config.yaml` with `gdformat` and `gdlint` hooks so issues are caught before commit.
