## Why

The Context Fixer analysis engine now exposes the Codex Context Lens budget
model, but the requirements and technical solution also describe user-facing
interfaces and workflow integrations that are not fully implemented yet. The
current CLI still has a single legacy flag surface, no first-class Markdown
report mode, no session listing/inspection commands, no offline hook collector,
and the bundled skill still documents only the old invocation pattern.

This change completes the practical Python-route implementation of the supplied
documents without switching to TypeScript, adding a database, or enabling live
proxy capture.

## What Changes

- Add document-aligned CLI commands while preserving existing flags:
  `audit`, `sessions`, `inspect`, `report`, `recommend`, `doctor`, and
  `trace import`.
- Add Markdown report rendering and CLI selection through `--format markdown`
  and compatibility flags where appropriate.
- Add a local-first hook collector entry point that records sanitized
  PostToolUse-style audit events to user cache JSONL without changing Codex
  behavior.
- Update the bundled Context Fixer skill to use the new command surface.
- Update README and workflow records to describe the completed interface layer.
- Keep reports sanitized and local; do not upload traces or mutate user Codex
  configuration.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `current-system`: add command-level and integration behavior required by the
  Codex Context Lens documents while preserving the existing Python package and
  compatibility CLI behavior.

## Impact

- Affected code: `src/context_fixer/cli.py`, `src/context_fixer/render.py`,
  `src/context_fixer/session.py`, new hook/support modules as needed, and
  `pyproject.toml`.
- Affected docs/integration: `README.md`, `skills/context-fixer/SKILL.md`,
  OpenSpec artifacts, planning/checkpoint files.
- Public CLI: additive. Existing legacy `context-fixer --repo ...` flags remain
  supported.
- Dependencies: no new production dependency planned.
- Security/privacy: hook records only sanitized metadata and size/hash evidence;
  it does not persist prompt, command output, or trace payload bodies.
