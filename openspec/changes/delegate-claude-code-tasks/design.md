## Context

DevFlow already owns Codex-first planning, OpenSpec artifacts, verification records, checkpoint policy, and project-local skills. The repository has no existing DevFlow capability for delegating a Codex task to Claude Code; direct shell calls would bypass consistent safety and evidence handling.

Capability evidence collected on 2026-05-31:

- Authoritative/current CLI evidence: `/Users/cy/.local/bin/claude` exists and reports `2.1.158 (Claude Code)`.
- `claude --help` confirms non-interactive execution through `-p/--print`, structured output through `--output-format json|stream-json`, permission modes including `plan` and `acceptEdits`, tool controls through `--tools` and `--allowedTools`, additional directory access through `--add-dir`, and budget limiting through `--max-budget-usd`.
- `claude agents --help` confirms a background-agent UI exists, but it is TTY/session oriented and is not the smallest stable contract for Codex automation.
- Local scan: DevFlow scripts, hooks, skills, and tests do not currently define a Claude Code delegation wrapper.
- Runtime probe: `claude -p --output-format=json --max-budget-usd 0.01` returned a JSON `result` object with `subtype: error_max_budget_usd`, `is_error: true`, `session_id`, cost, usage, and errors. The wrapper must therefore normalize both success and error JSON, not assume nonzero process status is the only failure signal.

## Goals / Non-Goals

**Goals:**

- Give Codex a standard DevFlow entrypoint for delegating a bounded task to Claude Code.
- Keep plan-only delegation as the default so Claude can analyze or propose without editing.
- Require explicit apply mode for edit-capable delegation.
- Prevent accidental edits in dirty worktrees unless the caller explicitly opts in.
- Normalize Claude Code output into stable JSON for Codex and tests.
- Record lightweight run metadata under `.dev-flow/claude-code/` without committing runtime logs.
- Add a DevFlow skill that tells Codex when delegation is appropriate and how it fits with OpenSpec, TDD, review, and verification gates.

**Non-Goals:**

- Do not replace Codex execution, OpenSpec apply, Superpowers TDD, or DevFlow verification gates.
- Do not add Anthropic SDK or other production dependencies.
- Do not automate the interactive `claude agents` TTY UI in this change.
- Do not enable bypass-permissions mode or broad destructive commands by default.
- Do not guarantee Claude Code is installed; report it as an optional runtime capability.

## Decisions

### Decision 1: Use a Python wrapper around `claude -p`

The implementation will add a script facade such as `scripts/claude_code_delegate.py` backed by a focused module such as `workflow_claude_delegate.py`. This matches existing DevFlow script patterns and is testable with standard-library `unittest` and subprocess fakes.

Alternatives considered:

- Direct instructions in a skill only: too easy for future Codex runs to invoke Claude inconsistently.
- MCP/tool integration: broader integration surface than needed for a local CLI that already supports JSON output.
- Claude `agents` UI: useful for humans, but less deterministic for Codex automation than `claude -p`.

### Decision 2: Default to plan-only delegation

The wrapper default will run Claude Code in plan mode. Apply mode must be requested explicitly with an argument such as `--apply`. In apply mode the wrapper will reject dirty Git state unless `--allow-dirty` is present.

Alternatives considered:

- Always allow edits: unsafe in Codex sessions with existing user changes.
- Always require a clean worktree for all modes: too restrictive for read-only analysis and review.
- Automatically create a worktree: useful later, but this change should first establish a deterministic delegation contract.

### Decision 3: Normalize output and metadata

The wrapper will emit one JSON object with stable keys such as `ok`, `mode`, `claudePath`, `claudeVersion`, `command`, `exitCode`, `resultType`, `resultSubtype`, `isError`, `sessionId`, `costUsd`, `text`, `errors`, and `runLog`. If Claude emits invalid JSON, the wrapper will return a structured failure with captured stderr and a bounded stdout preview.

Runtime metadata will be written under `.dev-flow/claude-code/runs/` by default. The metadata should avoid storing the full task prompt unless an explicit `--record-prompt` option is added in the implementation.

Alternatives considered:

- Pass Claude stdout through unchanged: fragile for Codex and tests.
- Store full transcripts by default: useful for debugging, but risky for private task text.

### Decision 4: Keep Codex responsible for verification

Claude Code delegation is a sub-task execution aid. Codex remains responsible for inspecting diffs, running tests, recording verification evidence, and updating OpenSpec tasks and workflow state.

Alternatives considered:

- Let Claude run verification and mark work complete: conflicts with DevFlow's archive and verification gates.
- Use delegation only for review: safer, but does not satisfy the requested execution path.

## Risks / Trade-offs

- Claude Code may be missing or unauthenticated -> The wrapper returns a structured capability failure and implementation tests cover the missing executable path.
- Claude Code output schema may drift -> The wrapper preserves raw subtype/type fields and handles non-JSON output defensively.
- Apply mode may conflict with user changes -> Dirty-worktree blocking is the default, with explicit override required.
- External model cost can exceed expectations -> The wrapper supports a required or default `--max-budget-usd` value and surfaces cost fields when Claude provides them.
- Claude may make incorrect edits -> Codex must review the diff and run verification before claiming completion.

## Migration Plan

1. Add tests for command construction, missing executable handling, dirty-worktree blocking, JSON success/error normalization, and non-JSON failure normalization.
2. Add the wrapper module and CLI script.
3. Add the `claude-code-delegate` skill and README usage.
4. Sync development and release plugin copies.
5. Run focused unit tests, release smoke tests, `openspec validate --all --strict`, and workflow validation.

Rollback is file-level: remove the wrapper script/module, skill, docs, tests, and this OpenSpec change if validation cannot be made reliable within scope.

## Open Questions

- Default apply-mode permission should start as `acceptEdits`; future work can add isolated worktree execution after this contract is validated.
