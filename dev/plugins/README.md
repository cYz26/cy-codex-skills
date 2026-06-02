# Development Plugins

This directory stores Codex plugins that are still in local development or staging before being promoted to a release-ready package under `../../plugins/`.

Each plugin should keep its own `.codex-plugin/plugin.json`, skills, hooks, scripts, tests, and README under:

```text
dev/plugins/<plugin-name>/
```

Keep tests, fixtures, logs, eval output, and local reports in this development
directory. Promote only runtime files to `plugins/<plugin-name>/` with
`sync_release_assets.py --apply`, then point `.agents/plugins/marketplace.json`
at the promoted copy. DevFlow also runs this sync at verified stop boundaries.

See `../../docs/release-isolation.md` for the repository-wide isolation policy.
