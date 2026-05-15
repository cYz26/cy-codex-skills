# Agent Instructions

## Project Context

This workspace contains the source for the `godot-ai-2d-skeletal-animation` Codex skill.

- Workspace root: `/Users/cY/dev/godot-ai-2d-skeletal-animation`
- Canonical skill source: `/Users/cY/dev/godot-ai-2d-skeletal-animation/skill`
- Installed skill copy: `/Users/cY/dev/skills/godot-ai-2d-skeletal-animation`
- Project status snapshot: `/Users/cY/dev/godot-ai-2d-skeletal-animation/CONTEXT_SNAPSHOT.md`
- Verification log: `/Users/cY/dev/godot-ai-2d-skeletal-animation/VERIFICATION.md`
- gstack checkpoints: `/Users/cY/.gstack/projects/godot-ai-2d-skeletal-animation/checkpoints`

Read `CONTEXT_SNAPSHOT.md` before making project-level changes. It is the current source of truth for status, decisions, gotchas, and the next plan.

## Skill routing

- Use Superpowers process skills when their trigger matches the work.
- Before claiming completion or a passing state, use Superpowers `verification-before-completion`: identify the command that proves the claim, run it fresh, read the output, then report the evidence.
- For Codex skill edits, use `skill-creator` and keep `SKILL.md` concise with detailed material in `references/`.
- For Godot fixture or script changes, use the Godot project workflow in `godot-core`: inspect first, keep edits local, and run the nearest Python and Godot validations.
- For context save/restore work, use the helper scripts in `scripts/` and keep `CONTEXT_SNAPSHOT.md` plus the gstack checkpoints in sync.

## Context Management

Use these commands from the workspace root:

```bash
./scripts/context_status.sh
./scripts/context_checkpoint.sh
./scripts/run_all_checks.py
./scripts/sync_skill.py --check-only
```

`context_status.sh` is read-only. It reports the current snapshot header, git state if available, skill sync state, QA summary, Godot import side effects, and the latest gstack checkpoint.

`context_checkpoint.sh` writes a new gstack checkpoint and updates the `timestamp` and `latest_checkpoint` fields in `CONTEXT_SNAPSHOT.md`.

`run_all_checks.py` runs the full verification suite. By default it uses a temporary Godot fixture copy for import/build/load so the skill source remains clean.

`sync_skill.py` syncs the canonical `skill/` directory to `/Users/cY/dev/skills/godot-ai-2d-skeletal-animation`. Use `--check-only` to verify sync without copying.

After meaningful changes:

1. Update `CONTEXT_SNAPSHOT.md` if status, decisions, gotchas, or next steps changed.
2. Run `./scripts/run_all_checks.py` or the nearest smaller validation command.
3. Sync `skill/` with `./scripts/sync_skill.py` if the skill source changed.
4. Run `./scripts/context_checkpoint.sh`.

## Verification

Minimum checks for status-only work:

```bash
./scripts/run_all_checks.py --skip-godot
```

Full Godot validation should run on a temporary fixture copy when possible, so `.godot/` and `*.import` files do not pollute the skill source.

## Gotchas

- This workspace is not currently a git repository.
- `skill/` should match the installed skill copy after sync.
- Run `summarize_animation_qa.py` from inside `skill/` so QA report paths stay relative.
- Keep `.godot/` and `*.import` files out of the skill source.
- The expected committed Godot script UID files are:
  - `skill/fixtures/godot_demo_project/tools/build_ai_2d_rig.gd.uid`
  - `skill/fixtures/godot_demo_project/tools/demo_event_receiver.gd.uid`
- AI reference-art prompting is allowed when constrained to Godot cutout
  riggability; provider-specific image API integration remains outside the
  skill promise.
