---
status: codex-first-plugin-roadmap-planned
branch: none
timestamp: 2026-05-15T19:48:36+08:00
workspace: /Users/cY/dev/godot-ai-2d-skeletal-animation
skill_source: /Users/cY/dev/godot-ai-2d-skeletal-animation/skill
skill_sync_target: /Users/cY/dev/skills/godot-ai-2d-skeletal-animation
---

## Context Checkpoint

Skill sync state: in sync

## QA Summary

```text
/Users/cY/dev/godot-ai-2d-skeletal-animation/skill/fixtures/godot_demo_project/fixtures/cases/case_01_humanoid_adventurer/qa_report.json critical=0 warning=0 info=6
/Users/cY/dev/godot-ai-2d-skeletal-animation/skill/fixtures/godot_demo_project/fixtures/cases/case_02_weapon_swordsman/qa_report.json critical=0 warning=0 info=6
/Users/cY/dev/godot-ai-2d-skeletal-animation/skill/fixtures/godot_demo_project/fixtures/cases/case_03_quadruped_beast/qa_report.json critical=0 warning=0 info=6
/Users/cY/dev/godot-ai-2d-skeletal-animation/skill/fixtures/godot_demo_project/fixtures/cases/case_04_mechanical_trap/qa_report.json critical=0 warning=0 info=6
```

## Snapshot Source

Project-local snapshot: /Users/cY/dev/godot-ai-2d-skeletal-animation/CONTEXT_SNAPSHOT.md

## Current Snapshot Excerpt

---
status: codex-first-plugin-roadmap-planned
branch: none
timestamp: 2026-05-15T15:55:03+08:00
workspace: /Users/cY/dev/godot-ai-2d-skeletal-animation
skill_source: /Users/cY/dev/godot-ai-2d-skeletal-animation/skill
skill_sync_target: /Users/cY/dev/skills/godot-ai-2d-skeletal-animation
latest_checkpoint: /Users/cY/.gstack/projects/godot-ai-2d-skeletal-animation/checkpoints/20260515-155503-godot-ai-2d-skeletal-animation-context.md
---

## Working On

Codex-first AI 2D game art pipeline, with the current Godot 2D skeletal
animation skill as its verified core.

This project currently contains a reusable Codex skill for Godot 4.x 2D
skeletal animation generation and validation. The next product direction is a
unified Codex Plugin for AI-first 2D game art generation: static art, reference
art, semantic part splitting, cutout skeletal animation, and Godot import/QA.
The existing skill remains the skeletal-animation core of that larger Plugin.

## Current Status

V1 of the skeletal-animation skill is complete and synced. The AI reference and
part-splitting probe is validated. The current planning pass records the V2
decision to wrap the broader 2D game art workflow as a Codex Plugin instead of
continuing to expand one large skill.

- The skill structure is valid.
- The canonical source is `skill/`.
- The installed/discoverable copy is `/Users/cY/dev/skills/godot-ai-2d-skeletal-animation`.
- `skill/` currently matches the installed copy.
- Four P0 fixture cases generate Godot scenes.
- All four QA reports have `critical=0`, `warning=0`, `info=6`.
- Negative fixtures fail for the expected reasons.
- `scripts/run_all_checks.py` now verifies QA report integrity after summary generation.
- `skill/tests/test_validators.py` directly covers the bundled rig and motion validators.
- `validate_rig_meta.py` and `validate_motion.py` are split into smaller validation helpers.
- The skill now documents AI-friendly reference prompts and semantic part splitting before rig metadata.
- A real GPT Image API probe now exists under
  `log/ai_pipeline_probe/case_01_ai_humanoid/`: reference generation, image-edit
  part sheet, cropped transparent parts, `rig_meta.json`, three motions, Godot
  scene generation/load validation, and `qa_report.json`.
- The first AI split passed file validators but failed manual visual QA because
  `torso` and `pelvis` looked like hard crops. V2 was regenerated with stricter
  semantic extraction instructions and promoted to the current `part_sheet.png`
  and `parts/*.png`; V1 is preserved as `part_sheet_v1_failed.png` and
  `parts_v1_failed/`.
- The AI probe QA summary is `critical=0`, `warning=0`, `info=6`.
- The V2 package decision is now: Codex Plugin as the unified product wrapper;
  the current skill becomes the Plugin's Godot cutout skeletal-animation core.
- New planning artifacts:
  - `docs/superpowers/specs/2026-05-15-codex-first-2d-game-art-plugin-design.md`
  - `docs/superpowers/plans/2026-05-15-codex-first-2d-game-art-plugin.md`
- The workspace is still not a git repository, so there is no branch, commit history, or git diff.

## Project Shape

```text
/Users/cY/dev/godot-ai-2d-skeletal-animation/
  AGENTS.md
  PROJECT_CONTEXT.md
  CONTEXT_SNAPSHOT.md
  VERIFICATION.md
  docs/
    superpowers/
      specs/
        2026-05-15-real-ai-reference-generation-design.md
        2026-05-15-codex-first-2d-game-art-plugin-design.md
      plans/
        2026-05-15-codex-first-2d-game-art-plugin.md
  scripts/
    context_status.sh
    context_checkpoint.sh
    run_all_checks.py
    sync_skill.py
  tests/
    test_run_all_checks.py
    test_sync_skill.py
  skill/
    SKILL.md
    agents/openai.yaml
    assets/
      rig_meta.schema.json
      motion.schema.json
      qa_report.schema.json
    references/
      pipeline.md
      ai-reference-and-part-splitting.md
      schemas.md
      godot-tool-contract.md
      qa-rules.md
      test-fixtures.md
    scripts/
      generate_fixture_assets.py
      validate_rig_meta.py
      validate_motion.py
      summarize_animation_qa.py
    tests/
      test_validators.py
    fixtures/godot_demo_project/
      project.godot
      main.tscn
      tools/
        build_ai_2d_rig.gd
        check_generated_scenes.gd
        demo_event_receiver.gd
      fixtures/cases/
      fixtures/negative_cases/
```

There is no project-local `checkpoints/` directory. The latest checkpoint for
this work is stored by gstack at the `latest_checkpoint` path in the frontmatter.

## Decisions Made

- V1 is a Codex skill plus deterministic Godot fixture, not a Godot EditorPlugin.
- V2 should be packaged as a Codex Plugin because the desired scope is now a
  unified AI-first 2D game art workflow, not only one skeletal-animation task.
- The Plugin should contain focused skills for static art, reference art,
  semantic part splitting, Godot cutout skeletal animation, and Godot import/QA.
- The current `skill/` should be preserved as the skeletal-animation core and
  migrated into the Plugin after a scaffold exists.
- AI reference-image generation is allowed when constrained to riggability and
  reference-to-part splitting. Provider-specific image API plumbing should stay
  thin and replaceable.
- Open-ended commercial art direction belongs in the future Plugin boundary,
  not in the current skeletal-animation skill.
- Fixture art is deterministic/programmatic so validation remains reproducible.
- Runtime scene generation is headless through `tools/build_ai_2d_rig.gd`.
- Scene load validation is separate through `tools/check_generated_scenes.gd`.
- The Godot strategy is cutout-first: `Sprite2D` parts attached to `Bone2D` nodes under `Skeleton2D`.
- Python validators use only the standard library, including a small PNG header parser.
- Data contracts are `rig_meta.json`, `motion.json`, and `qa_report.json`.
- QA report paths should be generated from inside `skill/` so the reports stay relative and portable.
- Project-level agent/context instructions now live in `AGENTS.md`.
- Context status and checkpoint helpers now live in `scripts/context_status.sh` and `scripts/context_checkpoint.sh`.
- Full verification now lives in `scripts/run_all_checks.py`; it uses a temporary Godot fixture copy by default.
- Full verification now includes QA report integrity checks for summary counts and portable artifact paths.
- Skill sync now lives in `scripts/sync_skill.py`; `--check-only` verifies the canonical skill and installed skill match.
- Skill-local validator tests live in `skill/tests/test_validators.py` so quality checks see tests with the skill.

## Fixture Coverage

Positive P0 cases:

- `case_01_humanoid_adventurer`: humanoid rig, idle, run, basic attack.
- `case_02_weapon_swordsman`: weapon humanoid, weapon socket, slash socket, hitbox timing.
- `case_03_quadruped_beast`: quadruped skeleton, walk, bite hitbox, tail/spine motion.
- `case_04_mechanical_trap`: mechanical hinge/trap, armed/trigger states, hazard timing.

Negative cases:

- `missing_part`
- `bone_cycle`
- `pivot_out_of_bounds`
- `missing_bone_motion`
- `action_missing_event`

## Latest Verified State

Environment:

```text
Godot CLI: /opt/homebrew/bin/godot
Godot version: 4.6.2.stable.official.71f334935
```

Most recent synchronized checks:

```bash
python3 /Users/cY/dev/skills/skill-creator/scripts/quick_validate.py /Users/cY/dev/godot-ai-2d-skeletal-animation/skill
cd /Users/cY/dev/godot-ai-2d-skeletal-animation
python3 -m unittest tests/test_run_all_checks.py tests/test_sync_skill.py
cd /Users/cY/dev/godot-ai-2d-skeletal-animation/skill
python3 -m unittest tests/test_validators.py
cd /Users/cY/dev/godot-ai-2d-skeletal-animation
./scripts/run_all_checks.py
```
