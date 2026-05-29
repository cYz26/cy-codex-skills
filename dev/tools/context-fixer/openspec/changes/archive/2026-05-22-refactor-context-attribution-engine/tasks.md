## 1. Budget Model Tests

- [x] 1.1 Add failing tests that require `report["budget"]` with baseline, session growth, turn deltas, request composition, top offenders, and recommendation evidence.
- [x] 1.2 Add failing tests for stable source categories covering AGENTS, skill metadata, MCP inventory, hooks/config, user/assistant history, tool arguments, tool output, bash output, patch/diff, file content, web result, and request trace contributors.

## 2. Budget Aggregation

- [x] 2.1 Create a focused budget aggregation module that maps sanitized contributors and timeline/activity evidence into Context Lens budget sections.
- [x] 2.2 Wire the budget module into `analyze_context` while preserving existing report keys and compatibility behavior.
- [x] 2.3 Generate top offenders and budget recommendation evidence from the new budget model.

## 3. Parser Classification

- [x] 3.1 Refine static-source classification for global/project/nested AGENTS, skill metadata, Codex config, MCP inventory, hooks, and workflow context.
- [x] 3.2 Refine session JSONL classification for user/assistant history, developer instructions, summaries, tool arguments, bash output, file content, patch/diff content, web/search output, MCP output, and generic tool results.
- [x] 3.3 Refine request trace composition for instructions/system-like content, messages by role, tool definitions, tool results, exact usage, and request metadata.

## 4. Reporting and Documentation

- [x] 4.1 Render budget sections in text output without exposing sensitive bodies.
- [x] 4.2 Render budget sections in the HTML dashboard without exposing sensitive bodies.
- [x] 4.3 Update README usage/report-shape documentation for the budget model while preserving Context Fixer naming and `codex-context-lens` compatibility notes.

## 5. Verification and Workflow Records

- [x] 5.1 Run targeted red/green tests for each implemented task and the full unittest suite.
- [x] 5.2 Update `.planning/STATE.md` and write a checkpoint with changed-files summary, verification evidence, unresolved risks, and next action.
