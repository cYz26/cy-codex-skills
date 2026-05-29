# Context Fixer Web Dashboard

This dashboard uses the stable sanitized JSON projection emitted by
`context-fixer dashboard data`. The current implementation is dependency-free
and served by the Python standard-library HTTP server, so the Web version works
without Tauri or a Node build step.

The placeholder token in `dist/index.html` is replaced by `dashboard serve` at
request time.
