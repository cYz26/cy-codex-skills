# Tasks: Integrate AI-native planning

<!-- ai-native-plan-lint: allow-human-planning-terms -->

## Target State

The codex-project-orchestrator plugin treats AI-native planning as the default way to produce and execute technical work. Generated plans use Target State, Completion Contract, Capability Slices, Execution Ledger, Acceptance Criteria, Validation Commands, Goal Mode prompts, continue prompts, and final review checklists. Existing Superpowers, GSD, and OpenSpec skills remain integrated as execution discipline and governance mechanisms rather than human timeline planning.

## Completion Contract

- [x] `ai-native-tech-plan` skill exists in development and release plugin copies.
- [x] The skill includes concise core workflow instructions and loads detailed templates from references/assets.
- [x] Scaffold templates stop using MVP-style baseline language by default.
- [x] Generated AGENTS.md includes AI Coding Planning Rules.
- [x] OpenSpec templates and task templates include Target State, Completion Contract, Capability Slices, Execution Ledger, Acceptance Criteria, Validation Commands, and Final Verification.
- [x] A lint script detects human-style planning terms in generated plans and supports an explicit allow marker for policy docs.
- [x] Existing orchestrator skills route planning/execution/verification through the AI-native completion contract.
- [x] Unit tests cover the new skill, scaffold language, template content, and lint behavior.
- [x] Focused and full plugin tests pass, and verification evidence is recorded.

## Capability Slices

### Slice 1: Characterize current planning behavior

**Status:** done

**Goal**
- Capture failing expectations for AI-native skill presence, scaffold language, template structure, and lint behavior.

**Files / Modules**
- `dev/plugins/codex-project-orchestrator/tests/test_project_orchestrator.py`

**Implementation**
- [x] Add tests for `ai-native-tech-plan` skill inventory.
- [x] Add tests that greenfield scaffold uses an AI-native baseline change id.
- [x] Add tests that generated AGENTS.md contains AI Coding Planning Rules and does not instruct greenfield projects to establish MVP scope.
- [x] Add tests that OpenSpec templates contain AI-native planning sections.
- [x] Add tests for lint pass/fail behavior.

**Tests**
- [x] Run the new targeted test methods and confirm they fail before implementation.

**Validation Commands**
```bash
python3 -m unittest dev.plugins.codex-project-orchestrator.tests.test_project_orchestrator
```

**Done When**
- [x] Tests fail for the expected missing skill/template/script behavior before implementation.

**Risks / Rollback**
- Keep tests scoped to plugin behavior so failures do not depend on external Codex runtime state.

### Slice 2: Add AI-native planning skill and bundled resources

**Status:** done

**Goal**
- Provide the reusable planning capability as a Codex skill.

**Files / Modules**
- `dev/plugins/codex-project-orchestrator/skills/ai-native-tech-plan/SKILL.md`
- `dev/plugins/codex-project-orchestrator/skills/ai-native-tech-plan/references/planning-principles.md`
- `dev/plugins/codex-project-orchestrator/skills/ai-native-tech-plan/references/agents-md-snippet.md`
- `dev/plugins/codex-project-orchestrator/skills/ai-native-tech-plan/references/goal-prompt-template.md`
- `dev/plugins/codex-project-orchestrator/skills/ai-native-tech-plan/assets/task-ledger-template.md`
- `dev/plugins/codex-project-orchestrator/skills/ai-native-tech-plan/assets/review-checklist.md`

**Implementation**
- [x] Create the skill with trigger metadata for technical plans, implementation plans, architecture plans, workflow plans, Codex execution plans, and anti-MVP planning requests.
- [x] Keep SKILL.md concise and move longer reusable templates into references/assets.
- [x] Document how to combine AI-native planning with Superpowers, GSD, and OpenSpec.

**Tests**
- [x] Update skill inventory tests.

**Validation Commands**
```bash
python3 -m unittest dev.plugins.codex-project-orchestrator.tests.test_project_orchestrator.ProjectOrchestratorTests.test_all_expected_skills_have_codex_frontmatter
```

**Done When**
- [x] Skill files exist and pass frontmatter/inventory tests.

**Risks / Rollback**
- Avoid bloating SKILL.md; use progressive disclosure for templates.

### Slice 3: Update scaffold templates and routing skills

**Status:** done

**Goal**
- Make AI-native planning the default generated workflow behavior.

**Files / Modules**
- `dev/plugins/codex-project-orchestrator/assets/templates/AGENTS.md.template`
- `dev/plugins/codex-project-orchestrator/assets/templates/ROADMAP.md.template`
- `dev/plugins/codex-project-orchestrator/assets/templates/PHASE_PLAN.md.template`
- `dev/plugins/codex-project-orchestrator/assets/templates/OPENSPEC_DESIGN.md.template`
- `dev/plugins/codex-project-orchestrator/assets/templates/OPENSPEC_TASKS.md.template`
- `dev/plugins/codex-project-orchestrator/skills/project-orchestrator/SKILL.md`
- `dev/plugins/codex-project-orchestrator/skills/feature-intake/SKILL.md`
- `dev/plugins/codex-project-orchestrator/skills/change-plan/SKILL.md`
- `dev/plugins/codex-project-orchestrator/skills/execute-task/SKILL.md`
- `dev/plugins/codex-project-orchestrator/skills/verify-and-archive/SKILL.md`

**Implementation**
- [x] Add AI Coding Planning Rules to generated AGENTS.md.
- [x] Replace setup and greenfield scaffold wording that treats MVP as a default.
- [x] Add Target State, Completion Contract, Capability Slices, Execution Ledger, Acceptance Criteria, Validation Commands, and Final Verification sections to OpenSpec templates.
- [x] Add routing rules that call `ai-native-tech-plan` for plan-generation requests and keep OpenSpec for behavior-level artifacts.
- [x] Require execution and verification skills to read/update ledgers and completion contracts.

**Tests**
- [x] Update scaffold and skill dependency tests.

**Validation Commands**
```bash
python3 -m unittest dev.plugins.codex-project-orchestrator.tests.test_project_orchestrator.ProjectOrchestratorTests.test_scaffold_dry_run_and_greenfield_apply
python3 -m unittest dev.plugins.codex-project-orchestrator.tests.test_project_orchestrator.ProjectOrchestratorTests.test_orchestrator_skills_name_dependency_skills_explicitly
```

**Done When**
- [x] Generated scaffolds and skill routes use AI-native planning language by default.

**Risks / Rollback**
- Preserve GSD phase terminology only for governance and checkpoint sequencing.

### Slice 4: Add plan lint tooling

**Status:** done

**Goal**
- Provide deterministic validation for generated AI-native plans.

**Files / Modules**
- `dev/plugins/codex-project-orchestrator/scripts/lint_ai_plan.py`
- `dev/plugins/codex-project-orchestrator/tests/test_project_orchestrator.py`

**Implementation**
- [x] Add forbidden term detection for MVP, numbered phases, future-work buckets, calendar estimates, sprint/person-day terms, and Chinese equivalents.
- [x] Add required section checks.
- [x] Support `<!-- ai-native-plan-lint: allow-human-planning-terms -->` for docs that discuss anti-patterns.
- [x] Return exit code `1` on lint failure and `0` on pass.

**Tests**
- [x] Add direct CLI tests with temporary plan files.

**Validation Commands**
```bash
python3 -m unittest dev.plugins.codex-project-orchestrator.tests.test_project_orchestrator.ProjectOrchestratorTests.test_lint_ai_plan_flags_human_planning_terms
```

**Done When**
- [x] Lint fails and passes for the expected fixtures.

**Risks / Rollback**
- Do not run this lint over policy docs unless they intentionally use the allow marker.

### Slice 5: Sync release copy, docs, state, and verification

**Status:** done

**Goal**
- Ship the same capability in the distributable plugin and record evidence.

**Files / Modules**
- `plugins/codex-project-orchestrator/**`
- `dev/plugins/codex-project-orchestrator/README.md`
- `dev/plugins/codex-project-orchestrator/.planning/STATE.md`
- `dev/plugins/codex-project-orchestrator/.planning/verification/*.md`

**Implementation**
- [x] Copy changed runtime plugin files from `dev/plugins/codex-project-orchestrator` to `plugins/codex-project-orchestrator`.
- [x] Update README with AI-native planning usage and lint examples.
- [x] Mark completed OpenSpec tasks.
- [x] Update workflow state.
- [x] Record verification evidence.

**Tests**
- [x] Run full plugin unittest suite.

**Validation Commands**
```bash
python3 -m unittest discover -s dev/plugins/codex-project-orchestrator/tests
python3 dev/plugins/codex-project-orchestrator/scripts/record_verification.py --repo dev/plugins/codex-project-orchestrator --command "python3 -m unittest discover -s dev/plugins/codex-project-orchestrator/tests" --result pass --json
```

**Done When**
- [x] Development and release plugin copies contain the same runtime changes.
- [x] Full tests pass and evidence is recorded.

**Risks / Rollback**
- Keep tests/fixtures/dev-only OpenSpec files out of the release copy.
