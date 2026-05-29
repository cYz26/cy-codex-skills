## 1. Tests

- [x] 1.1 Add failing tests for project-local tool discovery.
- [x] 1.2 Add failing tests for claude-tap supplied trace reuse.
- [x] 1.3 Add failing tests that claude-tap probe output is not stored as a
  trace artifact.

## 2. Implementation

- [x] 2.1 Add project-local executable discovery.
- [x] 2.2 Pass supplied trace artifacts into the managed runner.
- [x] 2.3 Replace unsupported claude-tap invocation with reuse/probe behavior.

## 3. Real Project Setup

- [x] 3.1 Install or expose usable project-local tools for `app_ai_doctor`
  where available.
- [x] 3.2 Re-run full collect and tool doctor against `app_ai_doctor`.

## 4. Verification

- [x] 4.1 Run targeted tests.
- [x] 4.2 Run full unit tests and py_compile.
- [x] 4.3 Run strict OpenSpec validation.
