# Design: Integrate AI-native planning

<!-- ai-native-plan-lint: allow-human-planning-terms -->

## Approach

Make AI-native planning a first-class orchestrator route instead of a separate, optional style guide. The implementation adds one focused skill, supporting references/templates, and deterministic lint tooling, then updates existing scaffold and routing instructions so new projects receive the same planning rules by default.

The plugin will continue to rely on existing project-local dependencies:

- Superpowers for brainstorming, writing plans, TDD, and verification-before-completion.
- OpenSpec for behavior-level proposal, design, specs, tasks, and archive gates.
- GSD for roadmap and workflow sequencing.

The change clarifies that GSD phases are governance checkpoints and sequencing containers, not acceptable technical completion boundaries for required behavior. Technical plans must use Target State, Completion Contract, Capability Slices, Execution Ledger, Acceptance Criteria, Validation Commands, and Final Verification.

## Data Flow

Planning requests flow through `project-orchestrator` and `feature-intake`.

1. A user asks for a technical plan, implementation plan, architecture plan, workflow plan, or a way to prevent partial completion.
2. `project-orchestrator` routes the work to `ai-native-tech-plan` when the request is plan-generation oriented, or to `feature-intake`/`change-plan` when behavior-level OpenSpec artifacts are needed.
3. `ai-native-tech-plan` instructs Codex to:
   - confirm whether the user explicitly requested a prototype/demo/partial target;
   - default to complete Target State otherwise;
   - generate a ledger-backed plan with capability slices and validation commands;
   - save the ledger to a repo file for medium or large tasks;
   - produce `/goal`, continue, and review prompts when useful.
4. During execution, `execute-task` requires reading the ledger and active OpenSpec artifacts before starting the next slice, then updating ledger status only after validation.
5. During completion, `verify-and-archive` checks completion contracts and validation evidence before claiming the work is complete or archiving.

Generated project scaffolds receive AI-native defaults through template updates:

- `AGENTS.md.template` gains AI Coding Planning Rules.
- `ROADMAP.md.template`, `PHASE_PLAN.md.template`, and OpenSpec templates stop framing setup as MVP-style delivery.
- New task ledger templates provide a durable source of truth after compaction or session restart.

## Compatibility

- Existing scripts remain callable with the same arguments.
- The release plugin keeps the same manifest name and plugin identity.
- Existing workflow terms are retained where they are part of GSD/OpenSpec mechanics, but generated technical plans must not use them as delivery boundaries.
- Documents that explain prohibited planning terms include the lint allow marker.

## Testing

Add focused tests that fail before implementation:

- Expected skill inventory includes `ai-native-tech-plan`.
- Scaffolded greenfield repositories use an AI-native baseline change id rather than the old MVP baseline.
- Generated AGENTS.md includes AI Coding Planning Rules and no longer instructs greenfield projects to establish MVP scope.
- OpenSpec task/design templates include Target State, Completion Contract, Capability Slices, Execution Ledger, and Validation Commands.
- The lint script fails on generated plans that contain forbidden planning terms and passes AI-native plans.

Run the existing plugin unittest suite after implementation and record verification evidence through `record_verification.py`.
