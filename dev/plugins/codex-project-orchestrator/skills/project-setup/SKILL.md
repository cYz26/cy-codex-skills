---
name: project-setup
description: Use when initializing Codex workflow files in a repo.
---

# Project Setup

Initialize project workflow files.

## Procedure

1. Run `scripts/activate_project_dependencies.py --repo <repo> --json`.
2. Run `scripts/check_dependencies.py --plugin-root <plugin-root> --repo <repo> --json`.
3. Run `scripts/detect_project_mode.py --repo <repo> --json`.
4. Run `scripts/scaffold_workflow.py --repo <repo> --dry-run --json`.
5. If the plan is safe, run `scripts/scaffold_workflow.py --repo <repo> --json`.
6. Run `scripts/validate_workflow_state.py --repo <repo> --json`.
7. Report generated files, skipped files, risks, and next action.

## Notes

- Greenfield creates `AGENTS.md`, `.planning/`, `openspec/`, `initial-mvp`, `01-foundation`.
- Brownfield preserves rules and drafts architecture, conventions, commands, risks, current-system spec.
- Use `gsd-new-project` when the user wants full GSD project intake.

## Constraints

Do not overwrite `AGENTS.md` without `--force-agents`. Do not edit production code. Keep Superpowers, GSD, and OpenSpec project-local.
