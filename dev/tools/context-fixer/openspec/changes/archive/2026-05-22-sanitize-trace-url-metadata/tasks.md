## 1. Regression Test

- [x] 1.1 Add a failing test proving request trace URL query strings and
  fragments are omitted from serialized reports.

## 2. Implementation

- [x] 2.1 Sanitize request trace `request_path` to path-only metadata.
- [x] 2.2 Sanitize upstream and endpoint URL metadata by removing query strings
  and fragments.

## 3. Verification

- [x] 3.1 Run the targeted regression test.
- [x] 3.2 Run full unit tests, py_compile, strict OpenSpec validation, and
  repeat the `app_ai_doctor` trace smoke check.
