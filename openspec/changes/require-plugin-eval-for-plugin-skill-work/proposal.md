## Why

Plugin and skill changes can look structurally correct while still carrying
poor trigger text, excessive context cost, or missing evaluation evidence. The
user has requested that Plugin Eval become an active gate for future plugin and
skill creation or updates.

## What Changes

- Add a repository workflow rule requiring Plugin Eval for future plugin and
  skill creation or updates.
- Require skill work to run `plugin-eval analyze` against the changed skill.
- Require plugin work to run `plugin-eval analyze` against the changed plugin
  bundle or the smallest relevant plugin path.
- Require evaluation findings and optimization decisions to be recorded in
  verification evidence.
- Update DevFlow AGENTS templates so generated project instructions carry the
  same rule.

## Capabilities

### New Capabilities

- `plugin-eval-quality-gate`: A workflow gate requiring Plugin Eval evaluation
  and optimization evidence for plugin and skill changes.

### Modified Capabilities

- None.

## Impact

- Updates repository `AGENTS.md`.
- Updates DevFlow `AGENTS.md` templates in development and release plugin trees.
- Adds tests that enforce the Plugin Eval rule remains present.
- Adds a memory note for future sessions, because the user explicitly requested
  future behavior.
