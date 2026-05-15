# Codex-First 2D Game Art Plugin Design

Date: 2026-05-15

## Decision

Package the broader AI-first 2D game art workflow as a Codex Plugin. Keep the
existing `godot-ai-2d-skeletal-animation` skill as the validated
skeletal-animation core, then migrate or mirror it into the Plugin after the
Plugin scaffold exists.

The Plugin is the product boundary. Individual skills inside the Plugin stay
small and task-focused.

## Goals

- Provide one Codex-first entrypoint for 2D game art asset production.
- Cover static 2D art, reference art, semantic part splitting, cutout skeletal
  animation, and Godot import/QA.
- Preserve the current deterministic Godot validation workflow for skeletal
  animation.
- Share artifact contracts, prompt patterns, schemas, and validation rules
  across the Plugin skills.
- Keep image-provider integration thin and replaceable.

## Non-Goals

- Do not turn the current skeletal-animation skill into a large general art
  production skill.
- Do not require a Godot EditorPlugin before the Codex Plugin workflow works.
- Do not promise a single image provider as the durable API contract.
- Do not replace human or agent visual QA for art suitability with file-level
  validators alone.
- Do not pollute `skill/` with Plugin evaluation artifacts, image-provider logs,
  rejected generations, `.godot/`, or `*.import` files.

## Plugin Shape

Target scaffold:

```text
/Users/cY/dev/godot-ai-2d-skeletal-animation/
  plugins/
    codex-2d-game-art/
      .codex-plugin/
        plugin.json
      skills/
        ai-2d-static-art/
          SKILL.md
        ai-2d-reference-art/
          SKILL.md
        ai-2d-part-splitting/
          SKILL.md
        godot-2d-skeletal-animation/
          SKILL.md
        godot-2d-art-import-qa/
          SKILL.md
      shared/
        references/
          artifact-contract.md
          routing.md
          prompt-patterns.md
        schemas/
          asset_pack.schema.json
      scripts/
        validate_plugin_layout.py
      assets/
  .agents/
    plugins/
      marketplace.json
```

## Skill Responsibilities

`ai-2d-static-art` generates static assets such as props, icons, tiles, simple
background elements, and UI game-art pieces. It should output local PNGs plus a
short provenance note and should not promise animation-ready rig data.

`ai-2d-reference-art` generates or refines riggable reference images. It owns
pose, camera, padding, silhouette clarity, background, and style constraints.

`ai-2d-part-splitting` turns a reference image into semantic transparent parts.
It rejects hard rectangular crops when semantic part extraction is required.

`godot-2d-skeletal-animation` is the current validated skill capability:
`rig_meta.json`, `motion.json`, Godot cutout rig generation, and animation QA.

`godot-2d-art-import-qa` validates asset-pack layout, Godot import behavior, QA
reports, previews, and project cleanliness.

## Artifact Contract

The Plugin should use an asset-pack folder as the durable handoff between
skills:

```text
asset_pack/
  asset_pack.json
  design_brief.md
  static/
  reference/
    reference_prompt.txt
    reference.png
  parts/
  rig/
    rig_meta.json
  motions/
  godot/
    generated/
    qa_report.json
```

The exact files may vary by workflow, but every workflow should make clear which
phase owns each artifact and which downstream phase can consume it.

## Routing Rules

- Concept-only requests start in `ai-2d-static-art` or `ai-2d-reference-art`
  depending on whether animation is needed.
- Existing reference image requests start in `ai-2d-part-splitting` when parts
  are missing, or `godot-2d-skeletal-animation` when parts and metadata exist.
- Existing parts plus motion requirements start in `godot-2d-skeletal-animation`.
- Godot project cleanliness, generated scene checks, and QA summaries route to
  `godot-2d-art-import-qa`.

## Verification

For Plugin planning or docs-only changes:

```bash
./scripts/run_all_checks.py --skip-godot
./scripts/sync_skill.py --check-only
./scripts/context_status.sh
```

For skeletal-animation skill or fixture changes:

```bash
./scripts/run_all_checks.py
./scripts/sync_skill.py --check-only
```

For Plugin scaffold changes after `plugins/codex-2d-game-art/` exists:

```bash
python3 plugins/codex-2d-game-art/scripts/validate_plugin_layout.py
./scripts/run_all_checks.py --skip-godot
```

## Risks

The largest product risk is scope creep: static art, reference generation,
semantic splitting, animation data, and Godot QA are related but separable. The
Plugin should coordinate them without hiding each phase's acceptance gates.

The largest technical risk is non-deterministic image generation. Keep generated
art probes and provider logs outside final skill folders, and use deterministic
fixtures for repeatable validation.

## Next Step

Use the implementation plan at
`docs/superpowers/plans/2026-05-15-codex-first-2d-game-art-plugin.md` to scaffold
the Plugin, migrate the skeletal-animation core, add focused skill shells, and
introduce Plugin-level validation.
