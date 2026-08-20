# Changelog

## 0.2.4

Suite-provenance and multi-CLI diagnostic hardening.

### Changed

- Binds suite provenance to the CLI-reported `suite` layout, explicit
  `in_sync: true` evidence, and SHA-256 equality for every nested Skill body; a
  complete but hand-shaped, stale, or unverifiable suite remains unverified.
- Treats any unreachable embedded inventory as unverified guidance divergence,
  and preserves structured stderr errors even when a failed command also emits
  JSON on stdout.

## 0.2.3

Codex manager-visibility correction for the official suite layout.

### Changed

- Separates one-directory filesystem compaction from Codex manager visibility:
  Codex recursively discovers the suite's nested `references/lark-*/SKILL.md`
  files, so a verified suite is not reported as manager-compact.
- Reports `codex_recursive_exposure_count` and `codex_manager_compact` alongside
  structural provenance and recommends the plugin-only path when zero global
  Lark exposure is required.

## 0.2.2

Compact global-guidance layout compatibility patch.

### Changed

- Recognizes a CLI-managed `lark-suite` as verified official exposure only when
  its canonical shared-root path, frontmatter, and nested Skill inventory match
  the healthy canonical CLI embedded inventory.
- Keeps spoofed, incomplete, symlinked, or inventory-divergent suite trees in
  the unverified bucket.
- Reports `layout: suite` and filesystem `compact_layout: true` for the verified
  one-directory topology while retaining the warning that the shared root
  remains visible to Codex.

## 0.2.1

Lark CLI 1.0.88 compatibility and identity-safety release. Public plugin,
Skill, and script entry-point names remain unchanged.

### Changed

- Treats omitted identity/profile as `unknown`, emits explicit `--as` and
  `--profile` arguments when requested, blocks returned identity/profile
  mismatches, and never persists mismatched execution as success.
- Preserves requested domains and makes any unmapped or blocked guidance source
  deny otherwise direct-eligible routing.
- Retains structured CLI error JSON emitted on stderr while keeping nonzero
  process status authoritative.
- Makes Doctor update-cache writes opt-in through `--write-update-cache`; normal
  preflight remains no-write while still reusing an existing valid cache.
- Audits embedded skill name/optional-version digests for every reachable CLI
  and reports binary-version and embedded-guidance divergence separately.
- Blocks Codex-only Skill unload before mutation when the shared
  `~/.agents/skills` root makes agent-only isolation impossible.
- Preserves an explained Doctor warning as sync `WARN` instead of incorrectly
  upgrading current CLI/cache compatibility to `FAIL`, and returns a successful
  diagnostic exit for `PASS` or `WARN`.
- Keeps packaged Agent Context, Doctor, and Sync entry points no-write with
  respect to their release tree by disabling Python bytecode emission.
- Documents `LARKSUITE_CLI_PROFILE` precedence, separate/suite global Skill
  layouts, split embedded Skill references, and the 1.0.70+ dry-run envelope.

## 0.2.0

Compatibility-hardening release. The public plugin name `lark-feishu-ops`,
skill name `lark-feishu-ops`, and command entry points remain unchanged.

### Changed

- Classifies actions from an explicit read allowlist. Unknown, raw, write, and
  high-risk actions are no longer eligible for direct execution, and caller
  hints cannot downgrade risk.
- Resolves trusted, version-matched guidance through `lark-cli skills
  list/read`; arbitrary local paths, `inject_as`, and replacement commands are
  rejected with machine-readable warnings.
- Requires fresh FeishuOps work to use `fork_turns: none`, treats active
  registry entries as runtime-confirmed candidates only, and retires terminal or
  idle lifecycle state.
- Replaces rich continuity snapshots with bounded schema-v2 metadata, secure
  `0600` atomic writes, pruning, sensitive-domain no-cache defaults, explicit
  opt-out/purge, and caller-authoritative freshness.
- Inventories every reachable CLI, validates command-specific JSON fail closed,
  separates official skill provenance from exposure, supports current
  `.agents/skills` plus legacy `.codex/skills` reporting, and compares complete
  runtime assets from dynamic manifest/home state.
- Ignores and prunes schema-v1 continuity state rather than migrating private
  payloads; operators can remove all retained metadata through `purge`.
- Covers the current 27 embedded Lark skills, including apps, event, note, VC
  agent, and both workflow skills.
- Covers CLI-only top-level domains (`application`, `mindnotes`, `config`,
  `profile`, `doctor`, `update`, `whoami`, `skills`, and `schema`) with focused
  help fallbacks, while unmapped domains now return an explicit blocker.
- Preserves the complete runtime operation capsule across delegation while
  keeping persisted continuity allowlisted and metadata-only; current schema-v2
  snapshots and active-agent entries reject or strip unknown private fields.
- Declines persistence when result freshness/provenance is missing, malformed,
  future-dated, or marked `require_refetch`; enforces 24-hour ordering and the
  32 KiB serialized budget before write, and safely bounds oversized registries.
- Invalidates a same-day update-check cache when its current version differs
  from the executable detected by Doctor.
- Ships a bounded offline runtime-contract self-test for installed-package
  policy/state verification without network or state mutation.
- Replaces private-looking evaluation resources with reserved synthetic data.
