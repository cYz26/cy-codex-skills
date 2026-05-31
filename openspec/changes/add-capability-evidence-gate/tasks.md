# Tasks: Add capability evidence gate to research skills

## Target State

DevFlow provides a reusable Capability Evidence Gate in research/planning skills. Agents route capability-sensitive work through authoritative/current confirmation, local implementation scan, solution comparison, and OpenSpec/test contract before implementation. The process lives in skills and OpenSpec templates, with only a brief AGENTS trigger.

## Completion Contract

- [x] `capability-research` skill exists in dev and release plugin roots.
- [x] Existing DevFlow planning skills route capability-sensitive work to it.
- [x] OpenSpec templates contain a Capability Evidence section.
- [x] Dependency activation includes the new skill.
- [x] Dev, release, OpenSpec, preflight, and installed-cache checks pass or have recorded blockers.
- [x] Workflow state and verification evidence are updated.

## Capability Slices

### Slice 1: Skill contract and routing

**Status:** done

**Goal**
- Add the reusable capability research gate and route relevant DevFlow planning paths through it.

**Files / Modules**
- `dev/plugins/dev-flow/skills/capability-research/SKILL.md`
- `plugins/dev-flow/skills/capability-research/SKILL.md`
- `dev/plugins/dev-flow/skills/project-orchestrator/SKILL.md`
- `dev/plugins/dev-flow/skills/feature-intake/SKILL.md`
- `dev/plugins/dev-flow/skills/change-plan/SKILL.md`
- `dev/plugins/dev-flow/skills/ai-native-tech-plan/SKILL.md`
- release skill copies under `plugins/dev-flow/skills/`
- `dev/plugins/dev-flow/tests/test_project_orchestrator.py`

**Implementation**
- [x] Create `capability-research` with triggers, evidence sequence, comparison rules, and anti-patterns.
- [x] Update routing text in `project-orchestrator`, `feature-intake`, `change-plan`, and `ai-native-tech-plan`.
- [x] Mirror skill changes to `plugins/dev-flow`.

**Tests**
- [x] Update tests so missing skill or routing text fails.

**Validation Commands**
```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py
```

**Done When**
- [x] Focused test passes and routing content is present in dev and release roots.

**Risks / Rollback**
- Revert this slice if the skill becomes a broad generic checklist instead of a concrete trigger-driven gate.

### Slice 2: Durable OpenSpec and AGENTS surfaces

**Status:** done

**Goal**
- Add durable evidence fields to planning artifacts without moving the full process into AGENTS.

**Files / Modules**
- `dev/plugins/dev-flow/assets/templates/OPENSPEC_PROPOSAL.md.template`
- `dev/plugins/dev-flow/assets/templates/OPENSPEC_DESIGN.md.template`
- `dev/plugins/dev-flow/assets/templates/OPENSPEC_TASKS.md.template`
- `dev/plugins/dev-flow/assets/templates/AGENTS.md.template`
- release template copies under `plugins/dev-flow/assets/templates/`
- `dev/plugins/dev-flow/tests/test_project_orchestrator.py`

**Implementation**
- [x] Add Capability Evidence sections to OpenSpec templates.
- [x] Add a concise AGENTS trigger that delegates details to `capability-research`.
- [x] Mirror template changes to `plugins/dev-flow`.

**Tests**
- [x] Update template assertions for the evidence section and AGENTS delegation.

**Validation Commands**
```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py
```

**Done When**
- [x] Focused tests pass and AGENTS does not contain the full four-step procedure.

**Risks / Rollback**
- Shorten AGENTS text if it starts duplicating skill procedure.

### Slice 3: Dependency activation, packaging, and verification

**Status:** done

**Goal**
- Prove the change is complete in dev, release, and installed-cache plugin roots.

**Files / Modules**
- `dev/plugins/dev-flow/scripts/workflow_dependency_catalog.py`
- `plugins/dev-flow/scripts/workflow_dependency_catalog.py`
- `plugins/dev-flow/tests/test_release_smoke.py`
- `.planning/STATE.md`
- `.planning/verification/`
- `openspec/changes/add-capability-evidence-gate/tasks.md`

**Implementation**
- [x] Add `capability-research` to project-local DevFlow dependency activation.
- [x] Update release smoke tests.
- [x] Record verification evidence.
- [x] Update workflow state and this ledger.

**Tests**
- [x] Run focused, full dev, release, OpenSpec, preflight, and cache verification commands.

**Validation Commands**
```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py
python3 -m unittest discover -s dev/plugins/dev-flow/tests
python3 -m unittest discover -s plugins/dev-flow/tests
openspec validate --all --strict
python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root dev/plugins/dev-flow --json
python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root plugins/dev-flow --json
```

**Done When**
- [x] Verification evidence exists, installed cache matches changed packaged files, and the Completion Contract is checked.

**Risks / Rollback**
- Keep archive blocked until verification evidence is recorded.

## Execution Ledger

| Slice | Status | Evidence |
|---|---|---|
| Skill contract and routing | done | `python3 -m unittest dev/plugins/dev-flow/tests/test_project_orchestrator.py -k capability` passed; `.planning/verification/20260530014921-python3--m-unittest-dev-plugins-dev-flow-tests-test_project_orch.md` |
| Durable OpenSpec and AGENTS surfaces | done | Focused template assertions passed with the capability tests; `.planning/verification/20260530014921-python3--m-unittest-dev-plugins-dev-flow-tests-test_project_orch.md` |
| Dependency activation, packaging, and verification | done | Dev tests, release tests, OpenSpec strict, preflight, installed-cache checks recorded under `.planning/verification/20260530014925-*` through `.planning/verification/20260530015002-*` |

## Acceptance Criteria

- [x] `capability-research` defines triggers, four-step evidence sequence, evidence ledger fields, and anti-patterns.
- [x] Planning skills route current/external/local capability uncertainty to the skill.
- [x] OpenSpec templates expose Capability Evidence fields.
- [x] AGENTS template only delegates to the skill.
- [x] Dev/release plugin roots and installed cache are synchronized.

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

- [x] Focused tests pass.
- [x] Broader tests, lint, typecheck, or build pass where applicable.
- [x] Verification evidence is recorded.
