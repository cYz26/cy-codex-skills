# Optimize DevFlow AGENTS Drift Review

## Why

DevFlow refresh now documents an AGENTS drift gate, but the durable mechanism is
still incomplete: the AGENTS template does not carry the refresh workflow, and
workflow validation only checks an older set of guidance markers. This can make
a project appear current after a DevFlow upgrade even when its active
`AGENTS.md` is missing newly introduced durable workflow rules.

## What Changes

- Make AGENTS drift review a required part of the `dev-flow-refresh` workflow.
- Add the DevFlow refresh workflow to the canonical AGENTS template in both the
  development and release plugin trees.
- Teach workflow validation to check for durable DevFlow sections that reflect
  current core flow and template guidance.
- Preserve the existing safety boundary: generated AGENTS candidates are merge
  inputs, not automatic overwrites.

## Capabilities

### Modified Capabilities

- `devflow-refresh-skill`: Refresh work now includes an explicit AGENTS drift
  review gate driven by template/core-flow comparison and validation markers.
- `devflow-workflow-validation`: Validation now reports missing durable AGENTS
  sections that indicate workflow guidance drift.

## Impact

- Updates DevFlow skill guidance, AGENTS templates, validation logic, tests, and
  release assets.
- No production dependencies.
- Does not auto-merge or overwrite project `AGENTS.md` files.
