## 1. Managed Tool Tests

- [x] 1.1 Add failing tests for the managed tool registry.
- [x] 1.2 Add failing tests for `collect --profile full` with mocked tool
  execution.
- [x] 1.3 Add failing tests for `tools list` and `tools doctor`.
- [x] 1.4 Add failing tests for sensitive output omission.

## 2. Tool Registry and Runner

- [x] 2.1 Create `src/context_fixer/tools.py`.
- [x] 2.2 Implement `ManagedTool` and `ManagedToolRunner`.
- [x] 2.3 Implement run directories, timeouts, status records, and process
  cleanup.

## 3. Artifact Adapters

- [x] 3.1 Create `src/context_fixer/adapters.py`.
- [x] 3.2 Implement ccusage JSON parsing.
- [x] 3.3 Implement OTel JSONL parsing.
- [x] 3.4 Preserve existing trace import behavior.

## 4. CLI and Analyzer Integration

- [x] 4.1 Add `collect` command with profiles.
- [x] 4.2 Add `tools list` and `tools doctor`.
- [x] 4.3 Add manual `usage import` and `otel import`.
- [x] 4.4 Add `external_tools` and `usage` sections to reports.

## 5. Documentation

- [x] 5.1 Document managed collection profiles.
- [x] 5.2 Document external tool installation/availability expectations.
- [x] 5.3 Document manual imports as advanced/debug flows.

## 6. Verification

- [x] 6.1 Run targeted managed tool tests.
- [x] 6.2 Run full unit tests and py_compile.
