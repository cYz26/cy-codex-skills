# Playbook

## Fast Interview Prompts

Use short rounds (max 3 questions each).

### Round 1: Project Baseline
1. What is the core outcome this repository must deliver?
2. What are the canonical install/dev/test/build commands?
3. Which architecture constraints are mandatory (layering, modules, data boundaries)?

### Round 2: Quality and Risk
1. Which coding conventions are project-specific and non-negotiable?
2. Which anti-patterns or recurring mistakes must be blocked?
3. Are there compliance, privacy, or security rules that must be enforced?

### Round 3: Task Linkage and Knowledge
1. What is the current task id and issue URL?
2. What branch naming pattern maps to tasks?
3. Which authoritative references and internal domain docs must be tracked long-term?

### Round 4: Design Docs (if unclear)
1. Which file is the product design source of truth (GDD/PRD/spec)?
2. Can this file be normalized into `knowledge/project/design/` as canonical location?
3. Should old paths be moved or temporarily retained with redirect notes?

## Adaptation Notes

1. Prefer repository facts over assumptions.
2. Mark unknown fields as TODO with owner/date.
3. Keep `AGENTS.md` stable and policy-focused.
4. Keep transient execution state in `docs/work/.../status.md`.
5. Keep reusable knowledge in `knowledge/`.
6. If `.current` exists, update that task context first; avoid creating duplicate TODO folders.
7. Normalize product design docs into `knowledge/project/design/` and keep source registry in sync.
8. Create `docs/work/<task>/learning-log.md` and capture non-trivial errors, corrections, conventions, and repeated workflows there instead of burying them in chat.
9. Keep `status.md` focused on derived summaries via `Learning Capture` and `Promotion Queue`; raw event detail belongs in `learning-log.md`.
10. Before closing any task, make the durable-knowledge outcome explicit in task metadata and ensure relevant learning entries are no longer `pending`.
11. If a workflow repeats and already has stable validation, record it as a skill candidate instead of leaving it only in prose.

## Validation Checklist

1. A physical `AGENTS.md` exists at repository root and is non-empty.
2. `AGENTS.md` has required sections and project-specific rules.
3. `AGENTS.md` references product design source path (canonical).
4. `docs/work/.current` exists and points to a real task folder.
5. Task folder includes `meta.yaml`, `spec.md`, `status.md`, `decisions.md`, and `learning-log.md`.
6. `knowledge/project/design/` exists and contains canonical design doc (or explicit TODO).
7. `knowledge/sources.yaml` contains source metadata and review cadence, including design docs.
8. `knowledge/index.md` and `knowledge/changelog.md` are present.
9. Task metadata includes `knowledge_review_status`, `knowledge_targets`, `knowledge_followups`, and `skill_candidates`.
10. `status.md` contains `Learning Capture` and `Promotion Queue`, and `AGENTS.md` contains `Self-Improvement Protocol`.
11. No contradictory instructions across AGENTS and templates.
