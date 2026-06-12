# Spec Workflow Playbook

Use this file when the main skill has triggered and you need the detailed operating rules.

## 1. Core shape

This skill adapts the Spec Kit sequence into Codex-friendly artifacts:
1. Repo grounding
2. Clarify only what materially changes the spec
3. Write `spec.md`
4. Write `plan.md`
5. Write `tasks.md`
6. Implement and keep status inside `tasks.md`

Optional artifacts are created only when they reduce execution risk:
1. `research.md`
2. `data-model.md`
3. `contracts/`
4. `quickstart.md`

Repository `AGENTS.md` acts as the standing constitution. Read it before inventing process rules.

## 2. Folder selection and reuse

Prefer reusing an existing matching spec folder when:
1. The user names a feature or bug that already maps to an existing slug.
2. The repo has a current active spec for the same work.
3. The artifacts clearly represent an unfinished implementation of the same request.

Default folder policy when the repo has no stronger convention:
1. Root under `specs/`.
2. Use `specs/<NNN>-<slug>/`.
3. If `specs/` already contains numbered folders, continue that numbering style.
4. If there is no numbering yet, start with `001`.
5. Keep the slug stable across follow-up work.

Do not create duplicate folders for simple iteration on the same effort.

## 3. Mode choice

Pick one mode only:

### `requirements-first`

Use when:
1. The desired outcome is known.
2. The implementation path is still flexible.
3. Acceptance criteria must be stabilized before coding.

Order:
1. `spec.md`
2. `plan.md`
3. `tasks.md`

### `design-first`

Use when:
1. The architecture, platform constraint, or integration boundary is the main source of complexity.
2. The user already points to a technical direction.
3. Requirements can be cleanly derived from a chosen design.

Order:
1. Draft `plan.md`
2. Backfill `spec.md` so scope and acceptance are explicit
3. Write `tasks.md`

The final artifact set still includes all three core files.

### `bugfix`

Use when:
1. The main task is fixing incorrect behavior.
2. Reproduction and regression boundaries matter more than feature expansion.
3. The smallest safe fix is preferred over redesign.

Required bugfix content:
1. Observed behavior
2. Expected behavior
3. Reproduction path
4. Impacted users or systems
5. Unchanged behavior that must remain intact
6. Root-cause hypothesis
7. Regression coverage strategy

The first engineering task should usually be one of:
1. Add or tighten a failing test.
2. Build a reliable reproduction path when automated tests are not yet practical.

## 4. Clarification gates

Checkpoint-style means: continue by default, but stop when the decision is expensive or user-owned.

Ask the user before continuing when:
1. A scope choice changes user-visible behavior or acceptance criteria.
2. Two or more viable designs have clearly different cost, rollout risk, or UX tradeoffs.
3. A migration, irreversible data change, or destructive action needs owner approval.
4. An external dependency, product policy, or integration contract is unknown and cannot be derived locally.
5. The user explicitly requests step-by-step approval.

Proceed without blocking when:
1. Naming, file placement, or internal abstraction choices follow existing repo patterns.
2. A small assumption is reversible and does not change the visible contract.
3. Missing context can be recorded in `Clarifications` or `Assumptions` without invalidating execution.

When proceeding on assumptions:
1. Record them in the artifact.
2. Keep them concrete.
3. Surface them briefly in chat.

## 5. `spec.md` expectations

The spec captures behavior and completion boundaries, not implementation structure.

Minimum sections:
1. Summary
2. Goals
3. Non-goals
4. Actors and scenarios
5. Functional requirements
6. Non-functional requirements
7. Acceptance criteria
8. Clarifications
9. Assumptions

For bugfix work, also include:
1. Observed behavior
2. Expected behavior
3. Reproduction
4. Unchanged behavior and regression boundaries

Requirements style:
1. Standard Markdown structure is the default.
2. Use EARS-style phrasing when precision matters for triggers, preconditions, or system responses.
3. Prefer EARS in acceptance-critical behavior and bugfix regression points.

Good requirement examples:
1. "When a user submits an expired reset link, the system shall show a recovery path instead of a generic failure page."
2. "While offline mode is active, when the client cannot refresh inventory, the system shall keep the last synced catalog visible and mark it stale."

## 6. `plan.md` expectations

The plan explains how the change will be implemented and validated.

Minimum sections:
1. Summary of approach
2. Architecture or component impact
3. Data flow or control flow
4. Interfaces and contracts
5. Files or areas likely to change
6. Risks and mitigations
7. Validation strategy
8. Rollout, migration, or fallback
9. Alternatives considered

Add `contracts/` when interface detail would clutter the plan:
1. REST or RPC payloads
2. Events and message schemas
3. Storage contracts
4. Cross-service adapters

Add `data-model.md` when the change introduces or materially reshapes:
1. Entities
2. Schema fields
3. State machines
4. Migrations or backfills

Use `research.md` before or alongside the plan when you need to compare options or gather evidence.

## 7. `tasks.md` expectations

`tasks.md` is both the execution plan and the live status log.

Keep a status block at the top with:
1. Overall status
2. Mode
3. Current phase
4. Current task
5. Next task
6. Blockers
7. Decisions made during execution
8. Validation log

Task rules:
1. Order tasks by dependency.
2. Keep each task independently verifiable.
3. Include the purpose, touched areas, validation step, and done condition.
4. Link each task back to relevant spec items.
5. Split discovery, implementation, validation, and cleanup when useful.

Update `tasks.md` after each meaningful execution step. Do not create a separate `progress.md`.

## 8. Optional artifacts

Create `research.md` when:
1. You need to compare alternatives.
2. The root cause is not yet proven.
3. Tradeoff evidence would otherwise clutter `plan.md`.

Create `data-model.md` when:
1. A schema or entity model is part of the change.
2. Compatibility or migration needs explicit treatment.
3. Validation needs fixture or migration coverage.

Create `contracts/` when:
1. Multiple payload or interface definitions need concrete examples.
2. Interface drift between systems is a project risk.

Create `quickstart.md` when:
1. Manual smoke testing needs a reusable checklist.
2. The work changes operator or QA flows.
3. Release readiness would benefit from a short execution guide.

## 9. Execution discipline

Before coding:
1. Read `AGENTS.md`, repo manifests, related modules, existing specs, and nearby tests.
2. Confirm the nearest validation commands already used by the repo.
3. Write or update the spec artifacts first.

During coding:
1. Implement from `tasks.md`.
2. Keep changes small and reviewable.
3. Update artifacts before or alongside any material design change.
4. Record blockers and decisions in `tasks.md`.

Validation:
1. Prefer repo-native tests, lint, type-check, build, and smoke commands.
2. For bugfixes, prove both the fix and the preserved unchanged behavior.
3. If validation is partial, log the gap explicitly.

Completion:
1. Core artifacts exist and match final behavior.
2. Acceptance criteria have been checked or explicitly deferred.
3. `tasks.md` status reflects the real end state.

## 10. Chat summaries

Keep chat summaries short and structured around:
1. Mode
2. Assumptions and decisions
3. Artifacts touched
4. Current or next task
5. Validation result
6. Remaining risk

Avoid dumping full specs into chat once the files exist.

## 11. Naming, replacement, and icons

This skill keeps the canonical name `$spec-workflow`.

Replacement policy:
1. If an installation target already has `spec-workflow/`, overwrite that directory instead of creating a sibling variant.
2. Only create a differently named skill if the user explicitly wants side-by-side coexistence.

Icon policy:
1. Icons exist only for UI distinction.
2. Icons do not affect triggering, naming, or override behavior.
3. Missing icons should never block skill use.

## 12. Templates

Use these templates as starting points, then adapt them to the repo:
1. `assets/templates/spec-template.md`
2. `assets/templates/plan-template.md`
3. `assets/templates/tasks-template.md`
4. `assets/templates/research-template.md`
5. `assets/templates/data-model-template.md`
6. `assets/templates/quickstart-template.md`
7. `assets/templates/agents-snippet.md`
