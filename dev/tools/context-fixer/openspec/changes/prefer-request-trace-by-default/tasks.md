## 1. Trace-First CLI Tests

- [x] 1.1 Add a failing test for `context-fixer --repo <repo>` exiting with request trace guidance and no normal report.
- [x] 1.2 Update existing session-log-only CLI tests to pass `--session-only`.
- [x] 1.3 Add a passing behavior test that `--session-only` produces the normal report and keeps first-run guidance recommendations.
- [x] 1.4 Add a passing behavior test that `--trace` still produces the full trace report without requiring `--session-only`.

## 2. Trace-First CLI Implementation

- [x] 2.1 Add `--session-only` CLI flag and help text.
- [x] 2.2 Add missing-evidence-mode guard before analysis when neither `--trace` nor `--session-only` is supplied.
- [x] 2.3 Reuse claude-tap dependency guidance for the guard output without writing first-run cache state.
- [x] 2.4 Preserve existing fail-on-severity and output rendering behavior for valid evidence modes.

## 3. Documentation and Verification

- [x] 3.1 Update README usage examples and data source explanation for trace-first defaults.
- [x] 3.2 Run focused CLI tests.
- [x] 3.3 Run the full unit suite.
- [x] 3.4 Validate active OpenSpec changes and update task checkboxes.
