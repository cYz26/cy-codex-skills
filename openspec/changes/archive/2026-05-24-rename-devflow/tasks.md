## 1. Tests First

- [x] 1.1 Update packaging, marketplace, hook config, and README tests to expect `dev-flow` and `DevFlow`.
- [x] 1.2 Run focused unittest targets and confirm rename expectations fail before implementation.

## 2. Plugin Identity Rename

- [x] 2.1 Rename dev and release plugin directories to `dev-flow`.
- [x] 2.2 Update plugin manifests, marketplace catalogs, asset titles, preflight checks, dependency fixtures, and script descriptions.
- [x] 2.3 Update hook labels and hook config lookup to prefer `.dev-flow.json` with legacy fallback.
- [x] 2.4 Update maintained README/planning references for canonical plugin paths and install names.

## 3. Verification

- [x] 3.1 Run focused unittest targets for packaging, dependency, and hook behavior.
- [x] 3.2 Run full plugin unittest discovery from the renamed dev plugin path.
- [x] 3.3 Run plugin preflight for dev and release plugin roots against the updated marketplaces.
- [x] 3.4 Update this task list and report remaining risks.
