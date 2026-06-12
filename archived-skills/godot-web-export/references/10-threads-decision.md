# 10-threads-decision.md - Web Use Threads Decision

## Default

Keep `Use Threads` disabled by default for better compatibility and simpler deployment.

## Enable Only If All Conditions Hold

1. Runtime is secure context (`HTTPS` or `localhost`)
2. You can guarantee both response headers:
   - `Cross-Origin-Opener-Policy: same-origin`
   - `Cross-Origin-Embedder-Policy: require-corp`
3. Or, if header control is unavailable, explicitly use the export PWA workaround and verify service worker behavior.

## Post-Enable Checks

1. Confirm headers are present in deployment smoke checks.
2. Confirm browser console has no `SharedArrayBuffer` or COOP/COEP related errors.
