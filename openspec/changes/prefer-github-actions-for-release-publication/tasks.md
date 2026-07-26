## 1. Plan And Validate

- [x] 1.1 Record the Actions-first release route, authorization boundaries, fallbacks, readback, and rollback behavior.
- [x] 1.2 Strictly validate the change and confirm the implementation write set does not overlap existing user changes.

## 2. Contract Tests

- [x] 2.1 Add RED machine-readable release-route tests for Actions, direct `gh`, and non-release operations.
- [x] 2.2 Add RED public-guidance tests for workflow identity, least privilege, tag preservation, and publication readback.

## 3. Runtime And Guidance

- [x] 3.1 Add Actions-first release route metadata without adding a side-effect ID or changing non-release routing.
- [x] 3.2 Update the Git/GitHub routing reference, project orchestration, verification, root, and generated project guidance.
- [x] 3.3 Run focused tests to GREEN and confirm unrelated working changes remain untouched.

## 4. Verification

- [x] 4.1 Run the complete source-only DevFlow suite, strict change/all OpenSpec validation, workflow validation, and diff hygiene.
- [x] 4.2 Record implementation evidence, release drift, residual risks, and the separate promotion/commit/push/archive gates.
