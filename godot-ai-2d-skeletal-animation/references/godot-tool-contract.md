# Godot Tool Contract

The v1 fixture uses a headless Godot script instead of an editor plugin.

## Required Behavior

The Godot script must:

1. Read cases under `res://fixtures/cases`.
2. Parse each `rig_meta.json`.
3. Create a scene with `Skeleton2D`, `Bone2D`, sprites, sockets, hitbox markers, and `AnimationPlayer`.
4. Parse `motions/*.json`.
5. Add animation tracks for bone rotation, position, and scale.
6. Add method tracks for motion events when possible.
7. Save generated scenes under each case's `generated/` folder.

## Commands

```bash
godot --headless --import --path fixtures/godot_demo_project
godot --headless --path fixtures/godot_demo_project --script tools/build_ai_2d_rig.gd
godot --headless --path fixtures/godot_demo_project --script tools/check_generated_scenes.gd
```

## Non-Goals

- No dock UI.
- No asset-store-ready addon packaging.
- No mesh-weight editing.
- No runtime combat controller.

## Compatibility

Target Godot 4.x. This fixture was created against Godot 4.6.2.
