# 20-server-headers.md - Web Server Headers and Compression

Use this checklist for Web deployment setup.

## MIME

1. `.wasm` -> `application/wasm`
2. `.pck` -> `application/octet-stream` (common default)

## COOP/COEP (Only When Threads Enabled)

1. `Cross-Origin-Opener-Policy: same-origin`
2. `Cross-Origin-Embedder-Policy: require-corp`

## Compression

Enable `gzip` or `brotli` for `.wasm`, `.pck`, and `.js` when deployment platform supports it.

## Nginx Example Notes

1. Add wasm MIME mapping in `types`.
2. Scope COOP/COEP headers to proper paths.
