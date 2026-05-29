## 1. CLI and Markdown Tests

- [x] 1.1 Add failing tests for `audit`, `report --format markdown`, `recommend`, `doctor`, `sessions`, `inspect`, and `trace import` command behavior.
- [x] 1.2 Add failing tests that Markdown output includes budget/top-offender sections and omits sensitive bodies.

## 2. CLI Implementation

- [x] 2.1 Add Markdown rendering from sanitized report data.
- [x] 2.2 Refactor `cli.py` to support subcommands while preserving legacy flags.
- [x] 2.3 Implement `sessions`, `inspect`, `recommend`, `doctor`, and `trace import` command outputs.

## 3. Hook Collector

- [x] 3.1 Add failing tests for `context-fixer-hook post-tool-use` sanitized JSONL recording.
- [x] 3.2 Implement the hook collector module and console script.

## 4. Skill and Documentation

- [x] 4.1 Update `skills/context-fixer/SKILL.md` to use the new command workflows.
- [x] 4.2 Update README with the new command surface, Markdown output, and hook collector setup.

## 5. Verification and Workflow Records

- [x] 5.1 Run targeted red/green tests and the full unittest suite.
- [x] 5.2 Run CLI smoke checks for representative commands.
- [x] 5.3 Update `.planning/STATE.md` and write a verification checkpoint.
