## 1. First-Run Guidance Tests

- [x] 1.1 Add a failing CLI test showing missing claude-tap guidance on first run without `--trace`.
- [x] 1.2 Add a failing CLI test showing guidance is suppressed on the second run for the same repository.
- [x] 1.3 Add a failing CLI test showing installed claude-tap guidance uses the capture command and trace-supplied runs suppress onboarding.

## 2. First-Run Guidance Implementation

- [x] 2.1 Add a cache-backed onboarding helper keyed by repository path.
- [x] 2.2 Add optional claude-tap detection through `PATH`.
- [x] 2.3 Add onboarding recommendations to CLI-generated reports without changing `analyze_context()` behavior.
- [x] 2.4 Ensure first-run state is written outside the audited repository.

## 3. Documentation and Verification

- [x] 3.1 Update README with first-run dependency guidance behavior and cache boundary.
- [x] 3.2 Run focused onboarding tests.
- [x] 3.3 Run the full unit suite.
- [x] 3.4 Validate the OpenSpec change and update task checkboxes.
