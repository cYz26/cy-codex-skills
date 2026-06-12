# AGENTS.md - Godot Development Rules

All behavior-impacting changes must be reproducible and verifiable.

## Engine Policy

1. Use repository-locked Godot version first.
2. If repository is not locked, default recommendation is Godot `4.6 stable`.
3. Upgrade engine only when explicitly requested.

## Required Validation Chain

For script/scene/resource changes, run and report in order:
1. `make fmt` (or explain why skipped)
2. `make lint`
3. `make test` (or at least `make smoke`)
4. If Web export/deploy is involved:
   - `make export-web`
   - `make web-smoke`

## Export Preset Rule

Preset name must exactly match entries in `export_presets.cfg`.

## Change Scope and Safety

1. Prefer minimal changes.
2. Avoid broad refactors unless requested.
3. Avoid deleting or renaming scenes/resources without migration and rollback notes.
