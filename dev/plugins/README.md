# Development Plugins

This directory stores Codex plugins that are still in local development or staging before being promoted to a release-ready package under `../../plugins/`.

Each plugin should keep its own `.codex-plugin/plugin.json`, skills, hooks, scripts, tests, and README under:

```text
dev/plugins/<plugin-name>/
```

Keep tests, fixtures, logs, eval output, and local reports in this development
directory. Promote only runtime files to `plugins/<plugin-name>/` with
the plugin's issuer-gated release promotion path; direct
`sync_release_assets.py --apply` calls are denied. For DevFlow, record fresh
verification and run
`dev/plugins/dev-flow/scripts/release_promotion_gate.py --repo . --apply --json`,
then point `.agents/plugins/marketplace.json` at the promoted copy.

See `../../docs/release-isolation.md` for the repository-wide isolation policy.
