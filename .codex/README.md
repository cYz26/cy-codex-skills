# Project-Local Codex Setup

This directory is intentionally limited to reviewable documentation. Machine
local Codex runtime files below `.codex/` are ignored and are not DevFlow
configuration, readiness evidence, or release input.

Current DevFlow project configuration lives in `.dev-flow.json`; project-local
workflow skills live in `.agents/skills/`. Preview activation with:

```bash
python3 dev/plugins/dev-flow/scripts/activate_project_dependencies.py \
  --repo /Users/cY/dev/skills/cy-codex-skills \
  --plugin-root /Users/cY/dev/skills/cy-codex-skills/dev/plugins/dev-flow \
  --codex-home /Users/cY/.codex \
  --refresh-project-skills --dry-run --json
```

Apply mode, installed-cache refresh, and cleanup each require separate explicit
authorization.
