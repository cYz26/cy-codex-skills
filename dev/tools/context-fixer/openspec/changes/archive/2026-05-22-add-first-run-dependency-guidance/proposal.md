## Why

Codex request trace analysis depends on an external capture tool such as
claude-tap, but first-time Context Fixer users may not know that setup path.
The CLI should surface optional dependency guidance at the right moment without
turning claude-tap into a required dependency.

## What Changes

- Add first-run dependency guidance for each audited repository when the user
  runs the CLI without a request trace.
- Detect whether `claude-tap` is available on `PATH` and tailor the guidance to
  either install or run it for Codex capture.
- Store the "guidance already shown" marker in a user cache directory, not in
  the audited project.
- Preserve analyzer behavior, JSON/HTML/text sanitization, and normal operation
  when `claude-tap` is absent.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `current-system`: CLI reporting gains optional first-run dependency guidance
  for Codex request trace capture while preserving local-first project analysis.

## Impact

- Affected code: CLI orchestration, report recommendations, a small cache-backed
  onboarding helper, and tests.
- Affected behavior: first CLI run for a repository can include an additional
  recommendation. Subsequent runs suppress it after local cache state is written.
- Dependencies: no production dependency on claude-tap.
- Persistence: user cache only; the audited repository is not modified unless the
  user explicitly asks for an output file such as `--html`.
