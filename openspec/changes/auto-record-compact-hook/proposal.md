## Why

DevFlow can recommend `/compact` at checkpoint boundaries, but the user currently has to tell the assistant afterward so `.planning/STATE.md` and `.planning/compact-results/` can be updated. That leaves a manual gap exactly at the point where context was just compressed.

## What Changes

- Add DevFlow hook behavior that listens to Codex `PostCompact` lifecycle events for manual compaction.
- After manual compaction completes, record a completed compact result when the workflow state still has `compact_status: pending`.
- Reuse the existing compact result writer so `.planning/compact-results/<checkpoint>.json` and `.planning/STATE.md` stay authoritative.
- Keep the hook conservative: no action unless `trigger` is `manual`, workflow state is pending compact, and the current checkpoint file exists.

## Capabilities

### New Capabilities

- `devflow-compact-hook-recovery`: DevFlow `PostCompact` hook behavior for recording manual compact completion after `/compact`.

### Modified Capabilities

- `devflow-plugin-identity`: DevFlow hook packaging includes the new recovery hook entry while keeping existing hook configuration compatibility.

## Impact

- Affects DevFlow hook configuration in `dev/plugins/dev-flow/hooks.json` and `plugins/dev-flow/hooks.json`.
- Adds a focused hook script and compact recovery module under both DevFlow plugin roots.
- Adds development and release smoke tests for the new hook behavior.
- Does not add dependencies, change public plugin ids, change the `/compact` command, or archive any existing OpenSpec change.
