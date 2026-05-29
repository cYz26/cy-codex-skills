## Context

The current budget model exposes the evidence needed for governance, but that
evidence is spread across `budget`, `activity`, `config_audit`, `diagnosis`, and
`data_sources`. This change adds a dedicated advisory layer that translates
those sections into structured, user-facing guidance.

## Goals / Non-Goals

Goals:

- Add `report["governance"]` with stable recommendation groups.
- Cover profile, AGENTS, Skills, MCP, hooks, and command-output governance.
- Render the recommendations across existing report formats.
- Keep all recommendations traceable to sanitized evidence.

Non-goals:

- Do not modify files or apply recommendations.
- Do not introduce external dependencies.
- Do not perform live MCP schema calls or request capture.

## Decisions

1. **New focused module.** `governance.py` owns the governance model so
   `analyzer.py` remains an orchestrator.
2. **Evidence-first records.** Every recommendation includes `surface`,
   `priority`, `title`, `reason`, `action`, and `evidence`.
3. **Advisory snippets only.** TOML or command examples may be rendered as
   suggested snippets, but the system marks them as not applied.
4. **Existing recommendations remain.** `compression.recommendations` and
   `budget.recommendations` remain compatible; governance is additive.

## Data Model

`report["governance"]`:

```json
{
  "status": "advisory",
  "mutates_files": false,
  "recommendations": [],
  "profile_suggestions": [],
  "agents_suggestions": [],
  "skill_suggestions": [],
  "mcp_suggestions": [],
  "hook_suggestions": [],
  "command_output_suggestions": []
}
```

## Risks / Trade-offs

- Recommendations can be too generic if evidence is weak. Mitigation: include
  confidence and source evidence, and avoid pretending estimated tokens are
  exact.
- Too many suggestions can overwhelm users. Mitigation: cap rendered lists and
  sort by priority and estimated token impact.

## Migration Plan

1. Add failing tests for `report["governance"]`.
2. Implement `governance.py` and wire it into `analyze_context`.
3. Render governance sections.
4. Update docs and run full verification.
