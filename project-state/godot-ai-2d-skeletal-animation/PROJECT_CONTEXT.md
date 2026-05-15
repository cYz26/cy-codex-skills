# Godot AI 2D Game Art Project Context

## Goal

Build a Codex-first 2D game art generation workflow for Godot projects. The
current verified core is a reusable Codex skill for generating and validating
Godot 4.x 2D skeletal animation assets from AI/reference images,
reference-to-part splitting, part PNGs, and motion requirements.

The V2 direction is to package the broader workflow as a Codex Plugin. The
Plugin will be the unified entrypoint for static art, reference art, semantic
part splitting, skeletal animation generation, and Godot import/QA. The current
`godot-ai-2d-skeletal-animation` skill remains the skeletal-animation core
inside that larger product boundary.

## Current Scope

- Create the skill under `skill/`.
- Provide AI reference-art constraints and semantic part-splitting guidance for
  Godot cutout rigs.
- Provide JSON contracts for `rig_meta.json`, `motion.json`, and `qa_report.json`.
- Provide validation scripts for rig metadata, motion data, and QA summary.
- Provide a Godot demo fixture with four P0 cases:
  - `case_01_humanoid_adventurer`
  - `case_02_weapon_swordsman`
  - `case_03_quadruped_beast`
  - `case_04_mechanical_trap`
- Prove the fixture with Python validation and Godot headless import/build/load.

## V2 Plugin Direction

- Use a Codex Plugin as the product wrapper for the complete AI-first 2D game
  art pipeline.
- Keep the existing skill stable and reusable instead of folding unrelated art
  generation concerns into one large skill.
- Split the Plugin into focused skills:
  - static 2D art generation
  - reference art generation
  - semantic part splitting
  - Godot cutout skeletal animation
  - Godot 2D art import and QA
- Share artifact contracts, schemas, prompt patterns, and validation scripts
  across those skills.
- Treat a future Godot EditorPlugin or dock UI as an optional frontend after the
  Codex Plugin workflow is stable.

## Out Of Scope For V1

- Open-ended reference art generation unrelated to riggable Godot assets.
- Commercial art production.
- External image provider integration.
- Godot editor dock/plugin UI.
- Production SAM/MediaPipe/OpenPose automation.
- Polygon2D mesh deform and complex IK.

## Project Layout

```text
/Users/cY/dev/godot-ai-2d-skeletal-animation/
  PROJECT_CONTEXT.md
  docs/
    superpowers/
      specs/
      plans/
  skill/
    SKILL.md
    agents/openai.yaml
    assets/
    references/
    scripts/
    fixtures/
```

## Sync Strategy

`skill/` is the canonical source during implementation. When validation passes, sync it to:

```text
/Users/cY/dev/skills/godot-ai-2d-skeletal-animation
```

This keeps project work isolated while still making the final skill available from the local skills directory.

The future Plugin should be scaffolded separately under `plugins/` or a sibling
workspace. Until that scaffold exists, `skill/` remains the canonical source for
the validated skeletal-animation capability.

## Local Environment

- Godot CLI: `/opt/homebrew/bin/godot`
- Godot version checked: `4.6.2.stable.official.71f334935`
- Workspace root for this project: `/Users/cY/dev/godot-ai-2d-skeletal-animation`
