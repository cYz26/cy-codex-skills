# Slice 9 Provider Hardening Evidence

## Claim

DevFlow now has an independent `core + none` default, provider-neutral stable
contracts, action-free unselected providers, project-local Lean Matt
activation, optional roadmap-only GSD, and explicit Superpowers compatibility.
Provider cleanup is isolated from activation, requires complete persisted
selection plus a reviewed digest and named authorization, removes only verified
symlinks through no-follow anchored directory descriptors, and rolls back in
the same controlled directory.

## Current Upstream Comparison

- Superpowers `v6.1.1` and main resolved to
  `d884ae04edebef577e82ff7c4e143debd0bbec99` on 2026-07-13. Its selected
  Codex manifest declares no SessionStart hook, so DevFlow uses manifest-driven
  hook requirements instead of version inference.
- Matt main resolved to
  `391a2701dd948f94f56a39f7533f8eea9a859c87`; `v1.1.0` resolved to
  `d574778f94cf620fcc8ce741584093bc650a61d3`.
- The snapshots contain 14 Superpowers skills and 39 Matt skills. The six
  approved Matt primitives total 6,771 static words versus 20,957 for the six
  closest Superpowers primitives. This supports a smaller opt-in instruction
  surface; it does not establish equal outcomes and does not justify replacing
  DevFlow Core with the full Matt control plane.
- Decision: do not replace one mandatory dependency with another. Keep
  `core + none` as default, `lean-matt` as a project-local six-skill opt-in,
  `strict-superpowers` as an optional strict adapter, and GSD only as an
  explicitly selected roadmap provider.

Upstream references:

- <https://github.com/obra/superpowers>
- <https://github.com/obra/superpowers/releases/tag/v6.1.1>
- <https://github.com/mattpocock/skills>
- <https://github.com/mattpocock/skills/blob/main/skills/engineering/setup-matt-pocock-skills/SKILL.md>

## TDD and Review Evidence

- RED reproduced provider-specific stable gates, unselected remediation leaks,
  global Matt satisfaction, wrong-digest side writes, incomplete selection
  cleanup, external parent escape, parent-swap TOCTOU, action-bearing
  provenance, malformed ledger fail-open behavior, and missing Matt
  lock/unique-source bootstrap.
- GREEN added stable capability IDs, action-free `*_unselected` reports,
  project-local Matt routing, selector -> matching lock -> unique trusted source
  precedence, cleanup-only execution, complete explicit selection checks,
  digest and named authorization, symlink provenance checks, `O_DIRECTORY |
  O_NOFOLLOW` parent traversal, dirfd `stat/readlink/unlink/rollback`, parent
  inode revalidation, and fail-closed ledger parsing.
- Independent review initially reported four P1, five P2, and one P3 finding.
  A repair review ran 165 focused tests and confirmed every implementation and
  documentation finding closed. No unresolved P0-P3 finding remains.
- The reviewer accidentally invoked the Matt installer while testing its CLI;
  all 39 newly created skill directories and the new lock file were identified
  by creation time and moved to
  `/tmp/codex-accidental-matt-skills-20260713-164520/`. Project diagnosis then
  confirmed `projectPackPresent=false` and all six local Matt routes absent.

## Commands and Results

| Gate | Result |
|---|---|
| Full development discovery | 438 tests in 65.373s, `OK` |
| Packaged release discovery | 8 tests in 0.307s, `OK` |
| Release runtime verifier | 277 checks, `verified` |
| Runtime archive SHA-256 | `6f860c942a16fc853a5caa05ce4f2ef465c28cb1b5f19108a7e2239e173c8570` |
| Release asset dry-run | `current` |
| Strict OpenSpec validation | valid |
| Independent final review | implementation pass |
| `git diff --check` | pass |

Release-target Plugin Eval (`plugins/dev-flow`) reported:

- score `86/100`, grade `B`, medium risk;
- zero failures, three established static-budget warnings, two informational
  findings;
- `trigger_cost_tokens=385`, `invoke_cost_tokens=11430`,
  `deferred_cost_tokens=27044`, total `38859`;
- no observed-usage sample supplied.

The three static warnings are retained as an explicit residual. A paid/live
paired outcome benchmark and blind review remain separately authorized gates
for any future proposal to change the default provider; they do not block the
provider seam or the removal of a mandatory Superpowers/GSD dependency.

## Local Runtime and Cleanup

- Active usable runtime:
  `/Applications/ChatGPT.app/Contents/Resources/codex`, version
  `codex-cli 0.144.0-alpha.4`.
- The named cache refresh installed
  `dev-flow@cy-codex-skills` at
  `/Users/cY/.codex/plugins/cache/cy-codex-skills/dev-flow/0.3.0+codex.20260529145038`.
- Post-refresh cache verification is `matches-source`; project migration and
  skill layout are `current`; workflow doctor is healthy.
- `.dev-flow.json` explicitly persists `methodology_profile: core` and
  `roadmap_provider: none`.
- Reviewed cleanup plan
  `b4a46f672c0c965808edcda707d600e82c03f40f204cbde420402df2c560cc5a`
  removed exactly four legacy Superpowers links from `.agents/skills` and four
  from `.codex/skills`. Global plugin configuration and provider caches were
  preserved.
- After final cleanup hardening and cache refresh, dry-run plan
  `db93490cee5a17862c881c11cbb84f605638c9c3fa0cb95d71722a9913332a69`
  reports `current`, zero candidates, zero preserved paths, and zero writes.
- Current dependency diagnosis is `coreReady=true`,
  `methodologyReady=true`, `roadmapReady=true`. Superpowers, Matt, and GSD are
  `available_unselected`; their provenance contains no install command,
  recommended command, fallback, next action, or readiness effect.

## Risks and Dispositions

- Cleanup rollback is transactional within the running process. SIGKILL or
  power loss between multiple unlink operations can still leave partial
  removal; the reviewed plan retains per-link rollback commands for recovery.
- Globally installed Superpowers plugins, the global Matt pack, existing GSD
  project files, and provider caches remain in place. DevFlow ignores them when
  unselected; removal/disable is a separate user-authorized operation.
- The PATH shim `/Users/cY/.codex-switch/bin/codex` still targets missing
  `/Applications/Codex.app/Contents/Resources/codex`. The verified ChatGPT App
  runtime was used directly for refresh. Repairing `codex-switch` is outside
  this change.
- OpenSpec archive was not performed because archive remains separately gated.

## Reviewer Notes

- Provider identities remain implementation details of selected adapters;
  canonical completion evidence remains DevFlow/OpenSpec-owned.
- GSD is not needed for ordinary DevFlow execution. It remains useful only when
  explicitly selected to own roadmap, milestone, phase, and phase-verification
  governance.
