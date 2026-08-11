# Python 3.9 Hook Runtime Repair And 0.4.1 Release Verification

- Timestamp: `2026-08-11`
- Change: `repair-devflow-hook-python39-runtime`
- Boundary: development source, invocation-owned isolated candidates, canonical
  generated release, immutable publication, and the internal named cache.
  Consumer projects and archive remain unchanged.

## Claim

Both DevFlow public Hook entrypoints now start when `tomllib` is unavailable.
GSD-bearing TOML remains manual-only without parser-backed ownership proof,
while unrelated TOML creates no false legacy-uninstall action. The source
refresh contract advances to revision 12 at unchanged project schema 8 with no
new configuration target or migration step.

## TDD Evidence

- RED: 7 focused tests failed before the repair. Both Hook subprocesses exited
  with `ModuleNotFoundError: No module named 'tomllib'`; parser-unavailable
  classification reached the old parser-specific exception coupling.
- GREEN: the same 7 focused tests passed after the optional import and
  fail-closed classification change.
- Direct source qualification: migration and Stop Hook entrypoints returned
  existing Codex-compatible output schemas under Python 3.9.6 and 3.12.13.
- Final Project Refresh Impact: `changed_covered`; source revision 12 versus
  release baseline 11; project schema 8 on both sides; changed tracked inputs
  are plugin metadata, the OpenSpec config template, release policy, and
  `scripts/workflow_legacy_uninstall.py`; there are no
  configuration-sensitive changes. Tracked-input SHA-256:
  `0efefd8b804d81f4240e5667c5a92fd12a8df498e4844138d0c3ee553f52e8d6`.

## Fresh Verification

| Check | Result |
|---|---|
| focused Hook and legacy-uninstall suite | PASS, 7/7 |
| implementation-readiness regressions | PASS, 26/26 |
| project-refresh regressions | PASS, 64/64 |
| final full pre-promotion source suite | PASS, 743/743 across 34 modules |
| isolated candidate file count | 188 |
| isolated candidate tree SHA-256 | `dca4f197fea1a679fcd28b9e568d1bcaf9809d1828bd48bc5aa02587e1d6602f` |
| isolated runtime archive SHA-256 | `76d7bbf85f7dfaeb1d7e05b82792483d41f580dda5ccfccb0ed0104990d5421f` |
| runtime verification | PASS, 321/321 |
| source/packaged module SHA-256 | `a17c83e81f8b09e7b37ee7f7a49b163e10b20f23dd2a089f580eece4597e495d` |
| packaged Hooks on Python 3.9.6 | PASS |
| packaged Hooks on Python 3.12.13 | PASS |
| release-candidate Plugin Eval | 86/B, 0 fail, 3 warn, 2 info |
| isolated 0.4.1 bundle | PASS, exactly 7 assets |
| expected release manifest | PASS, 189 entries, tree `b035e4df01652c023c4a70a8968547af09f1e7328d226efa12ead704f89a47c3` |
| strict OpenSpec | PASS, 35/35 |
| workflow validation | PASS |
| `git diff --check` | PASS |
| temporary candidate cleanup | PASS |

The Plugin Eval warnings are the existing whole-plugin trigger, invoke, and
deferred token-budget findings recorded under `DF-IFL-001`. The informational
findings do not report a runtime, correctness, security, or packaging failure.

## Scope Review

- Runtime change is confined to optional TOML-parser capability and
  conservative GSD classification.
- No fallback or partial TOML parser can authorize cleanup.
- Hook manifests and public response schemas are unchanged.
- No production dependency or project configuration migration was added.
- Final diff review found no task-owned write outside the source module,
  focused tests, refresh evidence, OpenSpec, state, ledger, and this evidence.
- The repository intentionally ignores new `openspec/changes/**` and
  `.planning/**` paths; this change and evidence require explicit inclusion at
  any separately authorized commit boundary.

## Pre-Promotion External-Effect Readback

Checked-in `plugins/dev-flow/` and the internal installed DevFlow cache both
remain at refresh revision 11 with runtime archive SHA-256
`34a9e36a2760b9edfec35f789caa0f6829c942fab2074a350216d70475a8ce81`
and packaged legacy-uninstall module SHA-256
`def5a1fc65d9d1ab57a7ba23528d3bc4bb78508a1c4e9a27e8fa52b8be1c738d`.
This proves the verified revision-12 candidate was not promoted or installed.

## Authorized Release Gate

Source implementation, patch-release identity, and pre-promotion verification
are complete. The user explicitly authorized exact `plugins/dev-flow/**`
promotion, one reviewed commit, fast-forward `main` push, immutable
`dev-flow-v0.4.1` publication with asset readback, and refresh of only the
internal named DevFlow cache. Archive, PR, merge commit, rebase, force push,
release overwrite, other-plugin refresh, and consumer-project migration remain
excluded.

## Canonical Promotion And Post-Promotion Verification

The release verification receipt was regenerated after the final
post-promotion test adjustment. Its source SHA-256 is
`a3694173df0981f49b5bfa976415df0387bdb1f64b3378c2076304ab6903f1d6`.
The promotion gate then returned `status: current` with no changed or deleted
release files.

| Check | Result |
|---|---|
| final pre-promotion source suite | PASS, 743/743 across 34 modules |
| first post-promotion source suite | RED, 804/805; stale phase-specific assertion only |
| focused post-promotion guard | PASS, 26/26 |
| final complete source suite | PASS, 805/805 in 259.490 seconds |
| focused release/runtime suite | PASS, 68/68 |
| generated release suite | PASS, 60/60 |
| strict OpenSpec | PASS, 35/35 |
| workflow validation | PASS, no issues or warnings |
| runtime verification | PASS |
| runtime archive SHA-256 | `76d7bbf85f7dfaeb1d7e05b82792483d41f580dda5ccfccb0ed0104990d5421f` |
| source/packaged repaired module SHA-256 | `a17c83e81f8b09e7b37ee7f7a49b163e10b20f23dd2a089f580eece4597e495d` |
| release-target Plugin Eval | 86/B, 0 fail, 3 warn, 2 info |
| exact release asset verifier | PASS, 7/7 |
| asset-set digest | `74439cf989b85983c39277cbc71fcc49f07b56d4210503de39509a310b1d2d2a` |
| syntax checks | PASS |
| `git diff --check` | PASS |

The post-promotion RED was caused by a test that required
`changed_covered` after the generated release had already become the revision
12 baseline. The bounded regression now verifies `changed_covered` when source
revision is ahead and `current` when source and release revisions match. No
runtime or release byte changed.

The seven frozen asset records are stored in
`evidence/dev-flow-0.4.1.release-assets.json`.

## Published Release And Internal Cache Closeout

- Release commit:
  `47ca042c4b015a939e98e5e5def4c2680321e627`, tree
  `f3ed45449474418a9eb074675b2d112faee7e23e`.
- Local and remote `main` plus local and remote `dev-flow-v0.4.1` all resolved
  to the release commit at publication readback.
- The public GitHub Release is stable, non-draft, non-prerelease, and marked
  Latest. It was published at `2026-08-11T12:06:32Z` and binds commit
  `47ca042`.
- All seven downloaded assets passed
  `verify_devflow_release_assets.py` with asset-set SHA-256
  `74439cf989b85983c39277cbc71fcc49f07b56d4210503de39509a310b1d2d2a`.
- The internal absolute Codex CLI installed and enabled
  `dev-flow@cy-codex-skills` `0.4.1` at
  `/Users/cY/.codex-switch/homes/internal/plugins/cache/cy-codex-skills/dev-flow/0.4.1`.
  Source, generated release, and active cache are byte-identical at refresh
  revision 12 and project schema 8.
- Generated release and active cache runtime archive SHA-256 is
  `76d7bbf85f7dfaeb1d7e05b82792483d41f580dda5ccfccb0ed0104990d5421f`.
  Source, packaged release, and active cache
  `workflow_legacy_uninstall.py` SHA-256 is
  `a17c83e81f8b09e7b37ee7f7a49b163e10b20f23dd2a089f580eece4597e495d`.
- Installed migration and Stop Hooks both exited 0 with empty stderr under
  `/usr/bin/python3` 3.9.6 and returned their existing JSON schemas.
- The refresh initially invalidated the live task's already-loaded absolute
  `0.4.0` Hook path. Exact `0.4.0` bytes were restored from immutable tag
  `dev-flow-v0.4.0`, while `0.4.1` remains the active installed version. The
  compatibility snapshot is retained until old sessions restart; no cleanup
  was authorized.
- Consumer-project migration, archive, PR, merge commit, rebase, force push,
  release overwrite, and other-plugin refresh did not run.
