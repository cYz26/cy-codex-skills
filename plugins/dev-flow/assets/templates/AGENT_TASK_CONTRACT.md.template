# Agent Task Contract

## Goal

Describe the final delegated deliverable in one or two concrete sentences.

## Worker ID

`<worker-id>`

Use one repository-task-unique ID for this worker. Read-only explorers and
reviewers require an ID too.

## Scope

- Allowed write set for worker `<worker-id>` only:
  - `<exact-repository-relative-path>`
- The write-set owner must match this contract's Worker ID. Use one contract per
  worker. Write sets must be disjoint; repeat `--contract` when validating
  multiple contracts. Worker IDs must be unique across all files.
- Allowed read-only scope: list the exact files or directories the worker may
  inspect without modifying.
- Primary-owned shared paths: never assign root control-plane files,
  `.planning/devflow/**`, `openspec/**`, any nested `.codex-plugin/**`, or
  generated `plugins/**` release paths to a worker. The primary agent owns
  integration, final verification, and the completion claim.
- Forbidden: list boundaries the worker must not touch, including shared
  workflow files, release assets, unrelated modules, secrets, destructive
  commands, or any path outside the named scope.

## Constraints

- Compatibility: list version, platform, API, or migration limits.
- Safety: list security, privacy, permission, data-loss, or destructive-action
  limits.
- Style: list project conventions, dependency limits, and formatting
  constraints.
- Performance: list latency, memory, token, or runtime limits when relevant.

## Verification

List exact commands the worker must run, for example:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest path.to.test_module
```

For read-only explorer or review tasks, write an explicit rationale such as:

`Not applicable: this is a read-only explorer task; verify by reporting inspected files and residual risks.`

## Evidence

The worker must report:

- changed files
- commands run
- test logs or validation results
- unverified areas
- risk notes

## Human Gate

The worker must wait for human review before expanding scope, touching
forbidden files, changing public APIs or compatibility behavior, running
destructive commands, skipping required validation, or continuing with failing
tests or unresolved risk notes.
