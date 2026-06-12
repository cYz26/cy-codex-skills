---
name: godot-core
description: Plan-first core workflows for Godot 4 feature implementation, bug fixing, architecture refactor, and performance diagnosis with strict validation gates. Use when Codex edits common Godot project files (.godot, .tscn, .tres, .gd, .cs) and needs repeatable quality checks, decoupling conventions, testing flow, or evidence-based debugging.
---

# Godot Core

Use this skill for day-to-day Godot engineering tasks that are not primarily Web export tuning or mini-game product balancing.

## 1) Read-Only Snapshot First

1. Run `scripts/godot_project_snapshot.sh <project-root>` before editing files.
2. Confirm engine version, entry scene, autoloads, script stack, export presets, and quality gate availability.
3. If baseline files are missing and user asks for setup, use templates in `assets/templates/`.

## 2) Plan-First Gate

If change touches multiple systems, produce a short plan before coding.
Use `references/05-plan-first.md`.

## 3) Definition of Done (Mandatory)

Run in order after behavior-impacting changes:
1. `make fmt` (or repository equivalent)
2. `make lint`
3. `make test` (or `make smoke` if tests are unavailable)

State exact commands and summarized results in handoff.

## 4) Core Engineering Rules

1. Keep edits minimal and local.
2. Keep one responsibility per scene root.
3. Prefer typed GDScript APIs.
4. Use signals for decoupled events.
5. Use groups for one-to-many broadcast.
6. Use autoload for focused global services only.
7. Avoid brittle cross-tree hard node paths for core logic.
8. Keep `_physics_process`, `_process`, and input callbacks semantically correct.

See:
1. `references/godot-architecture.md`
2. `references/60-decoupling.md`

## 5) Debug and Performance Evidence

For performance or runtime incidents, provide reproducible evidence and before/after metrics.
See:
1. `references/70-debug-perf.md`
2. `references/troubleshooting-checklists.md`

## 6) Escalate to Specialized Subskills

1. Use `$godot-web-export` when primary scope is Web export, deployment headers, cache policy, or browser runtime failures.
2. Use `$godot-mini-game` when primary scope is mini-game constraints, short-loop balancing, package budget, or mini-game release checklist.

## Resource Map

1. `scripts/godot_project_snapshot.sh`: baseline project scan.
2. `references/workflows.md`: feature/bug/perf/export execution flow.
3. `references/05-plan-first.md`: plan template and trigger conditions.
4. `references/30-style-and-lint.md`: style and lint baseline.
5. `references/50-testing.md`: test and smoke conventions.
6. `references/60-decoupling.md`: decoupling conventions.
7. `references/70-debug-perf.md`: performance evidence protocol.
8. `references/80-release-policy.md`: version and release policy.
9. `references/godot-architecture.md`: architecture patterns.
10. `references/troubleshooting-checklists.md`: diagnosis checklist.
11. `assets/templates/`: drop-in project templates (`AGENTS.md`, `Makefile`, `.pre-commit-config.yaml`, smoke runner, constraints).
