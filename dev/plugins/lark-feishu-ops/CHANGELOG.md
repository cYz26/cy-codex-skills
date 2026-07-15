# Changelog

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
