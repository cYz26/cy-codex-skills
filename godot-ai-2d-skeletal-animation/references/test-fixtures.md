# Test Fixtures

These fixtures validate the rigging and Godot checks. They use deterministic art
so validation is reproducible, but real skill usage may start from an AI
`reference.png` and a reference-to-parts splitting pass.

## P0 Cases

### `case_01_humanoid_adventurer`

Standard humanoid. Validates base skeleton, pivots, idle, move, and action.

### `case_02_weapon_swordsman`

Weapon humanoid. Validates weapon socket, slash effect socket, and hitbox event timing.

### `case_03_quadruped_beast`

Non-humanoid creature. Validates quadruped skeletons, walk cycles, bite hitbox anchors, and tail/spine motion.

### `case_04_mechanical_trap`

Animated scene object. Validates hinge pivots, trigger/action/reset motion, and hazard hitbox timing.

## Negative Cases

Include at least:

- Missing part file.
- Bone parent cycle.
- Motion references missing bone.
- Action motion lacks on/off events.
- Pivot outside image bounds.

## Fixture Art

Fixture art may be generated or programmatic. Prefer deterministic programmatic
fallback assets when validating the skill itself. For AI-generated examples,
preserve the accepted `reference.png`, optional `part_sheet.png`, and final
transparent `parts/*.png` so visual QA can compare reference intent to riggable
parts.
