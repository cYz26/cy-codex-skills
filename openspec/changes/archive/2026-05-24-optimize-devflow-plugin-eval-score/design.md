## Context

The DevFlow rename is implemented, but Plugin Eval still identifies structural quality issues in the release package:

- `default-prompt-too-many` because the manifest exposes four default prompts.
- Heavy trigger/invoke budget, primarily from verbose skill metadata and always-visible skill bodies.
- Heavy deferred budget, primarily from scripts and documentation.
- `py-complexity-high` and long lines, concentrated in `workflow_context_tools.py` and related helpers.
- `py-tests-missing` for the release package because tests only exist in the development package.

The goal is to improve the actual package shape, not only suppress findings.

## Goals / Non-Goals

**Goals:**

- Keep DevFlow's public identity and skill protocol stable.
- Make the release manifest conform to Codex's three-default-prompt behavior.
- Reduce skill metadata token pressure without making routing ambiguous.
- Refactor context-tool audit/apply code into focused modules with clear responsibilities.
- Preserve existing CLI imports and `workflow_lib` exports.
- Add release-package smoke tests that validate packaged behavior.
- Verify the result with unit tests, preflight, OpenSpec validation, and Plugin Eval.

**Non-Goals:**

- Do not rename existing skill names.
- Do not remove context-tool audit/apply functionality.
- Do not add third-party dependencies.
- Do not copy the full development test suite into the release package.
- Do not archive this change automatically.

## Decisions

1. Keep `workflow_context_tools.py` as a compatibility facade.
   - Rationale: existing CLIs and `workflow_lib.py` import from this module. A facade avoids breaking consumers while allowing focused internal modules.

2. Split context-tool responsibilities by behavior.
   - `workflow_context_inventory.py`: reads config, global/project skills, installed cache, project signals, context pressure.
   - `workflow_context_catalog.py`: reads local/remote catalogs and normalizes candidate tools.
   - `workflow_context_recommendations.py`: builds findings, recommendations, and action dictionaries.
   - `workflow_context_actions.py`: validates, dry-runs, applies actions, and handles backups/config edits.
   - `workflow_context_tools.py`: orchestrates audit and re-exports apply behavior.

3. Add compact release smoke tests.
   - Rationale: Plugin Eval expects some test signal for Python-heavy packages. A focused release test validates packaged importability and core context-tool behavior without shipping all dev-only regression tests.

4. Optimize skill metadata conservatively.
   - Rationale: descriptions are always-visible trigger metadata. Shortening them should lower trigger cost, but they must still mention the concrete use cases that route to each skill.

5. Use Plugin Eval as a quality gate, not the only gate.
   - Rationale: Plugin Eval is heuristic. The final assessment should include unit tests, preflight, OpenSpec validation, and the before/after Plugin Eval report.

## Risks / Trade-offs

- Splitting modules can break imports if relative paths are mishandled. Mitigation: preserve top-level script imports and add tests for packaged importability.
- Adding release tests increases deferred token count slightly. Mitigation: keep tests compact and behavior-focused.
- Plugin Eval's Python analyzer is heuristic and may still flag complexity in generated or script-style modules. Mitigation: split code enough that the reported hotspot reflects real focused modules, and report any residual heuristic limits explicitly.
- Shortening skill descriptions can reduce routing recall. Mitigation: keep the highest-signal trigger nouns in each description and run Plugin Eval after edits.
