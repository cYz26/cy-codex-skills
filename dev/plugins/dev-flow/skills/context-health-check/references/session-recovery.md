# Historical Session Recovery

Read this file only for older Codex work that predates DevFlow context-health
events.

Import best-effort local history without mutating task artifacts:

```bash
python3 scripts/context_health_import_codex_sessions.py \
  --repo <repo> \
  --codex-home ~/.codex \
  --json
```

Imported history is partial. Treat missing context usage, prompt attribution,
and tool-schema attribution as unknown rather than healthy. Store only
sanitized metadata; never retain prompt bodies, file bodies, command-output
bodies, or raw tool payload bodies.
