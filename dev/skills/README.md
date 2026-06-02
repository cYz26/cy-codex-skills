# Development Skills

Use this directory for standalone Codex skills that are still being drafted, tested, or heavily revised.

```text
dev/skills/<skill-name>/
```

Promote a skill to the repository root only after it is ready to be restored
into `~/.codex/skills/`. Use `sync_release_assets.py --apply` after dev
validation has passed, or let the DevFlow release promotion gate run at the
verified stop boundary. Keep tests, scratch files, generated output, and local
reports in the dev skill directory unless the runtime skill directly references
them.

See `../../docs/release-isolation.md` for the repository-wide isolation policy.
