# Goal and Continue Prompts

## Goal Mode Prompt

```text
/goal

Goal: fully implement <task-name> Target State, not a prototype or partial implementation.

Define-goal handoff:
- Apply the Goal Suitability Gate before context-health drift appears.
- Use a goal for long-running, multi-slice, migration, release, broad-refactor,
  cross-context, subagent/delegation, or high definition-of-done drift risk.
- Use `define-goal` to create or refine this goal before goal-backed execution.
- Let `define-goal` check the active goal before creating a new goal.
- Include verification evidence, scope boundaries, non-goals, and stop conditions.
- Apply the Goal Quality Gate before goal creation: the candidate objective must
  name outcome, verification evidence, scope boundaries, non-goals, success
  threshold, and stop conditions.

Goal Slash Command:
- After `define-goal` shapes the objective, set it with `/goal <objective>`.
- Use `/goal` to view the active goal.
- Use `/goal pause`, `/goal resume`, or `/goal clear` to control the active goal.
- If `/goal` is unavailable, enable `features.goals` or run `codex features enable goals`.
- Do not use a top-level CLI `goal` subcommand; Goal Mode is an interactive slash command.

Rules:
- Read and maintain <ledger-file> first.
- Start from the next unfinished Capability Slice.
- Run the slice validation command before marking it done.
- Do not move required behavior into future work.
- Record blockers with impact, options, recommended decision, and unblock condition.
- Stop only after the Completion Contract and Acceptance Criteria are satisfied.

Completion criteria:
- <criterion 1>
- <criterion 2>
- <criterion 3>

Validation evidence:
- <command 1>
- <command 2>
- <manual check if needed>

Stop conditions:
- Stop when the Completion Contract and Acceptance Criteria are satisfied.
- Stop early if the active goal conflicts with repo state or validation evidence.
```

## Continue Prompt

```text
Continue the task defined in @<ledger-file>.

First:
1. Read Target State.
2. Read Completion Contract.
3. Read Capability Slices.
4. Confirm done, todo, and blocked items.
5. Continue from the next unfinished slice.

Execution rules:
- Do not replan into a prototype or partial delivery.
- Run validation for each slice.
- Update the ledger only after validation passes or a blocker is recorded.
- Fix failed validation before starting the next slice.
- Finish only after all acceptance criteria are complete.
```
