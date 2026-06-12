# Godot AICoding Workflows

Use this file when implementing, fixing, optimizing, or exporting Godot projects.

## 0. Start Rule

1. Run read-only snapshot first (`scripts/godot_project_snapshot.sh`).
2. If change touches multiple systems, produce plan first using `references/05-plan-first.md`.
3. Apply DoD chain at the end (`fmt -> lint -> test or smoke`, plus Web gates when relevant).

## 1. Feature Workflow

1. Define boundary:
   - Clarify feature goal, acceptance criteria, and target scenes/scripts.
   - Clarify platform constraints (`Web`, `Mobile`, `Desktop`).
2. Map impact:
   - Locate related `*.tscn`, `*.gd`, `*.cs`, `*.tres`.
   - Check existing signals, autoloads, and scene ownership.
3. Design minimal change set:
   - Prefer extension over rewrite.
   - Split work into scene updates, script updates, and data/resource updates.
4. Implement:
   - Keep scene trees stable unless change is required.
   - Preserve serialization compatibility for saved resources.
5. Validate:
   - Parse/check project.
   - Run smoke flow for the affected gameplay loop.
   - Confirm no regressions in connected scenes.
6. Deliver:
   - Summarize changed files, behavior delta, and remaining risks.

## 2. Bug Workflow

1. Reproduce first:
   - Capture exact trigger steps and expected vs actual behavior.
   - Identify whether defect is editor-only, runtime-only, or platform-specific.
2. Classify error family:
   - Parse/type errors
   - Node path / scene tree mismatch
   - Signal connection/lifecycle mismatch
   - Physics/update-loop misuse
   - Resource loading/runtime packaging mismatch
3. Localize root cause:
   - Follow call path from trigger to failure.
   - Check recent edits in related nodes/resources.
4. Apply smallest corrective patch:
   - Avoid broad refactors during incident fix.
   - Add guards/assertions only where they prevent repeated failures.
5. Re-verify:
   - Confirm primary reproduction no longer fails.
   - Run at least one neighboring flow to catch collateral regressions.

## 3. Performance Workflow

1. Define bottleneck shape:
   - CPU simulation, render cost, memory churn, or loading stalls.
2. Isolate hot path:
   - Check node count growth, expensive loops, resource reloading patterns.
3. Optimize in order:
   - Remove waste (redundant work, duplicate lookups).
   - Reduce frequency (cache, batch, throttle).
   - Replace algorithm/data structure when needed.
4. Re-measure:
   - Compare before/after in the same scenario.
   - Record measurable wins and remaining bottlenecks.

## 4. Export Workflow

1. Confirm target preset exists in `export_presets.cfg`.
2. Check target requirements:
   - Web: threads decision, MIME/headers, cache/versioning, browser compatibility.
   - Mobile: permissions, rendering backend, package identifiers.
   - Desktop: dynamic libraries and runtime dependencies.
3. Run actual export command for affected target.
4. Inspect export log and first-launch behavior on target platform.
5. Document unresolved target-specific risks.

For Web specifics, load:
1. `references/10-threads-decision.md`
2. `references/20-server-headers.md`
3. `references/30-loading-cache-versioning.md`
4. `references/90-web-debug-playbook.md`

## Delivery Template

Use this output structure in final handoff:

1. Goal and scope
2. Files changed
3. Behavioral result
4. Validation executed
5. Residual risks / follow-up actions
