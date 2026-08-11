## Why

DevFlow 0.4.0 packages every Hook command through the host's bare `python3`,
but the released runtime imports `tomllib` unconditionally through the legacy
workflow inspection path. On macOS hosts where `python3` is Python 3.9, both
the migration reminder and aggregate Stop Hook terminate with
`ModuleNotFoundError` before they can emit a Codex-compatible response.

## What Changes

- Make the legacy workflow inspection module importable when the host Python
  does not provide `tomllib`.
- Preserve fail-closed cleanup behavior by classifying a GSD-bearing TOML
  configuration as manual review when a standards-compliant TOML parser is
  unavailable.
- Advance the source project-refresh evidence contract to revision 12 because
  the repaired legacy-uninstall module is a tracked refresh input; keep project
  schema 8 and add no migration step.
- Add public-entrypoint regressions for the migration reminder and Stop Hook
  with `tomllib` deliberately unavailable, plus direct Python 3.9 and current
  Python runtime qualification when those interpreters exist.
- Preserve Python 3.11+ behavior, Hook response schemas, project-refresh
  planning, and all explicit apply/cleanup authority boundaries.
- Publish the corrected runtime as immutable patch release `0.4.1`, promote the
  generated release counterpart, and refresh only the explicitly named
  internal `dev-flow@cy-codex-skills` cache after publication readback.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `devflow-plugin-quality`: Add packaged Hook runtime compatibility and
  fail-closed parser-unavailability requirements.

## Impact

- Source runtime and refresh evidence:
  `dev/plugins/dev-flow/scripts/workflow_legacy_uninstall.py` and
  `dev/plugins/dev-flow/.codex-plugin/project-migration.json`.
- Tests: public Hook subprocess coverage and focused legacy-uninstall
  classification coverage plus the revision-12 refresh-impact regression under
  `dev/plugins/dev-flow/tests/`.
- Generated runtime: an isolated release candidate must include the corrected
  module and pass source/release parity checks before any promotion.
- No Hook manifest, dependency, project schema, workflow state, public response
  schema, cleanup authority, or user configuration changes.
- On 2026-08-11 the user explicitly authorized the exact source commit,
  fast-forward `main` push, immutable `dev-flow-v0.4.1` tag and GitHub Release,
  publication readback, and internal named-cache refresh.
- Archive, PR creation, force push, release overwrite, other-plugin refresh,
  global Python/PATH changes, and consumer-project migration remain excluded.

## Skill Routing Ledger

- artifact-status: final
- kind: bug, workflow repair, and Hook runtime compatibility
- workflow-mode: Full OpenSpec
- capability-research: required/used - the installed Hook manifest, host
  interpreter, packaged runtime, and source import graph were verified live.
- decision-resolution: required/used - selected an optional parser boundary
  with fail-closed classification; no Open Questions remain.
- decision-grilling: skipped - the diagnosed failure and safe behavior are
  deterministic and require no product choice.
- implementation-planning: required/used - proposal, design, delta spec, tasks,
  validation commands, write set, rollback, and release boundary are recorded.
- architecture-guidance: required/used - the parser capability is isolated
  from Hook process startup without weakening legacy cleanup ownership checks.
- domain-language-modeling: skipped - no domain vocabulary or invariant changes.
- openspec-routing: required/used - runtime compatibility and error handling
  require Full OpenSpec.

## Goal Suitability Gate

The release follow-through is governed by Goal Contract
`DF-HOOK-PY39-0.4.1` in `TASK_LEDGER.md`. It binds the patch-release outcome,
verification evidence, exact external effects, exclusions, and stop
conditions without creating a separate implementation queue.
