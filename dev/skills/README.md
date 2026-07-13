# Development Skills

Use this directory for standalone Codex skills that are still being drafted, tested, or heavily revised.

```text
dev/skills/<skill-name>/
```

Promote a skill to the repository root only after it is ready to be restored
into `~/.codex/skills/`. Direct `sync_release_assets.py --apply` calls are
denied; use the issuer-gated release promotion workflow after validation has
passed. DevFlow uses `release_promotion_gate.py --apply` at a verified boundary.
Keep tests, scratch files, generated output, and local reports in the dev skill
directory unless the runtime skill directly references them.

See `../../docs/release-isolation.md` for the repository-wide isolation policy.
