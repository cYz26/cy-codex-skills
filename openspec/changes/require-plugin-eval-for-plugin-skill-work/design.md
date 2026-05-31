## Context

This repository already has Plugin Eval installed and used in earlier DevFlow
quality work, but its use is not a durable repository rule. Skill and plugin
changes currently rely on tests and manual review, which do not consistently
catch skill trigger quality, context budget, or plugin packaging evaluation
issues.

## Goals / Non-Goals

**Goals:**

- Make Plugin Eval a required verification step for future plugin and skill
  creation or updates.
- Keep the rule practical: evaluate the smallest changed target that represents
  the work.
- Require optimization decisions to be explicit, even when Plugin Eval returns a
  clean score.
- Preserve normal tests, OpenSpec validation, and preflight checks as separate
  gates.

**Non-Goals:**

- Add Plugin Eval as a runtime dependency of DevFlow.
- Block unrelated code changes that do not create or update plugins or skills.
- Require benchmark execution for every small skill edit; static analysis is the
  minimum gate, benchmark/measurement is used when findings or risk justify it.

## Decisions

- **Rule location:** Add the requirement to root `AGENTS.md` and DevFlow
  `AGENTS.md` templates. This covers the current repo and future generated
  workflow instructions.
- **Command form:** Document both `plugin-eval analyze <path>` and the local
  fallback `node /Users/cy/.codex/plugins/cache/openai-curated/plugin-eval/.../scripts/plugin-eval.js`
  style because `plugin-eval` may not be on PATH.
- **Evidence expectation:** Verification records should include the evaluated
  target, score/grade, key findings, and what was changed or deliberately left
  unchanged.
- **Testing:** Add tests that fail if the Plugin Eval rule disappears from
  repository instructions or DevFlow templates.

## Risks / Trade-offs

- **Plugin Eval binary may not be on PATH** -> Document the Node script fallback
  and report when the command cannot be found.
- **Extra gate can slow small edits** -> Limit the minimum requirement to static
  `analyze`; benchmark or measurement is optional unless the evaluation points
  there.
- **Agents may run Plugin Eval but ignore findings** -> Require optimization
  decisions and residual risks in verification evidence.
