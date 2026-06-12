# Godot Troubleshooting Checklists

Use this file during failure analysis, optimization, and export incident response.

## 1. Parse or Runtime Errors

1. Confirm engine major version compatibility (`3.x` vs `4.x` API differences).
2. Check first error in log, not only trailing cascaded errors.
3. Validate renamed APIs, signature changes, and typed variable mismatches.
4. Confirm resource paths exist and use `res://` consistently.

## 2. Scene and Node Wiring Failures

1. Confirm node paths still match current scene tree.
2. Confirm instanced scenes expose expected child nodes/scripts.
3. Confirm `@onready` variables are resolved after node enters tree.
4. Replace fragile `get_node("...")` with safer lookup if hierarchy is variable.

## 3. Signals and Lifecycle

1. Confirm signal name and argument list match emitter definition.
2. Confirm connection happens once (avoid duplicate connections).
3. Confirm emitter and listener lifecycle overlap as expected.
4. Confirm freed nodes are not still referenced by callbacks.

## 4. Physics and Input Defects

1. Keep deterministic movement in `_physics_process`.
2. Confirm delta usage is not duplicated or omitted.
3. Confirm collision layers/masks are configured correctly.
4. Confirm input actions exist and are mapped in project settings.

## 5. Performance Regression

1. Check node/object count growth over time.
2. Check repeated allocation in hot loops.
3. Check redundant per-frame path lookup and resource loading.
4. Reduce update frequency for non-critical systems.
5. Verify batching opportunities and overdraw sources in rendering-heavy scenes.

## 6. Web Export Issues

1. Confirm `export_presets.cfg` target exists and points to intended output.
2. Confirm thread/extension settings match browser/runtime support.
3. Confirm compressed assets and initial payload size are acceptable.
4. Confirm browser console errors for wasm/script/resource load failures.

## 7. Mobile Export Issues

1. Confirm package/application identifiers and signing setup.
2. Confirm permissions and platform-specific feature flags.
3. Confirm renderer and texture settings match device class.
4. Confirm startup scene and assets are included in export bundle.

## 8. Release Readiness

1. Confirm deterministic repro for fixed critical defects.
2. Confirm at least one successful export per target platform.
3. Confirm startup path, save/load path, and core gameplay loop smoke tests.
4. Confirm known limitations are documented in handoff.
