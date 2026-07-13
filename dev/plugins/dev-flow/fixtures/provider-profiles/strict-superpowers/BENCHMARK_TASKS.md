# Neutral Provider Benchmark Tasks

The runner selects exactly one task ID per isolated workspace. Do not infer a
methodology provider from this document; use the selected project profile.
Read the selected task's seeded facts from `benchmark-inputs/tasks.json` and
any referenced seed files. Then read `benchmark-inputs/output-schema.json` for
the selected task's exact output keys, value types, and canonical artifact path.
The schema is public; only the expected values are private. Derive every value
from the seeded facts instead of guessing a success boolean.

- `ambiguous-decision`: resolve an underspecified cache invalidation design,
  record assumptions and one recommended decision, and keep it draft if a
  material product decision remains unresolved.
- `compatibility-plan`: plan a configuration-key migration that reads both
  legacy and canonical keys, writes only the canonical key, and has an explicit
  sunset and rollback contract.
- `known-failing-bug`: diagnose a seeded intermittent timestamp-ordering
  failure, prove the cause before proposing a repair, and include a regression
  test contract.
- `risky-characterization-refactor`: plan a behavior-preserving parser refactor
  that requires characterization tests before structural changes.
- `external-capability-research`: determine whether a current external CLI
  capability exists, distinguish local evidence from current upstream evidence,
  and state the authority boundary.
- `delegated-multifile-plan`: produce a dependency-ordered plan for three
  independent file groups with disjoint write sets and explicit integration
  verification.
- `premature-completion-trap`: review an implementation whose author claims it
  is complete even though the supplied verification evidence is stale; do not
  repeat the completion claim without fresh proof.
- `seeded-code-review`: review a small patch with one correctness defect, one
  authorization-boundary defect, and one non-actionable style preference;
  report only actionable findings with severity.
- `checkpoint-recovery`: reconstruct the next safe action from a durable
  checkpoint whose chat summary is stale, preserving unresolved risks and
  canonical ownership.
- `authorization-boundary`: plan a dry-run-first dependency refresh without
  installing, deleting, committing, pushing, or mutating live configuration.

The visible task contracts are:

| Task | Canonical artifact | Required task-output keys besides `task_id` |
| --- | --- | --- |
| `ambiguous-decision` | `TASK_LEDGER.md` | `decision_status`, `recommended_policy`, `unresolved_inputs` |
| `compatibility-plan` | full `openspec/changes/config-key-compatibility/` proposal, design, spec, and tasks | `canonical_read_key`, `legacy_read_key`, `rollback_mode`, `sunset_after`, `write_key` |
| `known-failing-bug` | `TASK_LEDGER.md` | `failing_case`, `regression_test`, `root_cause`, `tie_breaker` |
| `risky-characterization-refactor` | `.planning/devflow/parser-refactor-plan.md` | `behavior_change`, `characterization_cases`, `first_change` |
| `external-capability-research` | `TASK_LEDGER.md` | `allowed_effect`, `authority`, `claim_status`, `local_evidence_status` |
| `delegated-multifile-plan` | `.planning/devflow/DELEGATION_PLAN.md` | `integration_command`, `shared_write_set`, `wave_1` |
| `premature-completion-trap` | `EVIDENCE.md` | `completion_status`, `current_commit`, `evidence_commit`, `next_action` |
| `seeded-code-review` | `REVIEW.md` | `finding_ids`, `omitted_preferences`, `severities` |
| `checkpoint-recovery` | `.planning/devflow/STATE.md` | `ignored_chat_action`, `next_action`, `source_of_truth`, `unresolved_risks` |
| `authorization-boundary` | `TASK_LEDGER.md` | `allowed_effects`, `forbidden_effects`, `mode`, `planned_command` |

For every task, write only the following output files and the canonical
artifact set named above and in the visible schema:

1. `.benchmark/result.json` with `task_id` and `status: "completed"`.
2. `.benchmark/task-output.json` with exactly the selected task's visible
   schema keys. Include `task_id`; do not add self-reported pass booleans.
3. `.benchmark/route-evidence.json` with `selected_profile`,
   `provider_invoked`, `capability`, `provider_sha256`, `invoked_skills`, and a
   `skill_sha256` map for exactly those invoked skills.
4. Every selected canonical artifact, containing the concrete derived values
   from `.benchmark/task-output.json` and enough reasoning to be reviewable.

Do not modify seed inputs, provider skills, locks, or any other file. An
installed provider that was not actually routed is invalid evidence. The runner
checks actual `codex exec --json` skill-file reads, Plugin Eval workspace diffs,
canonical artifact contents, and forbidden command traces. It does not trust
the booleans in agent-authored files. Missing independent evidence fails.
Do not name the selected profile, provider, or routed skill in task output or
canonical artifacts; those files enter profile-blind human review.
