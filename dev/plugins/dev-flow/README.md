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
- Workflow mode routing selects Full OpenSpec, Lightweight Ledger, or Prototype
  Mode before execution. Full OpenSpec remains mandatory for behavior, API,
  data, migration, integration, permission, error-handling, and compatibility
  changes; `.dev-flow.json` can enable Lightweight Ledger only for low-risk
  work.
- Hooks use installed cache paths and support `off`, `warn`, and `block` modes.
  Diagnostics preserve the Codex hook event schema while reporting the current
  stage, failed gates, next action, and recommended skill or command.
- Agent Reach is deprecated and not recommended for DevFlow automation.

## Workflow Modes

Configure lightweight routing in `.dev-flow.json`:

```json
{
  "workflow": {
    "lightweight_ledger": {
      "enabled": true
    }
  }
}
```

Lightweight ledgers must include Target State, Scope / Non-Goals, Validation
Commands, Execution Log, and Completion Claim. Prototype Mode is only for an
explicit spike, prototype, proof of concept, or demo request, and the output
must be marked non-production with cleanup or promotion criteria.

Hook modes live under `hook.mode` in `.dev-flow.json` and accept `off`, `warn`,
or `block`. Warn mode exits successfully while still emitting diagnostics; block
mode exits non-zero for blocking diagnostics; off mode emits no model-visible
diagnostic.

## Archive Automation

Archive policy lives under `archive.policy` in `.dev-flow.json` and defaults to
`confirm-on-risk`:

```json
{
  "archive": {
    "policy": "confirm-on-risk"
  }
}
```

Supported policies are:

- `confirm-on-risk`: archive can proceed after explicit archive intent when the
  change is ready and no risk is present; risk requires confirmation.
- `manual`: archive always requires an explicit approval gate.
- `auto-after-explicit-request`: if the user already asked to archive after
  verification, clean archive can proceed once readiness is true.

Inspect readiness without mutating files:

```bash
python3 dev/plugins/dev-flow/scripts/archive_status.py --repo . --change <change> --json
```

The pre-archive hook guards mutating archive operations such as `openspec
archive`, `openspec-archive-change`, `mv`/`git mv` into
`openspec/changes/archive`, and `rm`/`git rm` of active changes. Read-only
status, validation, grep, and file inspection commands are not archive-gated.
Under `confirm-on-risk`, risky archive mutations are blocked even when general
hook mode is `warn`; set `hook.mode` to `off` only when intentionally opting out
of DevFlow archive protection.

## Dependency Provenance

External workflow dependency records are maintained in
`dev/plugins/dev-flow/docs/dependency-provenance.json`. Dependency reports read
that catalog and include each dependency's expected version, installed version,
binary path, install command, smoke command/result, source, last verified date,
and status (`verified`, `dependency_drift`, `missing`, or `smoke_failed`).
Read-only checks report drift without running installers; mutating install and
update commands remain behind explicit apply mode.

## Plugin Project Migration

`plugin-project-migration` detects drift after plugin or skill runtime updates.
The automatic path is sync-only: hooks and updater checks can remind, but they
do not edit `AGENTS.md`, `.agents/skills`, legacy `.codex/skills`, OpenSpec,
planning files, or scripts.
Reviewed apply mode refreshes declared project-local skill symlinks only when
targets are missing or already symlinks.

## Release Promotion

Develop plugins and standalone skills under `dev/`. At verified workflow
boundaries, `release_promotion_gate.py` promotes allowlisted runtime assets to
their release counterparts and then asks for release validation. Use
`sync_release_assets.py --apply --json` for an explicit sync, or
`sync_release_assets.py --eval-target <path> --json` to resolve the
release-first Plugin Eval target.

The packaged runtime archive is audited by
`scripts/devflow_runtime.MANIFEST.json`, `scripts/devflow_runtime.sha256`, and
`scripts/devflow_runtime.SOURCE_COMMIT`. Verify the release runtime with:

```bash
python3 plugins/dev-flow/scripts/verify_release_runtime.py --plugin-root plugins/dev-flow --json
```

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
