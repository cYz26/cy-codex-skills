# AI Reference And Part Splitting

Use this reference when the user starts from an AI-generated concept, a single
`reference.png`, or a combined part sheet and wants Godot-ready cutout parts.

## Goal

Produce a folder of transparent PNG parts that can be bound to `Bone2D` nodes.
The split result is the source of truth for rigging; the reference image is only
used to preserve design intent.

## Case Folder

```text
case_id/
  design_brief.md
  reference.png
  part_sheet.png        # optional intermediate
  parts/
    head.png
    torso.png
    ...
  rig_meta.json
  motions/
```

Do not put provider logs, temporary masks, or rejected generations in the final
case folder. Keep those in a work directory until the selected parts are clean.

## AI Reference Constraints

Ask for art that is easy to split before asking for beauty:

- Full subject visible, centered, uncropped, with padding around all sides.
- Orthographic or near-orthographic view; avoid strong perspective and foreshortening.
- Neutral rest pose with readable joints. Humanoids can use a relaxed A-pose;
  quadrupeds should show all legs clearly; mechanical objects should expose hinges.
- Plain transparent or flat solid background.
- Clean silhouette, minimal motion blur, minimal cast shadows, no dramatic lighting.
- No important limb hidden behind another limb unless the hidden piece will never animate.
- Weapons, capes, tails, wings, armor plates, straps, and mechanical arms should be
  visually separable from the body.
- Consistent style, line weight, palette, and scale across the whole subject.
- Prefer 1024 px or larger on the longest side so small hands, feet, jaws, and
  sockets survive cropping.

Avoid prompts that request cinematic poses, painterly occlusion, complex scenery,
merged silhouettes, rim-lit shadows, or cropped portraits.

## Reference Prompt Template

```text
Create a 2D game character reference for Godot cutout skeletal animation:
[subject and style].
Full body, centered, uncropped, orthographic front/three-quarter view, neutral
rest pose, clear visible joints, separate readable limbs, plain transparent or
flat solid background, no motion blur, no dramatic shadows, no perspective
foreshortening, no overlapping props except [allowed exceptions].
Keep all parts easy to isolate for skeletal rigging: [expected parts].
```

## Split Prompt Template

Use an image edit/generation tool when available, or do it manually in an image
editor. The output can be a labeled `part_sheet.png` first, then individual
cropped PNGs under `parts/`.

```text
Using the input reference, create a Godot 2D cutout animation part sheet.
Preserve the same character design, colors, and style. Split the subject into
separate transparent-background parts arranged in a clean grid with no overlap:
[part ids].
Each part must be complete, isolated, centered in its own cell, with slight
joint overlap/bleed where it rotates under another part. Do not merge upper and
lower limbs. Do not include the background. Add small labels outside the part
art if a sheet is needed, but the final cropped PNG files must contain only art.
```

## Recommended Part Sets

Humanoid:

```text
head, neck_optional, torso, pelvis,
upper_arm_L, lower_arm_L, hand_L,
upper_arm_R, lower_arm_R, hand_R,
upper_leg_L, lower_leg_L, foot_L,
upper_leg_R, lower_leg_R, foot_R
```

Weapon humanoid:

```text
humanoid parts + weapon, shield_optional, cape_or_cloak_segments_optional,
slash_fx_optional
```

Quadruped:

```text
body, chest, neck, head, jaw_optional,
front_upper_leg_L, front_lower_leg_L, front_paw_L,
front_upper_leg_R, front_lower_leg_R, front_paw_R,
rear_upper_leg_L, rear_lower_leg_L, rear_paw_L,
rear_upper_leg_R, rear_lower_leg_R, rear_paw_R,
tail_base_optional, tail_mid_optional, tail_tip_optional
```

Mechanical:

```text
base, hinge_cap, swing_arm, blade_or_tool, gear_optional,
pressure_plate_optional, trigger_optional
```

Use stable lowercase snake-case or side-suffixed IDs. Match each `parts/*.png`
filename to the `parts[].id` in `rig_meta.json`.

## Split Acceptance Checklist

Before writing `rig_meta.json`, inspect every part:

- PNG has alpha and no baked background.
- One semantic part per file; no labels, grid lines, shadows, or neighboring parts.
- Pivot candidate lies inside the visible art or intended joint overlap.
- Rotating the part around the pivot would not reveal large holes.
- Left/right pairs have compatible scale and style.
- Hands, feet, weapons, jaws, tails, and hinges are separated if they need their own tracks.
- Z-order is visually recoverable from the reference.
- File names are stable and map directly to bone names or clear bindings.

If a part fails the checklist, regenerate or manually clean it before rigging.

## Common Failures

- Single reference images often have connected silhouettes; color-threshold or
  connected-component splitting is not enough for limb segmentation.
- AI may merge upper/lower limbs, crop feet, duplicate hands, or change costume
  details between reference and part sheet.
- Labeled sheets are useful for review but labels must not be present in final
  `parts/*.png`.
- Transparent outputs may still contain faint shadows or background halos; clean
  them before validation.
- Tiny parts with no padding are hard to pivot; add transparent padding around
  joints rather than scaling the art in Godot.

## Handoff To Rigging

After splitting:

1. Place accepted cropped PNGs in `parts/`.
2. Choose the smallest rig family that fits the part set.
3. Define bones and bind each part with `pivot`, `offset`, and `z_index`.
4. Run `scripts/validate_rig_meta.py` before opening Godot.
5. Keep the original `reference.png` and optional `part_sheet.png` for visual QA.
