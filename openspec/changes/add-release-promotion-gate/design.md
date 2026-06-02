# Design: Release Promotion Gate

## Target State

Plugin and skill development can happen in `dev/`, but release packages remain
the installable source of truth. When a workflow reaches a verified boundary,
DevFlow checks development assets against their release counterparts. If a dev
asset has releasable changes, DevFlow applies an allowlist-based sync to the
release location, runs any asset-specific release build command, and then asks
for release validation before the work is considered ready to submit.

Plugin Eval uses the release target by default:

- `dev/plugins/<name>` resolves to `plugins/<name>` when that release package
  exists.
- `dev/skills/<name>` resolves to `<name>` when that release skill exists.
- Direct release paths evaluate as-is.
- Development paths remain available for diagnostics and source-quality checks.

## Scope / Non-Goals

In scope:

- Repository-local plugin and skill release target discovery.
- Dry-run check mode and explicit apply mode.
- Automatic apply from DevFlow stop hook when verification has passed.
- Release-target resolution for Plugin Eval guidance.
- DevFlow-specific packaged runtime build integration.
- Tests for drift detection, apply behavior, hook timing, and release eval
  target selection.

Non-goals:

- Cross-repository package publishing.
- External marketplace uploads.
- Silent sync during ordinary file edits or failing test runs.
- Full deletion/pruning of release-only compatibility files.
- Replacing Plugin Eval itself.

## Architecture Decisions

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| Sync at verification boundaries | Captures "developed enough" without copying half-finished edits. | Sync on every file write, which would pollute release with transient state. |
| Keep sync allowlist-based | Release packages should contain runtime files, not local reports or tests/fixtures unless explicitly shipped. | Copy whole directories, which already caused token and packaging pressure. |
| Add release-sync metadata per asset | DevFlow needs a packaged runtime archive; other assets can use direct copy. | Hard-code every plugin's behavior into one script. |
| Make hook auto-apply but require release validation after | Satisfies automatic trigger while keeping final readiness tied to release checks. | Only warn, which leaves the user to remember promotion manually. |
| Resolve Plugin Eval target through the sync CLI | Gives agents a deterministic way to prefer release paths. | Rely on prose-only instructions, which are easy to miss. |

## Release Sync Contract

The sync report contains:

- `status`: `current`, `pending`, `synced`, or `not_applicable`;
- `assets`: one record per dev plugin/skill with kind, name, source, release
  path, changed files, missing output files, and configured build commands;
- `evalTargets`: release-preferred mappings for detected assets.

Dry-run/check mode does not write files. Apply mode copies only included
runtime files and runs configured build commands. DevFlow's config excludes raw
release `scripts/` copying and invokes `dev/scripts/package_devflow_release_runtime.py`
to generate wrappers plus `devflow_runtime.pyz`.

## Capability Slices

### Slice 1: Contract and tests

Add OpenSpec artifacts and failing tests for discovery, drift, apply, hook
timing, and release eval target selection.

### Slice 2: Sync engine and CLI

Implement deterministic asset discovery, allowlist copying, release metadata,
and CLI report behavior.

### Slice 3: Gate and guidance

Wire the stop hook gate, update release-isolation docs and AGENTS template, then
mirror the release package through the new sync flow.

## Risks / Rollback

- Risk: hook-triggered sync changes files after dev validation. Mitigation:
  hook message requires release validation and Plugin Eval after sync.
- Risk: a plugin needs custom packaging. Mitigation: per-asset
  `.codex-plugin/release-sync.json` metadata supports build commands and
  excludes.
- Risk: direct importers depended on dev-only release files. Mitigation:
  release sync does not prune release-only files by default; DevFlow's packaged
  runtime change is separately covered by release smoke tests.
- Rollback: remove the sync CLI, hook entrypoint, metadata, docs updates, and
  hook registration. Existing release files remain usable.
