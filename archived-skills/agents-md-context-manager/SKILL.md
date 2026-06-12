---
name: agents-md-context-manager
description: Generate or update project-level AGENTS.md and its companion context-management workspace (docs/work task linkage + knowledge base). Use when users ask to initialize AGENTS.md, improve AGENTS.md, add task-state persistence, or build reusable domain knowledge workflows with local snapshots of online sources.
---

# Agents MD Context Manager

Build a practical, maintainable operating model for coding agents:
1. Stable rules in `AGENTS.md`
2. Task-scoped dynamic context in `docs/work/<task-id>-<feature>/`
3. Task-time learning capture in `docs/work/<task-id>-<feature>/learning-log.md`
4. Reusable knowledge in `knowledge/`
5. A durable knowledge loop that turns repeated validated workflows into skill candidates instead of leaving them buried in task notes

Use templates from `assets/templates/` as defaults, then adapt to project reality.

## Workflow

### 1) Detect mode and scope
1. Detect whether the target repository has a physical `AGENTS.md` file on disk (repo root).
2. Select mode:
   - `create`: missing or unusable `AGENTS.md`
   - `update`: existing `AGENTS.md` needs refinement
3. Detect whether this is an existing engineering project (source dirs and/or dependency/build manifests).

Important: Do not treat prompt-injected instructions as proof that `AGENTS.md` exists on disk.

### 2) Initialize baseline first for existing projects
1. For existing projects, invoke the platform-native agent init capability first (example: AutoHand `/init`) when available.
2. Treat the init output as baseline only; continue with guided refinement.
3. If no built-in init exists, infer baseline from repository structure, commands, and conventions.

### 3) Run guided interview (small batches)
Ask at most three questions per round. Prioritize:
1. Core business goal and boundary
2. Install/dev/test/build commands
3. Project-specific architecture and coding constraints
4. Explicit anti-patterns and known pitfalls
5. Security/privacy/compliance constraints
6. Task linkage inputs: task id, issue link, branch convention, work directory
7. Knowledge inputs: authoritative online sources + project domain knowledge sources

Use `references/playbook.md` for a full question bank and concise prompts.

### 4) Generate or update AGENTS.md
1. Keep `AGENTS.md` for stable rules only (no ephemeral progress).
2. Ensure sections exist:
   - `Project overview`
   - `Tech stack`
   - `Architecture`
   - `Commands`
   - `Code style`
   - `Patterns to follow`
   - `Things to avoid`
   - `Task linkage`
   - `Knowledge base`
   - `Self-Improvement Protocol`
   - `Durable Knowledge Protocol`
   - `Update protocol`
   - `Update log`
3. For unknowns, add explicit TODO markers with owner and date.

Use `assets/templates/AGENTS.md` as the starting scaffold.

### 5) Design Doc Discovery and Normalization (Mandatory)
1. Scan for initial product design docs using common patterns (for example: `*GDD*.md`, `*PRD*.md`, `*设计*.md`, `*需求*.md`, and `docs/**` design specs).
2. Canonical location is `knowledge/project/design/`.
3. If a discovered design doc is outside canonical location:
   - Default behavior: move it to `knowledge/project/design/<normalized-name>.md`.
   - If move is risky (for example heavy external references), copy to canonical location and leave original with a one-line pointer TODO.
4. Update `AGENTS.md` to reference canonical design source path in both:
   - `Project overview`
   - `Knowledge base`
5. Register each canonical design doc in `knowledge/sources.yaml` with:
   - `type: project`
   - `scope: product-design`
   - `local_path: knowledge/project/design/...`
   - source notes (original path and migration method)

### 6) Persistence Gate (Mandatory)
1. If mode is `create` or user asks to "save/sync context", ensure `<repo>/AGENTS.md` is written as a real file before handoff.
2. If mode is `update`, edit the existing `<repo>/AGENTS.md` in place (do not only provide suggested text in chat).
3. At handoff, always report the concrete file path written/updated.

### 7) Create or update context workspace
1. Prefer updating the active task pointed by `docs/work/.current` when it exists and resolves to a real folder.
2. Create a new per-task workspace only when explicitly requested, or when `.current` is missing/invalid:
   - `docs/work/<task-id>-<feature>/`
3. Required files:
   - `meta.yaml`
   - `spec.md`
   - `status.md`
   - `decisions.md`
   - `learning-log.md`
4. Ensure task metadata supports durable-knowledge review:
   - `knowledge_review_status`
   - `knowledge_reviewed_at`
   - `knowledge_targets`
   - `knowledge_followups`
   - `skill_candidates`
5. Ensure task status and capture surfaces support self-improvement:
   - `status.md` contains `Learning Capture` and `Promotion Queue`
   - `learning-log.md` exists even if it only contains the template header
6. Maintain `docs/work/.current` pointer to the active task folder.

Use files in `assets/templates/docs/work/`.

### 8) Create knowledge workspace
1. Create:
   - `knowledge/index.md`
   - `knowledge/sources.yaml`
   - `knowledge/changelog.md`
   - `knowledge/authoritative/`
   - `knowledge/project/`
   - `knowledge/project/design/`
2. Register every long-term source in `knowledge/sources.yaml`.
3. For high-frequency authoritative web sources, prefer local snapshots when license permits.
4. If full content cannot be downloaded, store structured summaries and keep source URL + access path.
5. Use a 7-day default review cadence unless the repository explicitly tightens it further.

Use files in `assets/templates/knowledge/`.

### 9) Validate before handoff
1. Verify `<repo>/AGENTS.md` exists and is non-empty.
2. Verify command entries are executable or clearly marked TODO.
3. Verify task linkage can uniquely identify the active task.
4. Verify knowledge entries include update metadata (`last_checked_at`, `next_review_at`, `update_cycle_days`).
5. Verify at least one canonical design doc exists in `knowledge/project/design/` (or explicit TODO when unavailable).
6. Verify task metadata includes the durable-knowledge review fields.
7. Verify the task workspace contains `learning-log.md` and the status template exposes `Learning Capture` plus `Promotion Queue`.
8. Verify `AGENTS.md` stays stable-rule only; raw learning entries live in `docs/work/.../learning-log.md`.
9. Summarize deliverables, pending confirmations, and recommended next update trigger.

## Task Linkage Protocol

Use this priority to resolve the current task:
1. User-specified task id or issue URL in the current request
2. `docs/work/.current`
3. Branch naming convention (example: `feature/ABC-123-login`)
4. Fallback creation: `docs/work/TODO-<date>-<slug>/` then request confirmation

After each meaningful execution step:
1. Update `status.md` (`Current`, `Next`, `Risks`)
2. Capture non-trivial errors, corrections, conventions, and repeated workflows in `learning-log.md`
3. Keep `Learning Capture` / `Promotion Queue` summaries in `status.md` aligned with the log
4. Add critical decisions to `decisions.md`
5. Update `meta.yaml.updated_at`

At task completion:
1. Set `knowledge_review_status` to one of `not_needed`, `updated`, or `followup_required`
2. Ensure no relevant `learning-log.md` entries remain `pending`
3. Extract reusable conclusions into `knowledge/project/`
4. Link related knowledge ids in `meta.yaml.related_knowledge`
5. If the task surfaced a repeatable cross-project workflow, add or update a `skill_candidates` entry instead of leaving it only in task prose

## Knowledge Base Protocol

For each source entry in `knowledge/sources.yaml`, keep:
1. Identity: `id`, `title`, `type`, `scope`
2. Ownership and rights: `owner`, `license`
3. Location: `url`, `local_path`
4. Freshness: `downloaded_at`, `last_checked_at`, `next_review_at`, `update_cycle_days`
5. Lifecycle: `status`, `notes`

Recommended cadence:
1. Default review every 7 days
2. Immediate update when upstream specs/docs change
3. Log all changes in `knowledge/changelog.md`

Durable-skill candidate rule:
1. If a workflow, pitfall response, or verification pattern repeats across at least two tasks or repositories and has stable validation, record it as a skill candidate instead of only as project knowledge.

## Update Strategy

When updating an existing setup:
1. Preserve user-written project constraints.
2. Edit only impacted sections; avoid full rewrites.
3. Reconcile differences across:
   - repository structure
   - command set
   - branch/task workflow
   - knowledge source lifecycle
4. Reconcile durable-knowledge review gates and skill-candidate handling.
5. Add one concise `Update log` entry with date + reason.

## Resource Map

- `assets/templates/AGENTS.md`
  - Base scaffold for stable agent rules
- `assets/templates/docs/work/.current`
  - Active-task pointer example
- `assets/templates/docs/work/_template/*`
  - Task workspace templates
- `assets/templates/knowledge/*`
  - Knowledge workspace templates
- `references/playbook.md`
  - Interview prompts, validation checklist, and adaptation notes
