# Goal and Delegation Disposition

Read this file only when a context-health report requires goal repair or a
subagent/reviewer disposition.

## Goal repair

Apply the Goal Suitability Gate before context-health drift appears. Use
`define-goal` to shape a measurable objective with outcome, verification
evidence, scope boundaries, non-goals, success threshold, and stop conditions.
Apply the Goal Quality Gate before creation.

Set the shaped objective in a Codex app, IDE, or CLI composer with
`/goal <objective>`. Use `/goal` to inspect it and `/goal pause`, `/goal resume`,
or `/goal clear` to control it. If `/goal` is unavailable, enable
`features.goals` or run `codex features enable goals`. When the interactive
command cannot run in the current environment, persist the Goal Mode Prompt in
the next checkpoint.

## Delegation disposition

Record every pending recommendation:

```bash
python3 scripts/record_context_health_disposition.py \
  --repo <repo> \
  --recommendation-id <recommendationId> \
  --disposition accepted \
  --note "Accepted for read-only investigation." \
  --json
```

Use `accepted` only when explicit user authorization or an approved delegated
workflow exists and a validated Agent Task Contract will be used. The contract
is scope evidence, not authorization. Use `declined` with a reason when
main-agent execution is safer, `superseded` when another action resolved the
need, and `blocked` when authorization or context is missing. The note is
required.

The generated Agent Task Contract must contain Goal, Scope, Constraints,
Verification, Evidence, and Human Gate. Keep read-only exploration, disjoint
write ownership, or diff-centric review explicit; the main agent owns
verification and durable workflow evidence.
