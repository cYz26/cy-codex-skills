# 30-loading-cache-versioning.md - Web Cache and Versioning

## Goal

Use strong cache where safe while keeping controllable invalidation for new releases.

## Strategy

1. Prefer versioned or hashed output file names.
2. Keep entry HTML weak-cached (short TTL), static assets strong-cached (long TTL).
3. If file renaming is impossible, use query-string versioning as fallback.

## Rollback

1. Keep previous full build directory (or storage prefix).
2. Roll back by switching entry pointer (`index.html` or manifest reference).
