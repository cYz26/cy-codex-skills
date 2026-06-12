# Learning Log

Use this file for raw task-time learnings. Keep full event detail here and only a short summary in `status.md`.

## Entry Template

## [LRN-YYYYMMDD-001] short-slug
- id: `LRN-YYYYMMDD-001`
- type: `workflow`
- logged_at: `YYYY-MM-DD HH:MM TZ`
- status: `pending`
- trigger: `better_repeatable_workflow`
- summary: `One-line summary of the learning`
- details:
  - `What happened`
  - `What was wrong or newly discovered`
  - `What should happen next`
- related_files:
  - `path/to/file`
- pattern_key: `workflow.example`
- promotion_target: `skill-candidate:example-skill`
- see_also:
  - `LRN-YYYYMMDD-000`

## Allowed values
- `type`: `error`, `correction`, `workflow`, `convention`, `missing_capability`
- `status`: `pending`, `triaged`, `promoted`, `dismissed`
- `trigger`:
  - `unexpected_command_failure`
  - `unexpected_tool_failure`
  - `user_correction`
  - `self_correction`
  - `repo_convention_discovered`
  - `better_repeatable_workflow`
  - `missing_capability`
