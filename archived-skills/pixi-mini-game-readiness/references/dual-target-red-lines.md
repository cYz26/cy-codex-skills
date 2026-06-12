# Dual-Target Red Lines

Use this reference during readiness audits to define constraints that future Web work must not violate.

## Shared Code Red Lines

Treat these as `blocker` or `high-risk` unless fully isolated:
1. `window`, `document`, `navigator`, or `location` in shared gameplay, systems, or scene orchestration
2. direct `localStorage`, `sessionStorage`, IndexedDB, or vendor storage APIs outside a storage wrapper
3. hardcoded asset roots such as `/assets/...` inside shared runtime code
4. raw `fetch` or `XMLHttpRequest` inside gameplay logic
5. vendor-specific conditionals spread through scenes or systems

## UI and Rendering Red Lines

Treat these as migration risks:
1. gameplay-critical HTML overlays
2. layout logic coupled to DOM geometry instead of a platform viewport contract
3. scene code that owns lifecycle listeners directly
4. fonts or assets that become mandatory for the mini-game critical path without package-budget review
5. Chinese UI text that assumes runtime font APIs or unverified mini-game canvas text will be reliable

## Platform Boundary Rules

Keep platform-specific behavior in one place:
1. target entrypoints
2. `platform/` wrappers
3. boot-time lifecycle wiring
4. build or packaging config

Do not leak vendor launch payloads, storage formats, or lifecycle callbacks into gameplay modules.

## Review Trigger

When any red line is touched, require:
1. explicit boundary review
2. updated validation notes
3. a statement of whether the change preserved future mini-game compatibility
4. for WeChat-bound Chinese copy, an explicit decision between runtime fonts and packaged glyph or bitmap strategy
