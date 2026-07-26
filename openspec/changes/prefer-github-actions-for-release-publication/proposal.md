## Why

DevFlow already separates native Git transport from GitHub control-plane
credentials, but release routing still treats local `gh` authentication as the
primary control-plane path. A repository-owned, tag-triggered GitHub Actions
workflow can publish a deterministic release without local GitHub CLI
credentials, while preserving reviewable source, least-privilege permissions,
and immutable trigger identity.

## What Changes

- Add an Actions-first execution policy for deterministic, tag-bound GitHub
  release publication.
- Keep SSH/native Git as the preferred transport for commit and tag push when
  the configured remote passes the existing read-only preflight.
- Treat GitHub Actions, authenticated `gh`, and named-human web operation as
  ordered execution paths under the existing `github.control_plane_write`
  authorization rather than as new side-effect authority.
- Require workflow-in-trigger-commit verification, scoped `GITHUB_TOKEN`
  permissions, immutable identity checks, conflict detection, and
  post-publication readback before local promotion can start.
- Preserve a pushed immutable tag when an Action fails; do not delete or
  retarget it as automatic rollback.
- Add machine-readable route metadata, public workflow guidance, and focused
  regression tests.

## Capabilities

### New Capabilities

- `github-publication-routing`: Actions-first release publication routing,
  fallback order, authorization boundaries, identity checks, readback, and
  failure behavior.

### Modified Capabilities

None.

## Impact

Affected surfaces are the development DevFlow Git workflow helper, Git/GitHub
routing reference, project orchestration and verification skills, root and
generated project guidance, and focused source tests. No dependency,
credential configuration, workflow file creation, Git mutation, GitHub
publication, release promotion, installed-cache refresh, or generated release
sync is included.
