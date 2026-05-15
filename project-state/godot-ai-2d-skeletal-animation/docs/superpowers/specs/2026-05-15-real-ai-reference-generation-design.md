# Real AI Reference Generation Design

Date: 2026-05-15

Status: Superseded for V2 packaging by
`docs/superpowers/specs/2026-05-15-codex-first-2d-game-art-plugin-design.md`.
This document remains useful as the historical V1.5 design for proving real AI
reference generation inside the current skeletal-animation skill. The current
product direction is to wrap the broader workflow as a Codex Plugin.

## Decision

Keep `godot-ai-2d-skeletal-animation` as one Codex skill and add a real AI
reference-image generation phase before the existing part-splitting, rigging,
motion, Godot build, and QA phases.

This was originally framed as a V1.5 expansion of the current skill. The V2
packaging decision now moves the broader workflow into a Plugin with separate
skills for reference art, part splitting, rigging, and motion QA.

## Goals

- Let the skill produce `reference.png` when the user starts from a concept and
  does not already have reference art.
- Keep existing workflows intact when the user provides `reference.png`,
  `part_sheet.png`, or `parts/*.png`.
- Preserve the Godot cutout-rig boundary: generated art must be optimized for
  riggability, not open-ended illustration.
- Keep provider-specific details thin and replaceable. The skill may call an
  available image tool, but the durable contract is the local artifact layout.

## Non-Goals

- Do not turn the skill into a general commercial art direction skill.
- Do not promise one specific image provider as the only supported backend.
- Do not include secrets, raw provider logs, failed temporary generations, or
  rejected masks in final case folders.
- Do not build a Godot EditorPlugin or dock UI in this phase.

## Workflow

1. Inspect the case folder for `design_brief.md`, `reference.png`,
   `part_sheet.png`, `parts/*.png`, `rig_meta.json`, and `motions/*.json`.
2. If `reference.png` is missing, generate `reference_prompt.txt` from the
   concept and the rig family target.
3. Call an available local image generation capability to save
   `reference.png` in the case folder.
4. Visually inspect `reference.png` against the riggability acceptance gate.
5. If it fails, revise `reference_prompt.txt` and regenerate, or ask the user
   whether to accept the risk.
6. Continue through the existing pipeline:
   `reference.png` -> optional `part_sheet.png` -> `parts/*.png` ->
   `rig_meta.json` -> `motions/*.json` -> generated Godot scene ->
   `qa_report.json`.

## Tool Strategy

When true image generation is needed, prefer the installed `gpt-image-api`
skill because it saves local PNG files directly. Use its CLI with an absolute
output path such as:

```bash
python3 /Users/cY/dev/skills/gpt-image-api/scripts/gpt_image.py generate \
  --prompt-file /absolute/path/reference_prompt.txt \
  --size 1024x1024 \
  --quality medium \
  --output /absolute/path/case_id/reference.png
```

If the image tool is unavailable, blocked, or missing credentials, the skill
must report the blocker and ask for either credentials or a user-provided
`reference.png`. It must not claim that reference generation completed.

## Artifact Contract

Final case folders may contain:

```text
case_id/
  design_brief.md
  reference_prompt.txt
  reference.png
  part_sheet.png
  parts/
  rig_meta.json
  motions/
  qa_report.json
```

Temporary generations, rejected outputs, masks, raw request payloads, and
provider diagnostics belong outside the final case folder, usually under a
project-local `log/` work area.

## Riggability Gate

Generated `reference.png` must be:

- Complete, centered, uncropped, and padded.
- Orthographic or near-orthographic.
- In a neutral rest pose with readable joints.
- Clear enough to split into semantic parts.
- Free of dramatic perspective, motion blur, heavy shadows, and occluding props
  unless those props are intended separate parts.
- On a transparent or plain flat background.

Failing this gate is a pipeline failure unless the user explicitly accepts the
risk for exploratory work.

## Skill Documentation Changes

- Update `SKILL.md` so the required workflow starts with an input mode:
  existing reference, generated reference, existing parts, or metadata/motion
  repair.
- Promote AI reference generation from prompt advice to a first-class optional
  phase.
- Update `references/ai-reference-and-part-splitting.md` with the generation
  command pattern, artifact rules, retry guidance, and acceptance gate.
- Keep detailed provider notes out of `SKILL.md`; point to the image-generation
  capability only when a real generation is needed.

## Validation

For documentation-only changes, run:

```bash
./scripts/run_all_checks.py --skip-godot
./scripts/sync_skill.py --check-only
```

For any later script or fixture change that affects generated assets, run the
full suite:

```bash
./scripts/run_all_checks.py
```

Before claiming a successful generated-reference workflow, prove it with a real
case folder containing `reference_prompt.txt`, `reference.png`, downstream
parts, valid rig metadata, valid motions, generated Godot scenes, and a
`qa_report.json` with `critical=0`.

## Open Risk

The current project has a successful AI pipeline probe, but the workflow still
depends on visual inspection for reference and part quality. This is acceptable
for V1.5 because the existing deterministic validators protect the Godot data
contracts, while visual art suitability remains a human or agent review gate.
