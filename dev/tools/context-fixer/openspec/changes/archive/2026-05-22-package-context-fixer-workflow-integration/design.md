## Context

The complete product spans CLI, managed external tools, SQLite history, Web
dashboard, and remediation. The bundled skill should provide the short path for
Codex users, while README provides complete reference workflows.

## Goals / Non-Goals

Goals:

- Document official one-command collection profiles.
- Document Web dashboard and history usage.
- Document remediation dry-run/apply workflow.
- Document manual imports as advanced/debug flows.
- Add tests that verify command examples are present.

Non-goals:

- Do not duplicate every implementation detail.
- Do not document Tauri or live proxy behavior as product requirements.

## Decisions

1. **README as complete reference.** It covers all commands and privacy notes.
2. **Skill as operational quickstart.** It gives concise commands and
   interpretation guidance.
3. **Docs tests.** Unit tests assert important command examples remain present.

## Risks / Trade-offs

- Docs can become noisy. Mitigation: split reference sections and keep skill
  concise.
- Command examples can drift. Mitigation: docs tests cover the core matrix.

## Migration Plan

1. Update README.
2. Update skill guide.
3. Add docs tests.
4. Run verification.
