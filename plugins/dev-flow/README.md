# DevFlow

DevFlow is the Codex workflow router for setup, planning, OpenSpec changes,
context health, verification, and plugin maintenance. Runtime code is packaged
under `scripts/`; detailed procedure stays in individual skills.

## Core Capabilities

- `project-setup`, `feature-intake`, `change-plan`, and
  `project-orchestrator` route common project work.
- `ai-native-tech-plan`, `context-health-check`, `checkpoint-compact`,
  `plugin-project-migration`, and `codex-updater` cover explicit specialist
  workflows.
- Hooks use installed cache paths and are advisory unless a stop/check policy
  returns a block.
- Agent Reach is deprecated and not recommended for DevFlow automation.

## Plugin Project Migration

`plugin-project-migration` detects drift after plugin or skill runtime updates.
The automatic path is sync-only: hooks and updater checks can remind, but they
do not edit `AGENTS.md`, `.codex/skills`, OpenSpec, planning files, or scripts.
Reviewed apply mode refreshes declared project-local skill symlinks only when
targets are missing or already symlinks.

## Release Promotion

Develop plugins and standalone skills under `dev/`. At verified workflow
boundaries, `release_promotion_gate.py` promotes allowlisted runtime assets to
their release counterparts and then asks for release validation. Use
`sync_release_assets.py --apply --json` for an explicit sync, or
`sync_release_assets.py --eval-target <path> --json` to resolve the
release-first Plugin Eval target.

## Repair Solution Discipline

For bugs, workflow repair, and mechanism failures, start from systemic repair:
root cause, affected contracts, durable prevention, tests, docs, compatibility,
and verification. Execution may still choose systemic, minimal, staged, or
deferred repair based on current risk and validation cost.

## SubAgent Strategy

DevFlow is the policy/router layer for SubAgents. It recommends delegation for
independent domains, disjoint write sets, repeated investigation pressure,
repeated command failures, or bounded review needs. DevFlow does not spawn subagents from scripts or hooks, and Codex should not spawn them without
explicit user authorization or an approved delegated workflow.

When authorized, route to `gsd-execute-phase`, `subagent-driven-development`,
`dispatching-parallel-agents`, or `executing-plans`. The main agent owns OpenSpec artifacts, `.planning/STATE.md`, verification evidence, shared docs,
and final integration unless shared files are explicitly serialized. Each
SubAgent result reports status (`DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`), files changed or inspected, commands or tests run, residual
risks, and review needs.

## Verification

Run:

```bash
python3 -m unittest discover -s dev/plugins/dev-flow/tests
python3 -m unittest discover -s plugins/dev-flow/tests
node /Users/cY/.codex/plugins/cache/openai-curated/plugin-eval/45fe2bdd/scripts/plugin-eval.js analyze plugins/dev-flow --format markdown
```
