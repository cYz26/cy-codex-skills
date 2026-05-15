# Codex-First 2D Game Art Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Codex Plugin that unifies AI-first 2D game art generation while preserving the current Godot 2D skeletal-animation skill as its validated core.

**Architecture:** Add a repo-local Plugin under `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/`. The Plugin contains focused skills for static art, reference art, semantic part splitting, skeletal animation, and Godot import/QA, with shared references and schemas for artifact contracts and routing.

**Tech Stack:** Codex Plugin manifest, Codex skills, Python 3 standard library validators, Godot 4.6 headless validation, existing `skill/` fixture suite, optional local image-generation capability.

---

## File Structure

- Create `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/.codex-plugin/plugin.json` for Plugin metadata.
- Create `/Users/cY/dev/godot-ai-2d-skeletal-animation/.agents/plugins/marketplace.json` for repo-local Plugin discovery metadata.
- Create `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/skills/ai-2d-static-art/SKILL.md` for static image asset generation.
- Create `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/skills/ai-2d-reference-art/SKILL.md` for riggable reference images.
- Create `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/skills/ai-2d-part-splitting/SKILL.md` for semantic transparent part extraction.
- Create `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/skills/godot-2d-skeletal-animation/SKILL.md` by adapting the current `/Users/cY/dev/godot-ai-2d-skeletal-animation/skill/SKILL.md`.
- Create `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/skills/godot-2d-art-import-qa/SKILL.md` for Godot project import and QA checks.
- Create `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/shared/references/artifact-contract.md`.
- Create `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/shared/references/routing.md`.
- Create `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/shared/references/prompt-patterns.md`.
- Create `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/shared/schemas/asset_pack.schema.json`.
- Create `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/scripts/validate_plugin_layout.py`.
- Create `/Users/cY/dev/godot-ai-2d-skeletal-animation/tests/test_plugin_layout.py`.
- Modify `/Users/cY/dev/godot-ai-2d-skeletal-animation/CONTEXT_SNAPSHOT.md` after each completed phase.
- Modify `/Users/cY/dev/godot-ai-2d-skeletal-animation/VERIFICATION.md` when verification evidence changes.

### Task 1: Repository Safety Baseline

**Files:**
- Modify: `/Users/cY/dev/godot-ai-2d-skeletal-animation/.git/`
- Modify: `/Users/cY/dev/godot-ai-2d-skeletal-animation/CONTEXT_SNAPSHOT.md`

- [ ] **Step 1: Confirm current non-git state**

Run:

```bash
git -C /Users/cY/dev/godot-ai-2d-skeletal-animation rev-parse --show-toplevel
```

Expected: command exits non-zero because the workspace is currently not a git repository.

- [ ] **Step 2: Initialize git**

Run:

```bash
git -C /Users/cY/dev/godot-ai-2d-skeletal-animation init
```

Expected: git creates `/Users/cY/dev/godot-ai-2d-skeletal-animation/.git/`.

- [ ] **Step 3: Add a root ignore file for generated artifacts**

Create `/Users/cY/dev/godot-ai-2d-skeletal-animation/.gitignore` with:

```gitignore
.DS_Store
log/
**/.godot/
**/*.import
__pycache__/
*.pyc
```

- [ ] **Step 4: Commit the documented baseline**

Run:

```bash
git -C /Users/cY/dev/godot-ai-2d-skeletal-animation add AGENTS.md PROJECT_CONTEXT.md CONTEXT_SNAPSHOT.md VERIFICATION.md docs scripts tests skill .gitignore
git -C /Users/cY/dev/godot-ai-2d-skeletal-animation commit -m "chore: establish godot ai 2d art baseline"
```

Expected: a baseline commit exists before Plugin scaffold changes begin.

### Task 2: Scaffold the Plugin Shell

**Files:**
- Create: `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/.codex-plugin/plugin.json`
- Create: `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/skills/`
- Create: `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/scripts/`
- Create: `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/assets/`
- Create: `/Users/cY/dev/godot-ai-2d-skeletal-animation/.agents/plugins/marketplace.json`

- [ ] **Step 1: Run the Plugin scaffold command**

Run:

```bash
python3 /Users/cY/.codex/skills/.system/plugin-creator/scripts/create_basic_plugin.py codex-2d-game-art \
  --path /Users/cY/dev/godot-ai-2d-skeletal-animation/plugins \
  --with-skills \
  --with-scripts \
  --with-assets \
  --with-marketplace \
  --marketplace-path /Users/cY/dev/godot-ai-2d-skeletal-animation/.agents/plugins/marketplace.json \
  --category "Game Development"
```

Expected: the command prints the Plugin scaffold path and marketplace manifest path.

- [ ] **Step 2: Inspect scaffolded files**

Run:

```bash
find /Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art -maxdepth 3 -type d -o -type f | sort
sed -n '1,220p' /Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/.codex-plugin/plugin.json
sed -n '1,220p' /Users/cY/dev/godot-ai-2d-skeletal-animation/.agents/plugins/marketplace.json
```

Expected: `.codex-plugin/plugin.json`, `skills/`, `scripts/`, `assets/`, and marketplace metadata are present.

### Task 3: Fill Plugin Metadata

**Files:**
- Modify: `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/.codex-plugin/plugin.json`
- Modify: `/Users/cY/dev/godot-ai-2d-skeletal-animation/.agents/plugins/marketplace.json`

- [ ] **Step 1: Replace scaffold values in `plugin.json`**

Set the Plugin manifest values to:

```json
{
  "name": "codex-2d-game-art",
  "version": "0.1.0",
  "description": "Codex-first 2D game art generation workflow for static assets, reference art, semantic part splitting, Godot cutout skeletal animation, and import QA.",
  "author": {
    "name": "Local Codex Workspace",
    "email": "devnull@example.local",
    "url": "https://example.local/codex-2d-game-art"
  },
  "homepage": "https://example.local/codex-2d-game-art",
  "repository": "https://example.local/codex-2d-game-art",
  "license": "UNLICENSED",
  "keywords": ["codex", "godot", "2d-game-art", "skeletal-animation"],
  "skills": "./skills/",
  "interface": {
    "displayName": "Codex 2D Game Art",
    "shortDescription": "Generate and validate AI-first 2D game art assets for Godot.",
    "longDescription": "A Codex-first workflow for creating static 2D assets, riggable reference art, semantic cutout parts, Godot cutout skeletal animation, and QA reports.",
    "developerName": "Local Codex Workspace",
    "category": "Game Development",
    "capabilities": ["Generate", "Validate", "Write"],
    "websiteURL": "https://example.local/codex-2d-game-art",
    "privacyPolicyURL": "https://example.local/privacy",
    "termsOfServiceURL": "https://example.local/terms",
    "defaultPrompt": [
      "Create a riggable 2D side-view hero reference and prepare it for Godot cutout animation.",
      "Generate static 2D prop assets for a Godot game and save them as local PNG files.",
      "Validate this Godot 2D cutout asset pack and summarize animation QA issues."
    ],
    "brandColor": "#2563EB",
    "composerIcon": "./assets/icon.png",
    "logo": "./assets/logo.png",
    "screenshots": []
  }
}
```

- [ ] **Step 2: Fill marketplace root metadata**

Set `/Users/cY/dev/godot-ai-2d-skeletal-animation/.agents/plugins/marketplace.json` root values to:

```json
{
  "name": "local-godot-ai-2d-art",
  "interface": {
    "displayName": "Local Godot AI 2D Art Plugins"
  },
  "plugins": [
    {
      "name": "codex-2d-game-art",
      "source": {
        "source": "local",
        "path": "./plugins/codex-2d-game-art"
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
      },
      "category": "Game Development"
    }
  ]
}
```

- [ ] **Step 3: Validate JSON syntax**

Run:

```bash
python3 -m json.tool /Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/.codex-plugin/plugin.json >/dev/null
python3 -m json.tool /Users/cY/dev/godot-ai-2d-skeletal-animation/.agents/plugins/marketplace.json >/dev/null
```

Expected: both commands exit 0.

### Task 4: Add Focused Skill Shells

**Files:**
- Create: `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/skills/ai-2d-static-art/SKILL.md`
- Create: `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/skills/ai-2d-reference-art/SKILL.md`
- Create: `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/skills/ai-2d-part-splitting/SKILL.md`
- Create: `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/skills/godot-2d-art-import-qa/SKILL.md`

- [ ] **Step 1: Create `ai-2d-static-art`**

Write `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/skills/ai-2d-static-art/SKILL.md`:

```markdown
---
name: ai-2d-static-art
description: Generate static 2D game art assets such as props, icons, tiles, UI art, and non-animated scene elements as local image files with concise provenance notes.
---

# AI 2D Static Art

Use this skill when the user needs static 2D game art and does not need a rig,
semantic cutout parts, or animation data.

## Workflow

1. Identify the asset type, target game perspective, style constraints, output
   count, and required file format.
2. Generate local image artifacts with an available image-generation capability.
3. Save outputs under the requested asset pack or a clearly named local output
   folder.
4. Write a short provenance note describing prompt intent, output files, and
   any manual acceptance risks.
5. Route to `ai-2d-reference-art` only when the user asks for animation-ready
   reference art.
```

- [ ] **Step 2: Create `ai-2d-reference-art`**

Write `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/skills/ai-2d-reference-art/SKILL.md`:

```markdown
---
name: ai-2d-reference-art
description: Generate or refine riggable 2D reference art for downstream semantic part splitting and Godot cutout skeletal animation.
---

# AI 2D Reference Art

Use this skill when the user needs an animation-ready reference image.

## Acceptance Gate

The reference must be complete, centered, padded, readable, and close to
orthographic. It should use a neutral rest pose, visible joints, and a plain or
transparent background. Reject dramatic perspective, motion blur, heavy
occlusion, or cropped limbs unless the user explicitly accepts exploratory risk.

## Workflow

1. Read or create `design_brief.md`.
2. Write `reference_prompt.txt` with riggability constraints.
3. Generate `reference.png` as a local file.
4. Inspect the image against the acceptance gate.
5. Route accepted references to `ai-2d-part-splitting`.
```

- [ ] **Step 3: Create `ai-2d-part-splitting`**

Write `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/skills/ai-2d-part-splitting/SKILL.md`:

```markdown
---
name: ai-2d-part-splitting
description: Convert riggable 2D reference art into semantic transparent cutout parts for downstream Godot skeletal animation.
---

# AI 2D Part Splitting

Use this skill when `reference.png` exists and the next step needs transparent
semantic parts.

## Workflow

1. Identify the target rig family and expected part list.
2. Generate or edit a `part_sheet.png` that contains complete semantic parts.
3. Crop or extract transparent `parts/*.png` files.
4. Reject hard rectangular crops when complete semantic parts are required.
5. Route accepted parts to `godot-2d-skeletal-animation`.
```

- [ ] **Step 4: Create `godot-2d-art-import-qa`**

Write `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/skills/godot-2d-art-import-qa/SKILL.md`:

```markdown
---
name: godot-2d-art-import-qa
description: Validate Godot 2D art asset packs, generated scenes, QA reports, previews, and project cleanliness after import/build steps.
---

# Godot 2D Art Import QA

Use this skill when the user needs Godot asset-pack validation, generated scene
checks, QA summaries, or cleanup of import side effects.

## Workflow

1. Inspect the asset pack and Godot project path.
2. Run the nearest Python validators.
3. Run Godot headless import/build/load checks when scene generation is in
   scope.
4. Confirm `qa_report.json` paths are portable and summary counts match checks.
5. Remove `.godot/` and `*.import` side effects from source folders.
```

### Task 5: Migrate the Skeletal-Animation Core

**Files:**
- Create: `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/skills/godot-2d-skeletal-animation/SKILL.md`
- Create: `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/skills/godot-2d-skeletal-animation/references/`
- Create: `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/skills/godot-2d-skeletal-animation/scripts/`
- Create: `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/skills/godot-2d-skeletal-animation/assets/`

- [ ] **Step 1: Copy current skill source into the Plugin skill**

Run:

```bash
mkdir -p /Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/skills/godot-2d-skeletal-animation
rsync -a --delete \
  --exclude=.godot/ \
  --exclude='*.import' \
  /Users/cY/dev/godot-ai-2d-skeletal-animation/skill/ \
  /Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/skills/godot-2d-skeletal-animation/
```

Expected: the Plugin contains a complete copy of the current skeletal-animation skill without Godot import side effects.

- [ ] **Step 2: Rename the Plugin-local skill metadata**

Edit `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/skills/godot-2d-skeletal-animation/SKILL.md` frontmatter to:

```markdown
---
name: godot-2d-skeletal-animation
description: Generate and validate Godot 4.x cutout skeletal animation assets from reference art, semantic parts, rig metadata, and motion JSON.
---
```

Keep the body aligned with the current skill, but update references to explain that this is the skeletal-animation module inside the Codex 2D Game Art Plugin.

- [ ] **Step 3: Validate the original skill remains unchanged**

Run:

```bash
./scripts/sync_skill.py --check-only
./scripts/run_all_checks.py --skip-godot
```

Expected: the installed current skill still matches `/Users/cY/dev/godot-ai-2d-skeletal-animation/skill`, and Python-only validation passes.

### Task 6: Add Shared Plugin Contracts

**Files:**
- Create: `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/shared/references/artifact-contract.md`
- Create: `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/shared/references/routing.md`
- Create: `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/shared/references/prompt-patterns.md`
- Create: `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/shared/schemas/asset_pack.schema.json`

- [ ] **Step 1: Create shared directories**

Run:

```bash
mkdir -p /Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/shared/references
mkdir -p /Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/shared/schemas
```

- [ ] **Step 2: Write `artifact-contract.md`**

Use this content:

````markdown
# 2D Game Art Asset Pack Contract

An asset pack is the durable handoff format between Plugin skills.

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

Each skill may create only the folders it owns. Downstream skills must inspect
which artifacts exist before generating replacements.
````

- [ ] **Step 3: Write `routing.md`**

Use this content:

```markdown
# Plugin Routing

- Static asset requests route to `ai-2d-static-art`.
- Animation-ready concept requests route to `ai-2d-reference-art`.
- Existing reference images without transparent parts route to
  `ai-2d-part-splitting`.
- Existing parts, rig metadata, or motion requests route to
  `godot-2d-skeletal-animation`.
- Godot import, generated scene checks, QA summaries, and cleanup route to
  `godot-2d-art-import-qa`.
```

- [ ] **Step 4: Write `prompt-patterns.md`**

Use this content:

```markdown
# Prompt Patterns

## Static Art

Describe the asset category, camera, palette, rendering style, background
requirement, output count, and forbidden details.

## Riggable Reference Art

Require a complete centered subject, neutral rest pose, visible joints,
orthographic camera, plain or transparent background, and clean silhouette.

## Semantic Part Splitting

Ask for complete semantic cutout parts with transparent backgrounds. Reject hard
rectangular crops and missing joint overlap.
```

- [ ] **Step 5: Write `asset_pack.schema.json`**

Use this content:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Codex 2D Game Art Asset Pack",
  "type": "object",
  "required": ["schema_version", "asset_id", "workflow"],
  "properties": {
    "schema_version": {
      "const": "1.0"
    },
    "asset_id": {
      "type": "string",
      "minLength": 1
    },
    "workflow": {
      "type": "string",
      "enum": ["static", "reference", "parts", "skeletal_animation", "godot_qa"]
    },
    "outputs": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1
      }
    }
  },
  "additionalProperties": true
}
```

### Task 7: Add Plugin Layout Validation

**Files:**
- Create: `/Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/scripts/validate_plugin_layout.py`
- Create: `/Users/cY/dev/godot-ai-2d-skeletal-animation/tests/test_plugin_layout.py`

- [ ] **Step 1: Write `validate_plugin_layout.py`**

Create a Python script that checks required Plugin files and JSON syntax:

```python
#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


REQUIRED_PATHS = [
    ".codex-plugin/plugin.json",
    "skills/ai-2d-static-art/SKILL.md",
    "skills/ai-2d-reference-art/SKILL.md",
    "skills/ai-2d-part-splitting/SKILL.md",
    "skills/godot-2d-skeletal-animation/SKILL.md",
    "skills/godot-2d-art-import-qa/SKILL.md",
    "shared/references/artifact-contract.md",
    "shared/references/routing.md",
    "shared/references/prompt-patterns.md",
    "shared/schemas/asset_pack.schema.json",
]


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_PATHS:
        path = root / relative
        if not path.exists():
            errors.append(f"missing: {relative}")

    manifest = root / ".codex-plugin" / "plugin.json"
    if manifest.exists():
        try:
            payload = load_json(manifest)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"invalid manifest: {exc}")
        else:
            if payload.get("name") != "codex-2d-game-art":
                errors.append("manifest name must be codex-2d-game-art")
            if payload.get("skills") != "./skills/":
                errors.append("manifest skills must be ./skills/")

    schema = root / "shared" / "schemas" / "asset_pack.schema.json"
    if schema.exists():
        try:
            load_json(schema)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"invalid asset pack schema: {exc}")

    return errors


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parents[1]
    errors = validate(root)
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 2: Write `tests/test_plugin_layout.py`**

Create a unittest wrapper:

```python
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "codex-2d-game-art"
VALIDATOR = PLUGIN / "scripts" / "validate_plugin_layout.py"


class PluginLayoutTests(unittest.TestCase):
    def test_plugin_layout_is_valid(self) -> None:
        spec = importlib.util.spec_from_file_location("validate_plugin_layout", VALIDATOR)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        errors = module.validate(PLUGIN)

        self.assertEqual([], errors)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run Plugin layout validation**

Run:

```bash
python3 /Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/scripts/validate_plugin_layout.py
python3 -m unittest /Users/cY/dev/godot-ai-2d-skeletal-animation/tests/test_plugin_layout.py
```

Expected: both commands exit 0.

### Task 8: Verify, Document, and Checkpoint

**Files:**
- Modify: `/Users/cY/dev/godot-ai-2d-skeletal-animation/CONTEXT_SNAPSHOT.md`
- Modify: `/Users/cY/dev/godot-ai-2d-skeletal-animation/VERIFICATION.md`

- [ ] **Step 1: Run current skill validation**

Run:

```bash
cd /Users/cY/dev/godot-ai-2d-skeletal-animation
./scripts/run_all_checks.py --skip-godot
./scripts/sync_skill.py --check-only
```

Expected: Python-only checks pass and the current installed skeletal-animation skill remains in sync.

- [ ] **Step 2: Run Plugin validation**

Run:

```bash
python3 /Users/cY/dev/godot-ai-2d-skeletal-animation/plugins/codex-2d-game-art/scripts/validate_plugin_layout.py
python3 -m unittest /Users/cY/dev/godot-ai-2d-skeletal-animation/tests/test_plugin_layout.py
```

Expected: Plugin layout checks pass.

- [ ] **Step 3: Update project context**

Update `/Users/cY/dev/godot-ai-2d-skeletal-animation/CONTEXT_SNAPSHOT.md` so:

- `status` reflects the latest completed phase.
- `Project Shape` includes the Plugin scaffold.
- `Latest Verified State` includes the exact commands from Steps 1 and 2.
- `Next Plan` removes completed items and keeps the next three to five concrete actions.

- [ ] **Step 4: Write a checkpoint**

Run:

```bash
cd /Users/cY/dev/godot-ai-2d-skeletal-animation
./scripts/context_checkpoint.sh
```

Expected: the command prints a new checkpoint path under `/Users/cY/.gstack/projects/godot-ai-2d-skeletal-animation/checkpoints/`, and `CONTEXT_SNAPSHOT.md` receives an updated `timestamp` and `latest_checkpoint`.

- [ ] **Step 5: Commit the Plugin foundation**

Run:

```bash
git -C /Users/cY/dev/godot-ai-2d-skeletal-animation add .agents plugins tests PROJECT_CONTEXT.md CONTEXT_SNAPSHOT.md VERIFICATION.md docs
git -C /Users/cY/dev/godot-ai-2d-skeletal-animation commit -m "feat: scaffold codex 2d game art plugin"
```

Expected: the commit contains the Plugin scaffold, focused skill shells, shared references, validation script, tests, and updated project context.

## Self-Review

- Spec coverage: The plan covers Plugin scaffold, metadata, skill decomposition, skeletal-animation migration, shared contracts, validation, context updates, and checkpointing.
- Placeholder scan: The plan uses concrete names, paths, commands, and file contents.
- Scope check: This is focused on creating the local Codex Plugin foundation. Future work such as EditorPlugin UI, advanced motion heuristics, and production segmentation automation remains outside this implementation plan.
