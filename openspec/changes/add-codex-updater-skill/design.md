## Context

The canonical updater now lives at
`dev/plugins/dev-flow/scripts/codex_auto_update_plugins_skills.py`, with a root
wrapper at `dev/scripts/codex_auto_update_plugins_skills.py` and a release copy
under `plugins/dev-flow/scripts/`. The script already supports dry-run checks,
apply mode, plugin install refresh planning, plugin cache verification, and
Agent Reach exclusion.

The missing piece is a skill-level entrypoint. Users can ask Codex to run the
script, but future agents have no project-local workflow that says which command
to use, what to summarize, and when apply mode is allowed.

## Goals / Non-Goals

**Goals:**

- Add a concise DevFlow skill that triggers on Codex plugin/skill update checks.
- Make dry-run mode the default required first step.
- Require explicit user approval before apply mode unless the user already asked
  to update/apply in the latest request.
- Keep the skill anchored to the canonical updater script instead of duplicating
  updater logic.
- Package the skill in development and release plugin trees.

**Non-Goals:**

- Reimplement update detection inside the skill.
- Enable or resume the paused automation.
- Refresh the installed DevFlow cache during this change.
- Reintroduce Agent Reach update behavior.

## Decisions

- **Use a skill-only wrapper, not a new command.** The updater command already
  owns deterministic behavior and tests. The skill should route the agent to that
  command and explain reporting/confirmation expectations.
- **Allow implicit invocation.** The trigger is narrow and the skill's first step
  is read-only dry-run. This makes common requests like "检查 Codex 插件更新" work
  without requiring the exact skill name.
- **No bundled helper script.** A helper would duplicate the canonical updater
  path and add another sync surface. The skill points directly to the existing
  wrapper command.
- **Test by artifact assertions.** The behavior is documentation/process, so
  tests verify packaging, trigger language, dry-run/apply guardrails, canonical
  command references, result categories, and Agent Reach exclusion.

## Risks / Trade-offs

- **Skill can become stale if script flags change** → Keep the skill command
  minimal and cover required flags in tests.
- **Implicit triggering could lead to unintended updates** → The skill requires
  dry-run first and only permits `--apply` after explicit user intent.
- **Installed plugin cache will not include the skill immediately** → Report that
  users must reinstall/refresh `dev-flow@cy-codex-skills` after source changes if
  they want the skill available from the installed cache.
