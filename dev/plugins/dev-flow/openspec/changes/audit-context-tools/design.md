# Design: Audit context tools

## Approach

Add a focused library module, `workflow_context_tools.py`, plus two small CLI wrappers:

- `audit_context_tools.py` builds a deterministic analysis report.
- `apply_context_tool_actions.py` consumes that report and executes selected actions after explicit authorization.

The audit remains separate from the current required dependency checks so existing preflight behavior stays stable. The report can later be embedded into `doctor_workflow.py` or `check_dependencies.py`, but the first version keeps the blast radius small.

The audit categorizes tools into inventory, findings, recommendations, and actions. Actions are stable JSON objects with ids, type, target, reason, safety level, and required inputs. Cleanup actions disable global config entries rather than deleting files. Installation actions copy a known installed skill from the plugin cache into the target repo's `.codex/skills/`.

## Data Flow

1. Read `~/.codex/config.toml` with `tomllib` and preserve the raw text for later action application.
2. Inventory globally enabled plugin sections from `[plugins."<name>"]`.
3. Inventory global skills from `~/.codex/skills/*/SKILL.md`, including disabled status from `[[skills.config]]`.
4. Inventory installed cache skills from `~/.codex/plugins/cache/**/skills/*/SKILL.md`.
5. Inventory project-local skills from `<repo>/.codex/skills/*/SKILL.md`.
6. Detect repo signals from common files such as `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `Package.swift`, `*.xcodeproj`, `project.godot`, and Android Gradle files.
7. Load optional source catalogs from local marketplace JSON files or explicit HTTP(S) URLs.
8. Produce recommendations and action objects.
9. Apply script reads the saved report, verifies requested action ids, creates config backups, and performs only selected actions.

## Compatibility

Existing `check_dependencies.py`, preflight, and activation behavior must keep their current return codes. The audit script is advisory by default. The apply script defaults to dry-run and requires both a report file and either explicit `--action` ids or `--all-safe`; actual changes additionally require `--apply`.

## Testing

Add focused unit tests that create temporary Codex homes and repos.
