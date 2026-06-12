# Knowledge Base Index

Last updated: <YYYY-MM-DD>

## Purpose
Store reusable references and project domain knowledge for coding agents.

## Structure
- `knowledge/sources.yaml`: source registry and update metadata
- `knowledge/authoritative/`: local snapshots of authoritative online references
- `knowledge/project/`: project-specific domain docs and decisions
- `knowledge/project/design/`: canonical product design docs (GDD/PRD/spec)
- `knowledge/changelog.md`: change history

## Durable Knowledge Loop
- Task-time raw learnings are captured in `docs/work/<task>/learning-log.md`.
- Task-close durable updates are tracked through `docs/work/<task>/meta.yaml` and `status.md`.
- Only triaged or promoted learnings may update durable docs or candidate records.
- Repositories should keep a 7-day default review cadence unless they choose a stricter policy.
- Repeated durable workflows should be promoted into skill candidates instead of staying only in task notes.

## Rules
1. Register every long-term source in `knowledge/sources.yaml`.
2. Save high-frequency online references locally when license permits.
3. Normalize product design docs into `knowledge/project/design/` and reference this path from `AGENTS.md`.
4. If full download is not permitted, store a structured summary with access instructions.
5. Update review metadata after each source check.
6. When a task completes, make the durable-knowledge outcome explicit instead of leaving the result implied in prose.
7. Keep raw learning detail in `learning-log.md`; do not turn `status.md` into an unstructured event dump.
