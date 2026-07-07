# AGENTS.md

## Purpose

This repository uses a Codex-first development workflow with GSD-style planning, OpenSpec change management, engineering discipline, and plan-first gates.

Do not implement non-trivial changes directly from chat memory.

## Workflow Ownership

- GSD owns roadmap, milestones, phases, and phase verification.
- OpenSpec owns behavior-level proposal, specs, design, tasks, verification, sync, and archive.
- Engineering discipline governs clarification, brainstorming, planning, TDD, review, and finishing.
- Codex planning behavior is required before major design or implementation boundaries.

## Project Control Plane

Use these checked-in files as the durable execution control plane:

- `AGENTS.md` routes Codex to the workflow and required skills.
- `ENGINEERING_POLICY.md` records durable engineering, dependency, testing, evidence, review, and release policy.
- `TASK_LEDGER.md` records the Goal Contract, task decomposition, owner, write set, required evidence, review gate, status, and execution log.
- `EVIDENCE_TEMPLATE.md` defines the evidence format for TDD, validation commands, changed files, risks, and reviewer notes.
- `REVIEW_CHECKLIST.md` defines correctness, verification, scope, release, and archive readiness checks.

Do not treat chat context or Superpowers scratch files as the source of truth
when a control-plane file is required.

## Superpowers Artifact Mapping

Superpowers provides process discipline for brainstorming, planning, TDD, and verification gates. OpenSpec, GSD, and DevFlow planning files are the canonical artifacts for this workflow.

- If `superpowers:brainstorming` produces design notes for behavior, API, data, integration, compatibility, or error-handling work, map the approved content into `openspec/changes/<change-id>/proposal.md`, `design.md`, and `specs/`.
- If `superpowers:writing-plans` produces task guidance for an OpenSpec change, map it into `openspec/changes/<change-id>/tasks.md`, including Capability Slices, Execution Ledger, Acceptance Criteria, and Validation Commands.
- If `superpowers:writing-plans` supports GSD phase or milestone work, map it into `.planning/phases/.../PLAN.md` or a DevFlow-approved ledger.
- Treat `docs/superpowers/specs/...` and `docs/superpowers/plans/...` as drafts, review notes, or inputs unless their content has been copied into the canonical artifacts above.
- If Superpowers notes conflict with OpenSpec, GSD, or DevFlow files, update or discard the notes; do not let them become a second source of truth.

## GSD/OpenSpec Skills

GSD and OpenSpec are activated project-locally through `.agents/skills/`; do not enable them globally for this workflow. Legacy `.codex/skills/` entries should be treated as migration inputs, not as the normal target layout.

- Use `openspec-explore` when requirements, compatibility, or behavior boundaries are unclear.
- Use `openspec-propose` before implementing user-visible behavior, public API, data model, permission, persistence, integration, migration, error handling, or compatibility changes.
- Use `openspec-apply-change` when executing approved OpenSpec tasks.
- Use `openspec-archive-change` only after verification evidence is recorded and the archive gate is clear.
- Use `gsd-discuss-phase` and `gsd-plan-phase` for multi-stage work, phase planning, broad refactors, or milestone planning.
- Use `gsd-execute-phase` only when executing an approved phase plan, and `gsd-verify-work` before marking a phase shipped.

## Brainstorm and Planning Flow

- Use `superpowers:brainstorming` before committing to a solution when goals, constraints, tradeoffs, or implementation shape are still open.
- Use `capability-research` when a solution depends on current, external, platform, plugin, API, hook, CLI, installed-cache, or local-vs-platform capability evidence; the detailed evidence workflow lives in that skill.
- For design, research, architecture, product-shape, or technical-plan requests,
  create a `Skill Routing Ledger` before writing the final design or plan. Record
  `kind`, workflow mode, `capability-research: required/used/skipped`,
  `brainstorming: required/used/skipped`, `decision-grilling:
  required/used/skipped`, `writing-plans`, OpenSpec/GSD routing, and the
  concrete reason for any skip.
- If an artifact has unresolved `Open Questions`, Brainstorming cannot be marked
  skipped. Mark the artifact as draft, not final, and return to
  `superpowers:brainstorming` or record `brainstorming: required` in the ledger.
- If unresolved `Open Questions` remain after local evidence gathering, use
  decision grilling: ask one question at a time, provide a recommended answer,
  walk dependent decision branches, and record resolved decisions in canonical
  OpenSpec, GSD, or DevFlow ledger artifacts. Decision grilling cannot be
  marked skipped while unresolved questions remain unless the artifact remains
  draft.
- Ledger field: `decision-grilling: required/used/skipped`.
- Use `openspec-explore` during brainstorming when the uncertainty is about user-visible behavior, compatibility, requirements, or acceptance criteria.
- Use `gsd-discuss-phase` during brainstorming when the uncertainty is about milestones, sequencing, scope boundaries, or phase structure.
- Use `superpowers:writing-plans` before writing a non-trivial implementation plan, phase plan, migration plan, or refactor plan.
- Use `ai-native-tech-plan` when generating technical plans, implementation plans, architecture plans, Codex execution plans, workflow plans, or anti-partial-delivery plans.
- Use `openspec-propose` after brainstorming when behavior-level artifacts need to become proposal, design, specs, and tasks.
- Use `gsd-plan-phase` after brainstorming when the work should become an approved phase plan.
- Do not move from brainstorming/planning into implementation until the chosen plan, scope, verification approach, and open risks are recorded.

## Goal Workflow

- Apply the Goal Suitability Gate during intake or planning, before
  context-health drift appears. Use `define-goal` when the user asks to create,
  set, refine, or use a goal, asks for goal-backed work, or when the
  development task is long-running, multi-slice, migration or release oriented,
  broad-refactor oriented, cross-context, subagent/delegation backed, or
  otherwise likely to lose its definition of done.
- `define-goal` owns active goal checks, goal-tool calls, objective wording,
  verification evidence, scope boundaries, non-goals, and stop conditions.
- Apply the Goal Quality Gate before goal creation: the candidate objective
  must name outcome, verification evidence, scope boundaries, non-goals, success
  threshold, and stop conditions.
- After `define-goal` shapes the objective, set it in a Codex app, IDE, or CLI
  composer with `/goal <objective>`. Use `/goal`, `/goal pause`,
  `/goal resume`, and `/goal clear` to inspect or control the active goal.
- If `/goal` is unavailable, enable `features.goals` in Codex config or run
  `codex features enable goals`. Do not rely on a top-level CLI `goal`
  subcommand.
- Do not require a Codex goal for ordinary narrow implementation work solely
  because it has multiple steps. Treat context-health goal drift as a repair
  signal after drift is discovered, not the primary trigger.
- DevFlow hooks and scripts may generate Goal Mode Prompts and route to
  `define-goal`, but they do not call goal tools automatically.

## AI Coding Planning Rules

This repository follows an AI-native execution model.

Do not produce human-style delivery plans such as:

- MVP or prototype as the default completion boundary.
- Numbered delivery phases as completion boundaries for required behavior.
- Future Work sections for required functionality.
- Calendar estimates, sprint estimates, or staffing assumptions.
- Partial implementation plans that stop after a simplified first slice.

Unless explicitly requested, assume the user wants the complete Target State.

When asked to design or implement a technical solution, use this structure:

1. Target State
   - Describe the complete final behavior after the task is done.
   - Include user-visible behavior, internal structure, boundaries, and non-goals.

2. Completion Contract
   - List concrete acceptance criteria.
   - Include tests, commands, screenshots, docs, or runtime checks where applicable.

3. Capability Slices
   - Break work into dependency-ordered, independently verifiable slices.
   - Each slice must be production-complete for its own scope.
   - Each slice must include implementation, validation, and cleanup.

4. Execution Ledger
   - Maintain a checklist in the plan or a repo file.
   - Mark each item done only after validation.
   - Resume from the ledger after interruption or context compaction.

5. Final Verification
   - Run the smallest relevant test suite, lint/typecheck, and project-specific checks.
   - Report exact commands and results.

GSD phases are governance and sequencing containers, not technical completion boundaries.

## Repair Solution Discipline

When asked to repair a bug, workflow break, or broken behavior, do not start
from the minimal fix as the default recommendation; after investigation,
present the systemic and thorough solution first: root cause, affected
contracts, durable prevention, tests, docs, migrations or compatibility
concerns, and verification.

Then compare whether actual execution should be the systemic repair, a minimal
fix, a staged repair, or a deferred follow-up. Explain why the selected path is
appropriate for the current repo state, risk, approval boundary, and validation
cost. This does not override brownfield compatibility, OpenSpec, safety, or
user-approval gates.

## Project Mode

Project mode: brownfield

### Greenfield

- Establish Target State and Completion Contract first.
- Create or update `.planning/ROADMAP.md`.
- Create initial OpenSpec specs or an `initial-target-state` change.
- Establish test, lint, and build baselines early.

### Brownfield

- Inspect existing architecture, conventions, tests, and specs first.
- Prefer minimal compatible changes.
- Reuse existing components, services, APIs, tokens, routing, data fetching, and error handling.
- Add characterization or regression tests before risky changes.

## When OpenSpec Is Required

Create or update `openspec/changes/<change-id>/` before implementation if work changes user-visible behavior, public APIs, data models, permissions, persistence, integrations, migrations, error handling, or compatibility behavior.

## Workflow Mode Routing

DevFlow routes work before execution:

- `Full OpenSpec` is mandatory for user-visible behavior, public API, data model,
  persistence, migration, integration, permission, error-handling, or
  compatibility changes. `.dev-flow.json` configuration cannot bypass this gate.
- `Lightweight Ledger` may be used only when `.dev-flow.json` enables it and the
  work is docs-only, test-only, internal maintenance, or a low-risk bugfix. The
  ledger must include Target State, Scope / Non-Goals, Validation Commands,
  Execution Log, and Completion Claim.
- `Prototype Mode` requires an explicit user request for a spike, prototype,
  proof of concept, or demo. Record non-production status and cleanup or
  promotion criteria before relying on the output.

DevFlow hooks support `off`, `warn`, and `block` modes through `.dev-flow.json`.
When hooks warn or block, diagnostics should preserve the Codex hook schema and
include current stage, failed gates, next action, and recommended skill or
command.

## Superpowers Discipline

Superpowers is activated project-locally through `.agents/skills/`; do not enable it globally for this workflow. Legacy `.codex/skills/` entries should be scanned and migrated through DevFlow rather than edited manually.

- Before structured ideation or solution exploration, use `superpowers:brainstorming`.
- Before writing or committing to a non-trivial plan, use `superpowers:writing-plans`.
- Before implementing a feature, bugfix, or risky behavior change, use `superpowers:test-driven-development`.
- Before claiming work is complete, fixed, passing, ready to commit, or ready for PR, use `superpowers:verification-before-completion`.
- If either Superpowers skill is unavailable, run the project orchestrator dependency check and activation before continuing.

## Plugin Eval Gate

- When creating or updating Codex plugins or skills, resolve the release target first: `sync_release_assets.py --eval-target <path> --json`. If a release counterpart exists, run Plugin Eval against the release path, for example `plugin-eval analyze plugins/<name> --format markdown` or `plugin-eval analyze <skill-name> --format markdown`.
- Use direct dev-path Plugin Eval only as a diagnostic source-quality check; it is not the primary release readiness signal when a release package exists.
- If `plugin-eval` is not on PATH, use the installed Plugin Eval plugin's `scripts/plugin-eval.js` with `node`.
- When Plugin Eval reports failures, warnings, or fix-first recommendations, default to fixing or optimizing them before completion.
- Deferral is an exception: only defer findings that are out of scope, destructive or risky, require dependency or architecture decisions, or need explicit user approval.
- Deferred findings must record the reason, residual risk and follow-up path.
- Verification evidence must record the score, findings, and optimization decisions, plus the evaluated target.

## Local Reference Update Reminder

After major Codex plugin or skill changes, remind the user to update local Codex
references before relying on the changed behavior locally. Start dry-run:
`python3 dev/scripts/codex_auto_update_plugins_skills.py --json`. Report release
asset sync, installed plugin cache refresh needs, and project-local skill links
migration. Apply mode requires explicit update intent or confirmation; record any
skipped local reference update with reason and residual risk.

## DevFlow Refresh Workflow

Use `dev-flow-refresh` when DevFlow has upgraded, when the local/global DevFlow
plugin installation or installed cache needs refresh, or when project-local
DevFlow workflow configuration needs refresh.

- Refresh global DevFlow first, then project-local workflow configuration.
- Start with the targeted local plugin refresh
  `codex plugin add dev-flow@cy-codex-skills --json` unless the user explicitly
  asks for the full updater workflow.
- Verify source/cache freshness with `doctor_workflow.py --check-cache-drift`
  or `codex_auto_update_plugins_skills.py --json` before claiming local runtime
  freshness.
- Run project diagnostics before applying project changes:
  `plugin_project_migration.py`, `validate_workflow_state.py`,
  `doctor_workflow.py --check-cache-drift`, `scaffold_workflow.py --dry-run`,
  and `git status`.
- Treat `AGENTS.md.generated` as a merge-required candidate. Compare durable
  workflow rules with active `AGENTS.md`; merge only durable routing or policy
  changes and preserve project-specific guidance.
- Ordinary skill-link refresh may use `activate_project_dependencies.py
  --refresh-project-skills`; legacy `.codex/skills` cleanup and conflict
  resolution require explicit approval.

## Execution Rules

- Execute one task at a time unless explicitly instructed otherwise.
- Prefer TDD for business logic, bug fixes, and risky behavior.
- Do not expand task scope without updating the plan.
- Do not introduce dependencies without documenting why.
- Do not modify unrelated files.

## Verification Rules

Before marking work complete, run relevant tests, run lint/typecheck/build where applicable, update OpenSpec tasks, update `.planning/STATE.md`, record verification evidence, and report remaining risks.

## Context Checkpoint and Compaction

At major workflow boundaries, create a durable checkpoint before continuing.

Major boundaries include project setup completed, codebase mapping completed, design saved, OpenSpec change planned, phase plan saved, verification passed, change archived, and phase shipped.

Before compaction, persist `.planning/STATE.md`, relevant `.planning/phases/` files, relevant `openspec/changes/` files, changed files summary, validation commands and results, unresolved risks, and next action.

Compaction is not a source of truth. Repository files remain authoritative. When a checkpoint is a
continuation gate for the current thread, recommend `/compact` in Codex CLI before moving to the next major
stage. When the task is complete or at a handoff/review boundary, update state immediately and treat compact
as optional. If an external harness runs API compaction for a pending gate, record the compact result under
`.planning/compact-results/`. If compaction is unavailable, start a new session from the checkpoint file.

## Forbidden Without Explicit Approval

- Deleting large amounts of code.
- Changing public APIs.
- Changing persistence schema.
- Adding production dependencies.
- Rewriting architecture.
- Bypassing failing tests.
- Archiving OpenSpec changes without verification.
