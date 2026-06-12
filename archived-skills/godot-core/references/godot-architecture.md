# Godot Architecture Patterns (Godot 4)

Load this file when planning or refactoring project structure.

## Scene Composition

1. Keep one responsibility per scene root.
2. Keep reusable behavior in component-like child nodes or scripts.
3. Prefer explicit ownership boundaries:
   - UI scene
   - Gameplay scene
   - Shared systems (autoload/services)
4. Avoid deep hard-coded node path dependencies across sibling branches.

## Script Design

1. Keep public script API typed and stable.
2. Keep data definition separate from runtime orchestration where possible.
3. Use signals for cross-node communication instead of direct tree crawling.
4. Keep frame-loop logic deterministic:
   - `_physics_process` for simulation and motion
   - `_process` for visual updates
5. Guard optional dependencies (`get_node_or_null`, defensive checks).

## State and Events

1. Use explicit state transitions for gameplay modes.
2. Emit domain events from producers and subscribe in consumers.
3. Avoid hidden side effects in setters and lifecycle callbacks.
4. Keep autoloads focused on globally shared services, not feature logic dumps.

## Resource Strategy

1. Distinguish static resources from runtime-instanced data.
2. Avoid repeated `load()` in hot loops; cache references.
3. Keep large assets lazy-loaded or streamed where possible.
4. Preserve compatibility when editing serialized `.tres` / `.res` assets.

## C# Interop Notes

1. Keep C# project files aligned with Godot editor-generated expectations.
2. Minimize mixed-language coupling unless required by external libraries.
3. Keep script naming and class naming consistent with scene attachment usage.

## Safe Refactor Sequence

1. Snapshot affected files.
2. Move one boundary at a time (scene, then script, then wiring).
3. Re-open/parse scene in editor or headless checks after each boundary move.
4. Run smoke flow before continuing with next refactor step.
