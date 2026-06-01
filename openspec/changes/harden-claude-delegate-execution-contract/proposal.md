# Proposal: Harden Claude Code Delegate Execution Contract

## Why

The current `claude-code-delegate` workflow lets Codex invoke Claude Code, but
its skill text still leaves room for Codex to do the real execution after
Claude returns. That defeats the purpose of delegation: the delegated task
should run inside the local Claude Code process, while Codex remains the
supervising workflow owner that checks scope, process evidence, diffs, tests,
and final results.

## What Changes

- Define Claude Code delegation as a worker contract, not a read-only
  confirmation step.
- Wrap delegated prompts with a mode-specific contract so Claude Code is told
  to complete the full bounded task inside its run.
- Keep Codex responsible for independent verification, workflow state, and
  reporting, but not for silently completing unfinished delegated execution.
- Update the DevFlow skill and README guidance so this applies to all delegated
  tasks, including but not limited to Git staging, commits, and pushes.
- Add regression coverage for the prompt contract and packaged skill wording.

## Capabilities

### Modified Capabilities

- `claude-code-task-delegation`: Clarifies that apply-mode delegation owns full
  task execution inside Claude Code, while Codex owns supervision and
  verification.

## Impact

- Affected code: DevFlow Claude Code delegation wrapper, skill, README, tests,
  and release-copy packaging under `dev/plugins/dev-flow/` and
  `plugins/dev-flow/`.
- Affected workflow: Codex should delegate complete execution tasks to Claude
  Code when the skill is invoked, then verify the result instead of taking over
  unfinished execution.
- Dependencies: No new production dependencies. Uses the existing local
  `claude` CLI wrapper.
