# Context Fixer

## What This Is

Context Fixer is a local-first, CLI-first context auditor for Codex sessions,
request traces, compaction timing, and AI project configuration. It helps a
developer understand context pressure, likely contributors, workflow readiness,
and safe next actions without exposing prompt or conversation bodies.

## Core Value

Make Codex context usage inspectable and actionable while keeping sensitive
session content local and sanitized.

## Requirements

### Validated

(None yet - current baseline is being recorded.)

### Active

- [ ] Diagnose local Codex context pressure from session telemetry.
- [ ] Attribute likely contributors from sessions, traces, project files, and
  Codex configuration without printing sensitive bodies.
- [ ] Render text, JSON, and self-contained HTML reports.
- [ ] Keep project workflow state, OpenSpec artifacts, checkpoints, and
  verification evidence durable before archive or phase completion.

### Out of Scope

- Proxy or tap capture - request traces are explicit opt-in file inputs.
- Mutating global Codex configuration - cleanup requires explicit user approval.
- Franchise-specific naming or protected likenesses - Context Fixer branding is
  original.

## Context

The project is brownfield inside the `cy-codex-skills` repository. The current
implementation is a standard-library Python CLI under `src/context_fixer`, with
`src/codex_context_lens` retained as a compatibility import/console alias.
Project governance is Codex-first: GSD owns roadmap/phase tracking, OpenSpec owns
behavior-level artifacts, and verification evidence must be recorded before
archive or ship decisions.

## Constraints

- **Runtime**: Python 3.11 standard library - keep the tool easy to run locally.
- **Privacy**: Reports must omit prompt, message, tool argument, and tool output
  bodies - only paths, labels, sizes, estimates, and sanitized inventory belong
  in output.
- **Compatibility**: Preserve the `codex-context-lens` compatibility path unless
  a future approved change removes it.
- **Workflow**: User-visible behavior changes require OpenSpec planning before
  implementation.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use Context Fixer as the English product name | Keeps user-facing naming clear while preserving the Chinese working idea as background | Pending |
| Keep request trace parsing opt-in | Avoids hidden capture and keeps privacy boundaries explicit | Pending |
| Keep the CLI read-only by default | Context audit should not mutate project or global Codex state unexpectedly | Pending |

---
*Last updated: 2026-05-18 after workflow status continuation.*
