---
name: godot-ai-2d-skeletal-animation
description: Use for Godot 4.x cutout rigs from AI/reference art, part splitting, rig metadata, or motion JSON. Covers AI art constraints, transparent part PNGs, Skeleton2D/Bone2D, AnimationPlayer tracks, sockets, hitboxes, QA reports, and headless fixture validation. Does not build editor UI.
---

# Godot AI 2D Skeletal Animation

## Overview

Use this skill to turn 2D game character/object concepts into a testable Godot
skeletal animation package: AI-friendly reference constraints, semantic part
splitting, data contracts, validation, scene generation, and visual QA for
cutout-style 2D rigs.

## Boundary

This skill can guide AI reference art generation and reference-to-part splitting
when the goal is a Godot cutout rig. Keep art direction constrained to riggable
asset requirements; do not treat it as a general commercial illustration skill.

Use it for:

- Writing AI reference-image constraints for riggable 2D cutout characters,
  creatures, weapons, props, traps, and scene objects.
- Splitting a `reference.png` or part sheet into named transparent `parts/*.png`
  assets suitable for Godot skeletal animation.
- Planning or generating `rig_meta.json` for Godot 2D cutout rigs.
- Planning or generating `motion.json` for `AnimationPlayer` tracks and events.
- Validating part PNGs, bones, sockets, hitbox anchors, and motion tracks.
- Building or checking a Godot headless demo fixture.
- Producing QA reports that separate critical failures from warnings.

Do not use it as the primary skill for:

- Open-ended commercial art direction unrelated to Godot rigging.
- Provider-specific image API integration beyond prompt/asset requirements.
- Building a Godot editor dock/plugin UI.
- Production SAM/MediaPipe/OpenPose automation.
- Polygon2D mesh-deformation weighting or advanced IK workflows.

## Required Workflow

1. **Inspect inputs**: find `reference.png`, `design_brief.md`, optional
   `part_sheet.png`, `parts/*.png`, `rig_meta.json`, and `motions/*.json`.
2. **Constrain reference art**: if using AI art, write prompts that produce a
   centered, complete, orthographic, easy-to-split subject. See
   `references/ai-reference-and-part-splitting.md`.
3. **Split into parts**: create named transparent PNGs under `parts/` for each
   independently animated limb, body segment, weapon, prop, or mechanical piece.
4. **Choose rig family**: humanoid, weapon humanoid, quadruped, mechanical, or
   the smallest explicit custom bone tree.
5. **Write or update metadata**: define bones, part bindings, pivots, sockets,
   and hitbox anchors in `rig_meta.json`.
6. **Write or update motions**: define length, loop flag, bone tracks, and
   required events in `motion.json`.
7. **Validate before Godot**: run `scripts/validate_rig_meta.py` and `scripts/validate_motion.py`.
8. **Build the demo scene**: use the project's Godot headless script or the bundled fixture pattern.
9. **Summarize QA**: run `scripts/summarize_animation_qa.py` and report
   critical issues, warnings, generated scenes, and preview outputs.

## Acceptance Defaults

- Treat `critical > 0` in `qa_report.json` as not shippable.
- Attack or trigger animations must include on/off events such as `hitbox_on`/`hitbox_off` or `hazard_on`/`hazard_off`.
- Looping animations must return to their first key pose within the configured tolerance.
- AI reference art must be complete, centered, uncropped, and free of extreme
  perspective, motion blur, heavy shadows, and occluding props unless those
  elements are intentionally split as separate parts.
- Split parts must be isolated transparent PNGs with no baked background, no
  unrelated neighboring pixels, and enough overlap/bleed around joints to rotate
  without exposing gaps.
- Parts must be transparent PNGs with pivots inside image bounds.
- Bone parent graphs must have exactly one root and no cycles.

## Bundled Scripts

- `scripts/validate_rig_meta.py`: validates `rig_meta.json` and part PNGs.
- `scripts/validate_motion.py`: validates one or more motion files against a rig.
- `scripts/summarize_animation_qa.py`: writes per-case `qa_report.json` files.
- `scripts/generate_fixture_assets.py`: creates deterministic test fixtures.
  Use for validation, not as a production art pipeline.

## Reference Map

- `references/pipeline.md`: end-to-end Godot skeletal animation workflow.
- `references/ai-reference-and-part-splitting.md`: AI reference constraints,
  part-splitting prompts, naming, and visual acceptance checklist.
- `references/schemas.md`: field-level contract for rig, motion, and QA data.
- `references/godot-tool-contract.md`: expected Godot project and headless build behavior.
- `references/qa-rules.md`: automated and visual acceptance rules.
- `references/test-fixtures.md`: P0 fixture cases and test-only art notes.

## Minimal Commands

```bash
python3 scripts/validate_rig_meta.py \
  fixtures/godot_demo_project/fixtures/cases/case_01_humanoid_adventurer/rig_meta.json
python3 scripts/validate_motion.py \
  fixtures/godot_demo_project/fixtures/cases/case_01_humanoid_adventurer/motions/*.json
python3 scripts/summarize_animation_qa.py fixtures/godot_demo_project/fixtures/cases
godot --headless --import --path fixtures/godot_demo_project
godot --headless --path fixtures/godot_demo_project --script tools/build_ai_2d_rig.gd
godot --headless --path fixtures/godot_demo_project --script tools/check_generated_scenes.gd
```

## Reporting

When finished, report:

- Which cases passed validation.
- Which Godot scenes were generated.
- Any critical QA failures and exact file paths.
- Preview paths or the reason preview generation was skipped.
