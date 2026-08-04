## Why

DevFlow currently pins OpenSpec `1.6.0`, while the latest formal npm release is
`1.7.0`. OpenSpec 1.7 keeps the existing Node floor and six-skill core profile,
but materially improves Codex skills-only delivery, current-context handling,
spec sync/archive safety, artifact ordering, and stale-CLI detection; DevFlow
should adopt those released fixes without weakening its deterministic,
project-local workflow boundary.

## What Changes

- Pin the supported OpenSpec CLI, installer, updater, diagnostics, and generated
  skill contract to the exact formal release `1.7.0`.
- Preserve DevFlow's isolated `core` generation command and exact six-skill
  allowlist; continue copying verified skills into project-local
  `.agents/skills/` without creating Codex prompt commands or changing global
  OpenSpec configuration.
- Refresh the six generated OpenSpec skills and their `generatedBy` contract to
  `1.7.0`, including the 1.7 runtime-context, operation-guidance, sync, and
  archive safeguards.
- Update dependency provenance, tests, documentation, release runtime, and
  updater behavior so `1.6.0` is reported as stale and only the pinned 1.7.0
  repair command is recommended.
- Validate compatibility against the current repository, the generated release
  plugin, and isolated OpenSpec 1.7 fixtures before any local plugin/cache
  refresh.
- Submit the reviewed upgrade directly to the verified `main` branch through
  native Git transport, then refresh only `dev-flow@cy-codex-skills` and this
  project's six OpenSpec skills and read back remote/local parity.

## Capabilities

### New Capabilities

- `devflow-openspec-release-upgrades`: Evidence-gated adoption of a formal
  OpenSpec release while retaining DevFlow's exact project-local skill and
  canonical-workflow boundaries.

### Modified Capabilities

- None.

## Impact

- Dependency policy and provenance under
  `dev/plugins/dev-flow/docs/dependency-provenance.json`.
- OpenSpec generation, verification, activation, updater, migration, and
  dependency-diagnosis code under `dev/plugins/dev-flow/`.
- The six project-local generated OpenSpec skills and their release-package
  counterparts.
- Version-specific regression tests, DevFlow guidance/templates, packaged
  runtime manifests, and release-target Plugin Eval evidence.
- The explicitly named OpenSpec CLI installation and current-project skill
  refresh after source/release verification.
- The user's 2026-08-04 follow-through authorization covers scoped commits,
  native push to `origin/main`, and a post-push targeted local refresh. PR,
  GitHub Release publication, archive, unrelated updater apply, legacy cleanup,
  and unrelated project migration remain outside this request.
