# Design: Add capability evidence gate to research skills

## Target State

DevFlow gains a reusable Capability Evidence Gate for research-heavy or capability-sensitive work. Agents use it when an answer or implementation depends on current external capabilities, platform behavior, plugin/tool availability, official documentation, hook/event semantics, installed-cache state, or any local-vs-platform ambiguity. The gate requires evidence before implementation:

1. Confirm authoritative/current capability from official or primary sources when the capability can drift.
2. Scan local implementation, installed cache, config, scripts, tests, and repo artifacts.
3. Compare official capability, local state, and fallback options, explicitly marking assumptions.
4. Persist the chosen behavior and validation surface in OpenSpec artifacts before implementation.

The detailed procedure lives in a new `capability-research` skill. Existing DevFlow skills route to it. OpenSpec templates add a durable evidence section. Generated AGENTS guidance remains a short trigger and does not become the procedure source of truth.

## Scope / Non-Goals

- In scope: DevFlow skills, OpenSpec templates, dependency skill catalog, release copy, and tests.
- In scope: a short AGENTS template trigger that delegates detail to the skill.
- Non-goals: new dependencies, automated documentation crawlers, runtime research scripts, or broad AGENTS rewrite.

## Architecture Decisions

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| Add a dedicated `capability-research` skill | Keeps the reusable process discoverable and avoids scattering a long checklist through AGENTS. | Put the full process in AGENTS; too broad and hard to evolve. |
| Route from existing planning skills | Keeps research as part of intake/design rather than an implementation afterthought. | Require users to name the skill manually; too easy to miss. |
| Add evidence sections to OpenSpec templates | Makes the result durable across compaction and review. | Keep evidence only in chat; repeats the original failure mode. |
| Keep AGENTS minimal | Gives agents a trigger without making AGENTS the operational source. | No AGENTS mention; lower discoverability in generated projects. |

## Completion Contract

- [ ] Development and release plugin roots contain the same `capability-research` skill.
- [ ] `project-orchestrator`, `feature-intake`, `change-plan`, and `ai-native-tech-plan` route capability-sensitive work to the skill.
- [ ] Dependency activation installs the new DevFlow project-local skill.
- [ ] OpenSpec proposal/design/tasks templates include capability evidence prompts.
- [ ] Tests fail without the new skill/template/routing content and pass after implementation.
- [ ] Installed cache is refreshed and verified because packaged plugin files changed.

## Capability Slices

### Slice 1: Research skill and routing

**Goal**
- Add the reusable gate and route capability-sensitive work to it.

**Files / Modules**
- `dev/plugins/dev-flow/skills/capability-research/SKILL.md`
- `dev/plugins/dev-flow/skills/project-orchestrator/SKILL.md`
- `dev/plugins/dev-flow/skills/feature-intake/SKILL.md`
- `dev/plugins/dev-flow/skills/change-plan/SKILL.md`
- `dev/plugins/dev-flow/skills/ai-native-tech-plan/SKILL.md`
- release copies under `plugins/dev-flow/`

**Implementation**
- [ ] Create the skill with explicit triggers, procedure, evidence ledger, and anti-patterns.
- [ ] Update routing text in existing skills.

**Tests**
- [ ] Update skill packaging and routing tests.

**Validation Commands**
```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py
```

**Done When**
- [ ] The focused test passes and release copies match.

**Risks / Rollback**
- Revert routing text and the new skill if it causes dependency activation or packaging regressions.

### Slice 2: Durable OpenSpec evidence surface

**Goal**
- Ensure future changes have a place to record capability evidence before implementation.

**Files / Modules**
- `dev/plugins/dev-flow/assets/templates/OPENSPEC_PROPOSAL.md.template`
- `dev/plugins/dev-flow/assets/templates/OPENSPEC_DESIGN.md.template`
- `dev/plugins/dev-flow/assets/templates/OPENSPEC_TASKS.md.template`
- `dev/plugins/dev-flow/assets/templates/AGENTS.md.template`
- release copies under `plugins/dev-flow/`

**Implementation**
- [ ] Add concise Capability Evidence sections to proposal/design/tasks templates.
- [ ] Add only a lightweight AGENTS trigger that routes to `capability-research`.

**Tests**
- [ ] Update template tests to assert the evidence section and minimal AGENTS delegation.

**Validation Commands**
```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py
```

**Done When**
- [ ] Generated templates include the evidence surface without embedding a long research procedure in AGENTS.

**Risks / Rollback**
- Remove or shorten AGENTS wording if tests or review show the procedural detail migrated there.

### Slice 3: Packaging, dependency activation, and installed-cache verification

**Goal**
- Package the new skill consistently and prove Codex can load the updated plugin.

**Files / Modules**
- `dev/plugins/dev-flow/scripts/workflow_dependency_catalog.py`
- `plugins/dev-flow/scripts/workflow_dependency_catalog.py`
- `dev/plugins/dev-flow/tests/test_project_orchestrator.py`
- `plugins/dev-flow/tests/test_release_smoke.py`

**Implementation**
- [ ] Add `capability-research` to DevFlow project-local activation.
- [ ] Update release smoke coverage.
- [ ] Refresh installed DevFlow plugin cache.

**Tests**
- [ ] Run dev and release tests, preflight, OpenSpec validation, and cache checks.

**Validation Commands**
```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py
python3 -m unittest discover -s dev/plugins/dev-flow/tests
python3 -m unittest discover -s plugins/dev-flow/tests
openspec validate --all --strict
python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root dev/plugins/dev-flow --json
python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root plugins/dev-flow --json
codex plugin add dev-flow@cy-codex-skills
```

**Done When**
- [ ] Tests and preflights pass, and cached skill/template files match source hashes.

## Execution Ledger

Track slice status in `tasks.md`, `.planning/STATE.md`, or a repo-specific ledger file. Mark a slice done only after its validation command passes or a blocker is recorded.

## Approach

Use a small documentation-and-routing change that follows the plugin's existing skill/template pattern. The new skill is procedural guidance, not executable code. Tests enforce packaging, routing, and template presence so the behavior is hard to drop from release builds.

## Data Flow

Capability evidence flows from the skill procedure into OpenSpec proposal/design/tasks and then into implementation decisions. For plugin verification, evidence also flows into `.planning/verification/` and installed-cache hash checks.

## Compatibility

No public plugin id, command name, hook event, state schema, or dependency changes are introduced. Existing DevFlow skills keep their current names and add only routing guidance.

## Testing

Use existing unittest coverage for plugin packaging, skill discovery, scaffold templates, and release smoke. Add assertions that fail if the new skill is missing, routing text is absent, OpenSpec templates lack a Capability Evidence section, or dependency activation omits the skill.

## Acceptance Criteria

- [ ] Capability-sensitive work has a documented skill route.
- [ ] Future OpenSpec changes can record authoritative/current evidence, local scan results, comparison, assumptions, and validation contract.
- [ ] Generated AGENTS guidance delegates to the skill rather than embedding the full procedure.
- [ ] Dev and release plugin roots are synchronized.
- [ ] Installed cache is refreshed and verified.

## Validation Commands

```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py
python3 -m unittest discover -s dev/plugins/dev-flow/tests
python3 -m unittest discover -s plugins/dev-flow/tests
openspec validate --all --strict
python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root dev/plugins/dev-flow --json
python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root plugins/dev-flow --json
```

## Final Verification

- [ ] Focused tests pass.
- [ ] Broader tests, lint, typecheck, or build pass where applicable.
- [ ] Verification evidence is recorded.
