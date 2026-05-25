---
name: project-setup
description: Use when initializing Codex workflow files.
---

# Project Setup

Initialize project workflow files.

## Procedure

1. Run `scripts/activate_project_dependencies.py --repo <repo> --json`.
2. Run `scripts/check_dependencies.py --plugin-root <plugin-root> --repo <repo> --json`.
3. Run `scripts/audit_context_tools.py --repo <repo> --json` for a read-only context tool audit.
4. Run `scripts/detect_project_mode.py --repo <repo> --json`.
5. Run `scripts/scaffold_workflow.py --repo <repo> --dry-run --json`.
6. If the plan is safe, run `scripts/scaffold_workflow.py --repo <repo> --json`.
7. Run `scripts/validate_workflow_state.py --repo <repo> --json`.
8. Report generated files, skipped files, context tool recommendations, risks, and next action.

## Notes

- Greenfield creates `AGENTS.md`, `.planning/`, `openspec/`, `initial-target-state`, `01-foundation`.
- Brownfield preserves rules and drafts architecture, conventions, commands, risks, current-system spec.
- Use `gsd-new-project` when the user wants full GSD project intake.
- Use `context-tool-audit` before applying any context cleanup or tool installation actions from the audit report.
- Generated workflow files include AI Coding Planning Rules; use `ai-native-tech-plan` for technical plan generation.

## Constraints

Do not overwrite `AGENTS.md` without `--force-agents`. Do not edit production code. Keep Superpowers, GSD, and OpenSpec project-local.
