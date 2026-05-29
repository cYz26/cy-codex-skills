## Context

Context Fixer has two evidence modes: request traces supplied through `--trace`
and lower-confidence session JSONL analysis. The CLI previously ran session-only
analysis by default and used recommendations to suggest optional trace setup.
The new desired behavior is to make request trace evidence the default expected
path.

## Goals / Non-Goals

**Goals:**

- Require either `--trace` or `--session-only` for CLI report generation.
- Provide actionable Codex claude-tap guidance when the user omits both.
- Support automation by making the lower-confidence path explicit and
  non-interactive.
- Avoid changing `analyze_context()` and renderers beyond the report data they
  already handle.

**Non-Goals:**

- Do not run claude-tap automatically.
- Do not ask an interactive yes/no prompt.
- Do not remove session log analysis.
- Do not change library API behavior.

## Decisions

1. **Use `--session-only` as explicit confirmation.**
   - Rationale: it is scriptable and records the user's intent in command
     history. An interactive prompt would be hostile to CI and tool wrappers.

2. **Exit before analysis when evidence mode is missing.**
   - Rationale: the default command should not produce a report that looks
     complete while lacking request trace evidence. The guidance output is the
     result in this state.

3. **Reuse onboarding guidance construction.**
   - Rationale: existing guidance already detects claude-tap and has install or
     capture commands. The new gate can use the same wording without marking
     per-project first-run state.

## Risks / Trade-offs

- **Risk: existing scripts break.** Mitigation: error text tells users to add
  `--session-only` or `--trace`.
- **Risk: users expect one-shot session-only reports.** Mitigation: README and
  CLI help document `--session-only`.
- **Risk: fail-on-severity has overlapping exit code semantics.** Mitigation:
  use a distinct exit code for missing evidence mode.
