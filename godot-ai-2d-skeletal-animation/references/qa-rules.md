# QA Rules

## Critical

- `rig_meta.json` is missing or invalid JSON.
- Required animated parts are missing after reference splitting.
- Split part PNG contains a baked background, sheet label, grid line, or unrelated neighboring art.
- More than one root bone or no root bone.
- Bone graph contains a cycle.
- Part file is missing or is not a PNG.
- Part pivot is outside image bounds.
- Motion references a missing bone or socket.
- Keyframe time is outside animation length.
- Action animation lacks required on/off events.
- Godot generated scene is missing after build.

## Warning

- AI reference art has heavy shadows, occlusion, cropped limbs, or perspective that makes splitting unreliable.
- Split part has too little transparent padding or joint overlap for clean rotation.
- Looping animation first and last key differ beyond tolerance.
- Part PNG lacks an alpha-capable color type.
- Motion has no events for non-action animations.
- Preview artifact is missing before final QA.

## Visual Acceptance

- Reference art is centered, complete, and readable as the same subject as the split parts.
- Split parts preserve style, palette, and scale from the reference.
- Upper/lower limbs, jaws, tails, weapons, hinges, and other independently animated pieces are not merged.
- Humanoid run or move: clear alternating limb motion.
- Weapon humanoid action: weapon socket remains attached; hitbox/fx events align with the swing.
- Quadruped move: front and rear legs alternate without obvious sliding.
- Mechanical action: hinge rotation is readable and active hazard timing is clear.

## Reporting

Do not mark a case ready if any critical issue remains. Include exact file paths in failure messages.
