# Dual-Target Pitfalls

## Asset and Packaging

Watch for:
1. raw `/assets/...` paths reappearing in shared runtime code
2. fonts becoming mandatory for startup or mini-game critical path
3. asset loaders that assume browser URL or cache behavior
4. DevTools or local precompile paths such as `gameContext/assets/...` being handled in shared runtime code instead of packaging
5. fixed-copy text atlases or similar packaged text assets changing without regenerating the bundle inputs
6. Chinese UI text that depends on runtime font APIs, `loadFontFace`, or mini-game canvas text without a verified fallback
7. packaged glyph or bitmap text assets that are read before the asset cache is ready
8. new Chinese UI copy landing in source code while the checked-in glyph atlas still lacks those characters, producing replacement squares only in the mini-game target
9. build pipelines that regenerate text assets only on one target path, leaving debug and release packages out of sync

## Lifecycle and Boot

Watch for:
1. visibility or resize logic attached directly inside scenes
2. launch context leaking vendor-specific payloads into gameplay code
3. duplicate listener registration after reload or scene restart

## Persistence and Network

Watch for:
1. direct browser storage access returning to shared modules
2. network or leaderboard logic bypassing platform wrappers
3. save formats diverging between targets without an explicit bridge contract

## Review Smell

Treat these as likely regressions:
1. "quick Web-only fix" that edits shared scene or system code
2. build commands run for only one target after changing boot, assets, storage, text assets, or packaging
3. no statement about which target was or was not smoke-tested
4. packaging fixes that rewrite shared asset resolution instead of satisfying the target-specific build layout
5. copy changes merged without regenerating packaged glyph or bitmap text assets when the project uses them
6. copy changes merged without any automated source-vs-atlas coverage test, so missing glyphs are discovered only in DevTools or on device
