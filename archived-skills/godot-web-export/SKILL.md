---
name: godot-web-export
description: Godot Web export and deployment workflow with thread compatibility decision gates, server header and MIME checks, cache/version policy, and browser runtime incident diagnosis. Use when Codex works on HTML5 export, CDN or object-storage deployment, WebView adaptation, or Web black-screen and startup failures.
---

# Godot Web Export

Use this skill for Web-specific export, deployment, and runtime troubleshooting.

## 1) Mandatory Web DoD

Run in order:
1. `make export-web`
2. `make web-smoke`

If repository lacks these targets, run equivalent commands and document mapping.
Use template script if needed:
1. `assets/templates/tools/web_smoke_test.sh`

## 2) Thread Decision (Mandatory)

Default to `Use Threads = off`.
Enable threads only when deployment guarantees secure context plus COOP/COEP headers, or verified PWA workaround behavior.
See `references/10-threads-decision.md`.

## 3) Deployment Contract

1. Confirm wasm MIME (`application/wasm`).
2. Configure COOP/COEP only when threads are enabled.
3. Configure compression for wasm/pck/js where supported.
4. Apply explicit cache and versioning policy for predictable rollouts and rollback.

See:
1. `references/20-server-headers.md`
2. `references/30-loading-cache-versioning.md`

## 4) Incident Playbook

When black-screen, no input, or no audio appears:
1. Check console/network evidence
2. Check threads/header state
3. Check asset paths and custom shell mismatches
4. Output minimal reproducible URL and browser version

See `references/90-web-debug-playbook.md`.

## 5) Handoff Requirements

Always provide:
1. Export command and preset used
2. Smoke/deploy verification commands and results
3. Header/MIME/cache decisions applied
4. Residual compatibility risks

## 6) Escalate to Other Subskills

1. Use `$godot-core` for non-Web architecture and gameplay refactor.
2. Use `$godot-mini-game` for mini-game constraints and release criteria.

## Resource Map

1. `references/10-threads-decision.md`: thread enablement decision gate.
2. `references/20-server-headers.md`: MIME/header/compression checks.
3. `references/30-loading-cache-versioning.md`: cache and rollout policy.
4. `references/90-web-debug-playbook.md`: incident diagnosis checklist.
5. `assets/templates/tools/web_smoke_test.sh`: local web smoke script template.
