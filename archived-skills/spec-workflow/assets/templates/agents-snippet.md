## Spec workflow

- Use `$spec-workflow` for non-trivial features, refactors, integrations, and bug fixes before broad implementation.
- Treat `AGENTS.md` as the standing repository constitution; do not create a parallel constitution file.
- Prefer spec folders under `specs/<NNN>-<slug>/` unless the repository already uses a different convention.
- Core artifacts are `spec.md`, `plan.md`, and `tasks.md`.
- Keep live execution state inside `tasks.md`; do not add `progress.md`.
- For bug fixes, document reproduction, expected behavior, unchanged behavior, and regression coverage before patching.
