# 90-web-debug-playbook.md - Web Incident Playbook

Use this checklist for black screen, no input, no audio, or startup failures.

## 1) Basic Checks

1. Check browser console for wasm MIME, resource 404, CORS, and runtime exceptions.
2. Check network panel for wasm/pck status and stale cache hits.
3. Confirm `.wasm` is served as `application/wasm`.

## 2) Threads-Related Checks

1. If `Use Threads` is on, verify COOP/COEP headers exist.
2. Or verify PWA workaround is active and service worker is functioning.

## 3) Asset and Path Checks

1. Confirm custom HTML shell matches exported file layout.
2. Confirm CDN rewrite or SPA fallback rules are not breaking resource paths.

## 4) Incident Output

1. Key error logs or screenshots
2. Minimal reproducible URL plus browser version
3. Proposed fix path (headers, MIME, cache, export options)
