## 1. Hook Event Tests

- [x] 1.1 Add failing tests for explicit `--hook-events` ingestion.
- [x] 1.2 Add failing tests for repo scoping and sensitive-body omission.
- [x] 1.3 Add failing tests for malformed-record tolerance.

## 2. Parser Implementation

- [x] 2.1 Create `src/context_fixer/hook_events.py`.
- [x] 2.2 Convert sanitized hook input/output token counts into contributors.
- [x] 2.3 Convert hook records into activity events.

## 3. Analyzer and CLI

- [x] 3.1 Add `hook_events` input to `analyze_context`.
- [x] 3.2 Add `--hook-events` and `--include-external-hook-events` CLI flags.
- [x] 3.3 Render hook event findings without raw bodies.

## 4. Documentation

- [x] 4.1 Document collector and ingestion as separate workflows.
- [x] 4.2 Update skill usage examples.

## 5. Verification

- [x] 5.1 Run targeted hook event tests.
- [x] 5.2 Run full unit tests and py_compile.
