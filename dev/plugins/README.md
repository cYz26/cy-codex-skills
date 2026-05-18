# Development Plugins

This directory stores Codex plugins that are still in local development or staging before being promoted to a marketplace-style package.

Each plugin should keep its own `.codex-plugin/plugin.json`, skills, hooks, scripts, tests, and README under:

```text
dev/plugins/<plugin-name>/
```

Keep production-ready standalone skills at the repository root. Keep development-stage plugin bundles here.
