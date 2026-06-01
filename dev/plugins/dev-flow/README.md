# DevFlow

DevFlow is the Codex workflow router for project setup, planning, OpenSpec
change work, context health, verification, and plugin maintenance. It keeps the
runtime package self-contained while pushing detailed procedures into skills and
scripts.

## Core Capabilities

- Brownfield and greenfield project setup through `project-setup`.
- Feature, bug, refactor, and workflow triage through `feature-intake`.
- OpenSpec proposal/change routing through `change-plan`.
- AI-native implementation planning through `ai-native-tech-plan`.
- Context-health and checkpoint/compact gates through `context-health-check`
  and `checkpoint-compact`.
- Plugin project migration sync for detecting project-local config drift after
  plugin or skill runtime updates.

## Runtime Hooks

Hooks call installed cache scripts with `python3
"${CODEX_HOME:-$HOME/.codex}/plugins/cache/..."` paths so they work outside the
source checkout. Hook checks are advisory unless a specific stop/check policy
returns a blocking response.

Agent Reach is deprecated and not recommended for new DevFlow automation.

## Plugin Project Migration

Use `plugin-project-migration` when plugin or skill runtime updates may require
project-local configuration updates. The automatic path is sync-only: hooks and
updater checks can detect drift and emit reminders, but they do not edit
`AGENTS.md`, `.codex/skills`, `openspec/`, `.planning/`, or project scripts.

Read-only sync:

```bash
python3 scripts/plugin_project_migration.py --repo /path/to/repo --json
```

Apply reviewed safe migrations:

```bash
python3 scripts/plugin_project_migration.py --repo /path/to/repo --apply --json
```

Apply mode currently refreshes declared project-local skill symlinks only when
the target is missing or already a symlink. Audit artifacts are written under
`.dev-flow/plugin-project-migration/`.

## Repair Solution Discipline

For bug fixes, workflow repair, and mechanism failures, DevFlow uses systemic
and thorough solution first framing: root cause, affected contracts, durable
prevention, tests, docs, compatibility concerns, and verification. Execution can
still choose a systemic repair, minimal fix, staged repair, or deferred follow-up
based on current risk and validation cost.

## SubAgent Strategy

DevFlow is the policy/router layer for SubAgents. GSD and Superpowers own the
execution mechanics; DevFlow decides when delegation is useful, records the
authorization boundary, and keeps workflow evidence authoritative.

Recommend SubAgents for independent domains, disjoint write sets, repeated
investigation pressure, repeated command failures, or bounded review needs.
DevFlow does not spawn subagents from scripts or hooks, and Codex should not
spawn them without explicit user authorization or an approved workflow that
allows delegated parallel work.

When authorized, route execution to existing systems: `gsd-execute-phase` for
approved GSD phase waves, `subagent-driven-development` for task-by-task
implementation, `dispatching-parallel-agents` for independent research or
review, and `executing-plans` as the inline fallback.

The main agent owns OpenSpec artifacts, `.planning/STATE.md`, verification
evidence, shared README/docs coordination, and final integration unless those
shared files are explicitly serialized. Every SubAgent result should report
status (`DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`), files
changed or inspected, commands or tests run, residual risks, and review needs.

## Verification

Development tests live under `dev/plugins/dev-flow/tests`. The release plugin
keeps a compact discovery entry in `plugins/dev-flow/tests` and stores the larger
release test fixtures under `fixtures/release-tests`, which keeps Plugin Eval
budget focused on runtime guidance while preserving `unittest discover` coverage.

```bash
python3 -m unittest discover -s dev/plugins/dev-flow/tests
python3 -m unittest discover -s plugins/dev-flow/tests
node /Users/cY/.codex/plugins/cache/openai-curated/plugin-eval/8770e9d2/scripts/plugin-eval.js analyze plugins/dev-flow --format markdown
```
