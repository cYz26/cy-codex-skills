## 1. OpenSpec And Test Setup

- [x] 1.1 Create OpenSpec artifacts for FeishuOps dynamic domain guidance.
- [x] 1.2 Add failing tests for action-to-domain guidance resolution and missing-skill fallback.

## 2. Resolver Implementation

- [x] 2.1 Add domain/action mapping and guidance-source resolution to `lark_feishu_ops_agent_context.py`.
- [x] 2.2 Include `guidance_sources` in normalized requests and fresh-subagent dispatch reports.
- [x] 2.3 Normalize FeishuOps result `guidance_sources` for context snapshots.

## 3. Documentation And Runtime Contract

- [x] 3.1 Update `SKILL.md` to describe FeishuOps domain guidance injection without global activation.
- [x] 3.2 Update `feishuops-protocol.md` and runtime prompt input/output contracts.
- [x] 3.3 Update README guidance and examples.

## 4. Verification And Release Prep

- [x] 4.1 Run focused Lark Feishu Ops tests.
- [x] 4.2 Run doctor, sync/cache parity, OpenSpec validation, and Plugin Eval.
- [x] 4.3 Refresh installed plugin cache if source/cache drift remains and verify parity.
- [x] 4.4 Record verification evidence and update workflow state.
