# AGENTS.md

## Purpose

This repository uses a Codex-first development workflow with OpenSpec change
management, DevFlow-native engineering discipline, and optional methodology and
roadmap providers.

Do not implement non-trivial changes directly from chat memory.

## Workflow Ownership

- DevFlow defaults to `methodology_profile: core` and `roadmap_provider: none`.
- GSD owns roadmap, milestones, phases, and phase verification only when
  `roadmap_provider: gsd` is explicitly selected or verifiably inferred.
- OpenSpec owns behavior-level proposal, specs, design, tasks, verification, sync, and archive.
- The selected methodology profile provides decision, planning, TDD, diagnosis,
  review, and completion primitives; canonical evidence remains DevFlow/OpenSpec-owned.
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

## Capability Routing

Route stable capabilities from
`dev/plugins/dev-flow/docs/provider_profiles.json`, not hard-coded provider
skills. The configured methodology and roadmap profiles supply implementations;
an unselected provider never blocks readiness or contributes commands, links,
hooks, or fallback behavior. Ambiguous or stale selected sources fail closed.

Activation, provider selection persistence, migration, dependency changes, and
external side effects retain their explicit authorization gates.

## Intake and Planning

- Use `feature-intake` for feature, bug, refactor, migration, tooling, or
  workflow-repair intake.
- Use `capability-research` for current external/platform/plugin/API/runtime
  evidence.
- Record the Skill Routing Ledger for research, design, architecture, product
  shape, and non-trivial plans.
- Resolve Open Questions before finalizing a design or implementation plan.
- Use `ai-native-tech-plan` for the technical execution contract and
  `change-plan` for canonical OpenSpec proposal, design, specs, and tasks.

Do not start implementation until scope, solution, validation, risks, and the
next ledger item are durable.

## Methodology Artifact Mapping

External methodology skills provide process primitives only. OpenSpec, selected
roadmap-provider files, and `.planning/devflow/**` are the canonical artifacts.

- If `superpowers:brainstorming` produces design notes for behavior, API, data, integration, compatibility, or error-handling work, map the approved content into `openspec/changes/<change-id>/proposal.md`, `design.md`, and `specs/`.
- If `superpowers:writing-plans` produces task guidance for an OpenSpec change, map it into `openspec/changes/<change-id>/tasks.md`, including Capability Slices, Execution Ledger, Acceptance Criteria, and Validation Commands.
- If `superpowers:writing-plans` supports selected GSD phase or milestone work,
  map it through the active GSD binding into the provider-owned phase plan; for
  roadmap provider `none`, use a DevFlow-approved ledger.
- Treat `docs/superpowers/specs/...` and `docs/superpowers/plans/...` as drafts, review notes, or inputs unless their content has been copied into the canonical artifacts above.
- If Superpowers notes conflict with OpenSpec, GSD, or DevFlow files, update or discard the notes; do not let them become a second source of truth.

## Roadmap/OpenSpec Skills

OpenSpec and any selected GSD overlay are activated project-locally through
`.agents/skills/`; do not enable GSD globally. Legacy `.codex/skills/` entries
are migration inputs, not the normal target layout.

- Use `openspec-explore` when requirements, compatibility, or behavior boundaries are unclear.
- Use `openspec-propose` before implementing user-visible behavior, public API, data model, permission, persistence, integration, migration, error handling, or compatibility changes.
- Use `openspec-apply-change` when executing approved OpenSpec tasks.
- Use `openspec-archive-change` only after verification evidence is recorded and the archive gate is clear.
- When `roadmap_provider: gsd`, use `gsd-discuss-phase` and `gsd-plan-phase` for
  milestone/phase structure, `gsd-execute-phase` for an approved phase plan,
  and `gsd-verify-work` before marking the bound phase shipped.
- When `roadmap_provider: none`, keep sequencing in the OpenSpec task ledger or
  `.planning/devflow/**`; do not require GSD.

## Decision and Planning Flow

- Resolve `.dev-flow.json` provider selection before routing methodology skills.
  Core uses DevFlow-native intake/planning, `lean-matt` uses only the mapped Matt
  primitives, and `strict-superpowers` uses the mapped Superpowers primitives.
- Use `capability-research` when a solution depends on current, external, platform, plugin, API, hook, CLI, installed-cache, or local-vs-platform capability evidence; the detailed evidence workflow lives in that skill.
- For design, research, architecture, product-shape, or technical-plan requests,
  create a `Skill Routing Ledger` before writing the final design or plan. Record
  `kind`, workflow mode, `artifact-status: draft/final`,
  `capability-research: required/used/skipped`,
  `decision-resolution: required/used/skipped`, `decision-grilling:
  required/used/skipped`, `implementation-planning: required/used/skipped`,
  `architecture-guidance: required/used/skipped`, OpenSpec/roadmap routing,
  and the concrete reason for any skip.
- If an artifact has unresolved `Open Questions`, decision resolution cannot be marked
  skipped. Mark the artifact as draft, not final, and use the selected profile's
  `decision-resolution` mapping or record it as required in the ledger.
- If unresolved `Open Questions` remain after local evidence gathering, use
  decision grilling: ask one question at a time, provide a recommended answer,
  walk dependent decision branches, and record resolved decisions in canonical
  OpenSpec, GSD, or DevFlow ledger artifacts. Decision grilling cannot be
  marked skipped while unresolved questions remain unless the artifact remains
  draft.
- Ledger field: `decision-grilling: required/used/skipped`.
- Use `openspec-explore` during decision resolution when the uncertainty is about user-visible behavior, compatibility, requirements, or acceptance criteria.
- Use `gsd-discuss-phase` for milestone, sequencing, or phase uncertainty only
  when `roadmap_provider: gsd`.
- Before a non-trivial plan, use the selected profile's
  `implementation-planning` mapping; canonicalize the result in OpenSpec or the
  selected roadmap ledger.
- Use `ai-native-tech-plan` when generating technical plans, implementation plans, architecture plans, Codex execution plans, workflow plans, or anti-partial-delivery plans.
- Use `openspec-propose` after decision resolution when behavior-level artifacts need to become proposal, design, specs, and tasks.
- Use `gsd-plan-phase` only when the selected GSD overlay should own an approved phase plan.
- Do not move from decision resolution or planning into implementation until the chosen plan, scope, verification approach, and open risks are recorded.

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
- Create or update a roadmap only when a roadmap provider is explicitly
  selected. Core + none does not create a synthetic roadmap.
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

## Methodology Provider Discipline

External methodology providers are opt-in, source-pinned, and activated
project-locally through `.agents/skills/`; do not enable them globally for this
workflow. Legacy `.codex/skills/` entries are migrated through DevFlow.

- `core`: use DevFlow-native capability mappings; no Superpowers or Matt dependency.
- `lean-matt`: use only `grilling`, `tdd`, `diagnosing-bugs`, `code-review`,
  `codebase-design`, and `domain-modeling`; DevFlow retains planning,
  orchestration, and completion proof.
- `strict-superpowers`: use the registry mappings for brainstorming, planning,
  TDD, diagnosis, review, orchestration, and verification. Conditional skills
  are required only when their capability is triggered.
- Missing, ambiguous, untrusted, or drifted selected-provider content blocks
  that routed capability. Run provider diagnostics/activation; never fall back
  silently to another installed provider.

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

Before marking work complete, run relevant tests, run lint/typecheck/build where applicable, update OpenSpec tasks, update `.planning/devflow/STATE.md`, record verification evidence, and report remaining risks.

## Context Checkpoint and Compaction

At major workflow boundaries, create a durable checkpoint before continuing.

Major boundaries include project setup completed, codebase mapping completed, design saved, OpenSpec change planned, phase plan saved, verification passed, change archived, and phase shipped.

Before compaction, persist `.planning/devflow/STATE.md`, selected-provider
roadmap files when applicable, relevant `openspec/changes/` files, changed files
summary, validation commands and results, unresolved risks, and next action.

Compaction is not a source of truth. Repository files remain authoritative. When a checkpoint is a
continuation gate for the current thread, recommend `/compact` in Codex CLI before moving to the next major
stage. When the task is complete or at a handoff/review boundary, update state immediately and treat compact
as optional. If an external harness runs API compaction for a pending gate, record the compact result under
`.planning/devflow/compact-results/`. If compaction is unavailable, start a new session from the checkpoint file.

## Forbidden Without Explicit Approval

- Deleting large amounts of code.
- Changing public APIs.
- Changing persistence schema.
- Adding production dependencies.
- Rewriting architecture.
- Bypassing failing tests.
- Archiving OpenSpec changes without verification.
