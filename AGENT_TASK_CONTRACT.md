# Agent Task Contract

## Goal

Describe the final delegated deliverable in one or two concrete sentences.

## Scope

- Allowed: list the exact files, directories, or read-only areas the worker may
  inspect or modify.
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
