# Release Plugin Eval Evidence

## Target and Command

Target: generated release `plugins/dev-flow`.

The standalone `plugin-eval` executable was not present on `PATH`, so the same
installed Plugin Eval 0.1.2 runtime was invoked through its checked-in Node
entrypoint:

```bash
node /Users/cY/.codex/plugins/cache/openai-curated-remote/plugin-eval/0.1.2/scripts/plugin-eval.js \
  start plugins/dev-flow --request 'Evaluate this plugin.' --format markdown

node /Users/cY/.codex/plugins/cache/openai-curated-remote/plugin-eval/0.1.2/scripts/plugin-eval.js \
  analyze plugins/dev-flow --format markdown
```

Both commands exited 0. The start command routed to the plugin evaluation
workflow and the analysis command inspected the generated release counterpart,
not the development path.

## Result

- Score: 86/100
- Grade: B
- Risk: medium
- Checks: 0 fail, 3 warn, 2 info
- Active budget: 15,173 tokens
- Trigger budget: 388 tokens
- Invoke budget: 14,785 tokens
- Deferred budget: 49,056 tokens
- Observed usage: not supplied

All 16 packaged Skills remained within the evaluator's good line-count and
frontmatter ranges. The three warnings were the existing plugin-wide static
budget classes:

- `trigger_cost_tokens-budget-high`
- `invoke_cost_tokens-budget-high`
- `deferred_cost_tokens-budget-high`

The informational coverage observation reports that no evaluator-native
coverage artifact was supplied; repository verification instead executed all
499 DevFlow tests plus focused release and runtime gates.

## Disposition

No Plugin Eval failure or new Project Refresh behavior defect was found. The
three static warnings are already registered as `DF-IFL-001` in
`TASK_LEDGER.md` with `DEFER_AND_CONTINUE`: reducing the 16-Skill plugin-wide
budget requires measured route usage and a separate architecture/write-set
decision, while this change's modified Skills remain individually within the
good range and all behavioral, release, and runtime checks pass. Residual risk
is avoidable prompt cost on some routes. The follow-up remains a separately
approved measurement and deduplication change; this evidence does not authorize
that work.

## Task 9.7 Corrective Rerun

The same release target was analyzed again after the 2026-08-07 systemic
repair and generated-release refresh:

```bash
node /Users/cY/.codex/plugins/cache/openai-curated-remote/plugin-eval/0.1.2/scripts/plugin-eval.js \
  analyze plugins/dev-flow --format markdown
```

The command exited 0 with score 86/100, grade B, medium risk, 0 failures,
3 warnings, and 2 informational observations. Current static budgets are
15,190 active tokens, 388 trigger tokens, 14,802 invoke tokens, and 49,422
deferred tokens. The three warning classes and their `DF-IFL-001` disposition
are unchanged; no new Project Refresh defect or actionable warning was found.
Repository verification for this snapshot is 504/504 complete DevFlow tests,
including the release-dependent modules.
