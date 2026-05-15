# Pipeline

This skill turns AI/reference art into Godot 4.x cutout skeletal animation
fixtures by constraining reference art, splitting it into transparent parts, and
then validating rig and motion data.

## Inputs

Expected case folder:

```text
case_id/
  reference.png
  design_brief.md
  part_sheet.png        # optional intermediate for AI/manual splitting
  parts/*.png
  rig_meta.json
  motions/*.json
```

`reference.png` may be hand-made or AI-generated. If it is generated, constrain
the prompt for riggability before style polish. `part_sheet.png` is optional;
the required rigging output is the final named transparent PNGs in `parts/`.

## Steps

1. Inspect the object type and available art inputs.
2. If needed, write an AI reference prompt with riggable pose, framing, and background constraints.
3. Split the reference into named transparent `parts/*.png`; use an optional labeled part sheet only as an intermediate.
4. Choose the smallest rig family that fits: humanoid, weapon humanoid, quadruped, mechanical, or custom.
5. Define bones with one root, explicit parents, local positions, and optional rest rotations.
6. Bind each transparent PNG part to one bone with `pivot`, `offset`, and `z_index`.
7. Add sockets for weapons, effects, bite points, hinges, trigger zones, and hitbox anchors.
8. Define motions with `idle`, `move`, and `action` categories.
9. Validate rig metadata and motions before opening Godot.
10. Generate a Godot scene and `AnimationPlayer` clips.
11. Summarize QA and attach preview artifacts.

## Godot Strategy

Use a cutout-first rig:

```text
Node2D
├── Skeleton2D
│   └── Bone2D...
├── AnimationPlayer
└── Hitboxes / sockets / markers
```

Sprites may be attached under their controlling `Bone2D`. Keep collision, hitboxes, and effects as separate marker-driven systems instead of baking gameplay logic into art nodes.

## Done

A case is done when split parts pass visual acceptance, schema validation
passes, Godot can build and load a scene, the preview is non-empty, and
`qa_report.json` has zero critical issues.
