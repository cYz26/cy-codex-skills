# Design: Deprecate Agent Reach Update Planning

## Target State

DevFlow update tooling no longer treats Agent Reach as a maintained external updater. Running `codex_auto_update_plugins_skills.py` in dry-run mode or apply mode should not mention Agent Reach, should not call `pipx upgrade agent-reach`, and should not call `agent-reach check-update`.

Documentation should make the policy visible: Agent Reach is retained only as a deprecated local skill in this repository and is not recommended for new use.

## Scope / Non-Goals

- In scope: update script behavior, focused tests, and documentation labels.
- Non-goals: deleting the `agent-reach/` skill directory, uninstalling any global executable, editing user automations, or changing other external updater handling for Lark, GSD, or OpenSpec.

## Architecture Decisions

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| Remove Agent Reach from `run_external_updaters` entirely | Prevents both detection-plan noise and accidental apply updates. | Keep a skipped/deprecated report item, but that would still keep it in the update plan. |
| Mark deprecation in docs, not manifests | It is a repository policy decision for this skill, not a Codex runtime capability change. | Change skill frontmatter, which could affect routing in unrelated sessions. |
| Keep existing skill files in place | The user asked to remove update planning and mark not recommended, not to delete code. | Delete the skill, which would be broader and destructive. |

## Completion Contract

- [x] Focused tests fail before implementation when Agent Reach still appears in update results.
- [x] `run_external_updaters` never returns an `agent-reach` item, even if `agent-reach` and `pipx` are available.
- [x] The updater script no longer contains Agent Reach mutating or check-update commands.
- [x] README documentation marks Agent Reach as deprecated/not recommended.
- [x] Dev and release DevFlow script/test/doc copies stay synchronized.
- [x] OpenSpec validation and relevant tests pass.

## Capability Slices

### Slice 1: Regression tests

**Goal**
- Lock the updater policy so Agent Reach cannot re-enter dry-run or apply plans accidentally.

**Files / Modules**
- `dev/plugins/dev-flow/tests/test_dependencies.py`
- `plugins/dev-flow/tests/test_dependencies.py`

**Validation Commands**
```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_dependencies.py -k agent_reach
```

### Slice 2: Update policy implementation

**Goal**
- Remove Agent Reach detection and update commands from DevFlow updater scripts.

**Files / Modules**
- `dev/plugins/dev-flow/scripts/codex_auto_update_plugins_skills.py`
- `plugins/dev-flow/scripts/codex_auto_update_plugins_skills.py`
- `dev/scripts/codex_auto_update_plugins_skills.py`

**Validation Commands**
```bash
python3 -m unittest dev/plugins/dev-flow/tests/test_dependencies.py -k agent_reach
```

### Slice 3: Documentation and verification

**Goal**
- Make the deprecation visible to maintainers and verify the full relevant surface.

**Files / Modules**
- `README.md`
- `dev/scripts/README.md`
- `dev/plugins/dev-flow/README.md`
- `plugins/dev-flow/README.md`

**Validation Commands**
```bash
python3 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_dependencies.py'
python3 -m unittest discover -s plugins/dev-flow/tests -p 'test_dependencies.py'
openspec validate deprecate-agent-reach-updater --strict
```

## Compatibility

Existing Agent Reach files and user installations remain untouched. Users who explicitly run Agent Reach can still do so, but DevFlow no longer presents it as a maintained or recommended updater target.
