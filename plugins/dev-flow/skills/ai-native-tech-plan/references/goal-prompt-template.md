# Goal and Continue Prompts

## Goal Mode Prompt

```text
/goal

Goal: fully implement <task-name> Target State, not a prototype or partial implementation.

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
