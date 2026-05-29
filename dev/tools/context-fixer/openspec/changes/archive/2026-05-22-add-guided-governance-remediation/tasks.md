## 1. Remediation Tests

- [x] 1.1 Add failing tests for `remediate plan`.
- [x] 1.2 Add failing tests for `remediate apply` backup behavior.
- [x] 1.3 Add failing tests for unknown operation and unsafe path refusal.
- [x] 1.4 Add failing tests for sensitive-body omission.

## 2. Remediation Implementation

- [x] 2.1 Create `src/context_fixer/remediation.py`.
- [x] 2.2 Implement dry-run plan generation from governance recommendations.
- [x] 2.3 Implement safe apply with operation allowlist and backups.

## 3. CLI and Docs

- [x] 3.1 Add `remediate plan` and `remediate apply`.
- [x] 3.2 Document remediation review and backup workflow.

## 4. Verification

- [x] 4.1 Run targeted remediation tests.
- [x] 4.2 Run full unit tests and py_compile.
