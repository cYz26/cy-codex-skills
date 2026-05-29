## 1. Store Tests

- [x] 1.1 Add failing tests for `audit --save --store`.
- [x] 1.2 Add failing tests for `history` listing and `history show`.
- [x] 1.3 Add failing tests proving stored JSON omits sensitive bodies.

## 2. Store Implementation

- [x] 2.1 Create `src/context_fixer/store.py`.
- [x] 2.2 Implement schema initialization and version metadata.
- [x] 2.3 Implement save, list, and load helpers.

## 3. CLI Integration

- [x] 3.1 Add `--save` and `--store` to relevant commands.
- [x] 3.2 Add `history` and `history show` commands.
- [x] 3.3 Wire managed collection to save when requested.

## 4. Documentation

- [x] 4.1 Document local store behavior and privacy boundary.
- [x] 4.2 Update skill examples.

## 5. Verification

- [x] 5.1 Run targeted store tests.
- [x] 5.2 Run full unit tests and py_compile.
