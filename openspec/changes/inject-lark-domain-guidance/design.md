## Context

The plugin already uses one main-agent skill, direct `lark-cli` for bounded reads, and FeishuOps for complex, side-effectful, cross-domain, or explicitly delegated work. The missing piece is a concrete parent-side mechanism that resolves domain guidance for a FeishuOps request and records what can be injected into the subagent.

Current local evidence also shows that official `lark-*` skills are not globally active for Codex. That is intentional for main-agent context pressure, but it means FeishuOps needs a bounded, auditable way to find relevant guidance or fall back to `lark-cli` help/schema.

## Goals / Non-Goals

**Goals:**

- Resolve action-specific Lark domain guidance before spawning FeishuOps.
- Prefer existing official `lark-*` `SKILL.md` files when available.
- Fall back to focused `lark-cli <domain> --help`, registered schema, or raw OpenAPI guidance when a skill is unavailable.
- Include guidance metadata in prepared handoff requests and expected outputs.
- Keep behavior testable without spawning real subagents.

**Non-Goals:**

- Do not globally register or activate all official `lark-*` skills.
- Do not add a production dependency or require network access.
- Do not make FeishuOps decide product or technical judgments.
- Do not install official skills automatically.

## Decisions

1. **Resolver lives in `lark_feishu_ops_agent_context.py`.**
   - Rationale: this script already prepares parent-side dispatch decisions and handoff context.
   - Alternative: add a new script. Rejected because guidance belongs with dispatch preparation and would duplicate request normalization.

2. **Guidance sources are metadata, not execution.**
   - Rationale: the platform operation still runs through `lark-cli`; skills only improve command choice, safety, and domain-specific evidence handling.
   - Alternative: treat skills as callable execution tools. Rejected because Codex skills are instructions, and runtime registration is not guaranteed per subagent.

3. **Use a deterministic action-to-domain map plus explicit fallback.**
   - Rationale: tests can validate the handoff for common actions, and unsupported domains get honest blockers or OpenAPI fallback.
   - Alternative: ask the subagent to discover all domains every time. Rejected because that wastes context and makes behavior less predictable.

4. **Do not require installed official skills for success.**
   - Rationale: local environments may not have official `lark-*` skill files. `lark-cli` help/schema remains the authoritative available command surface.
   - Alternative: block all FeishuOps work when skills are missing. Rejected because that would regress current CLI-based behavior.

## Risks / Trade-offs

- **Risk: guidance inventory becomes stale** -> Mitigation: resolver returns source status and tests cover common actions and missing-skill fallback.
- **Risk: subagent mistakes guidance metadata for authorization to broaden scope** -> Mitigation: protocol keeps one-operation boundaries and bounded expansion rules.
- **Risk: official skill paths vary across environments** -> Mitigation: resolver searches configured/local candidate roots and records missing sources instead of assuming.
- **Risk: Plugin Eval still reports budget warnings** -> Mitigation: keep main skill concise and put details in references/runtime prompt.
