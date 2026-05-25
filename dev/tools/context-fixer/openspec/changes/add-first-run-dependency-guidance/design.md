## Context

Context Fixer now imports Codex claude-tap traces through `--trace`, but the
baseline command still works without any external capture tool. The guidance
should help first-time users discover the optional setup path without adding
project mutations or a hard dependency.

## Goals / Non-Goals

**Goals:**

- Show Codex request trace setup guidance once per repository in normal CLI
  output when no trace is supplied.
- Detect whether `claude-tap` exists on `PATH` and adapt the message.
- Persist "shown" state in a user-local cache keyed by repository path.
- Make the feature testable with an override cache directory.

**Non-Goals:**

- Do not install claude-tap automatically.
- Do not write onboarding markers into the target repository.
- Do not show the prompt from `analyze_context()` API calls.
- Do not introduce interactive prompts or blocking confirmation.

## Decisions

1. **CLI-level onboarding only.**
   - Rationale: `analyze_context()` remains a pure-ish analysis entry point, and
     only the user-facing CLI needs first-run guidance.
   - Alternative considered: add guidance inside the analyzer. Rejected because
     it would make programmatic report generation stateful.

2. **User cache persistence.**
   - Rationale: "first use for a project" requires durable state, but the
     project spec says analysis should not mutate project files. A user cache
     preserves the read-only project boundary.
   - Cache location: `CONTEXT_FIXER_CACHE_HOME` when set, otherwise
     `$XDG_CACHE_HOME/context-fixer` or `~/.cache/context-fixer`.

3. **Recommendation-based presentation.**
   - Rationale: text and HTML renderers already show recommendations, and JSON
     reports already include them. The onboarding hint can fit the existing
     report shape without a new UI surface.

## Risks / Trade-offs

- **Risk: cache path reveals local repo paths.** Mitigation: store repository
  hashes as keys and keep paths only as local troubleshooting metadata.
- **Risk: users miss the guidance after first run.** Mitigation: README keeps
  explicit claude-tap setup examples.
- **Risk: environments without `uv`.** Mitigation: guidance labels claude-tap as
  optional and gives the capture command separately from installation.
