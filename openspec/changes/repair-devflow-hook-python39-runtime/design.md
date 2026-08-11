## Context

See `proposal.md` for motivation. Every Unix Hook command in
`dev/plugins/dev-flow/hooks.json` invokes the host's bare `python3`. On the
affected macOS profile that resolves to Python 3.9.6. The public Hook wrappers
load the packaged archive, and both relevant import graphs reach
`workflow_legacy_uninstall.py`, whose unconditional `import tomllib` aborts the
process before Hook policy or response adaptation runs.

The repository already requires standard-library-only runtime code and
fail-closed legacy cleanup classification. The source repair was isolated and
verified without mutating the immutable DevFlow 0.4.0 release. On 2026-08-11
the user separately authorized a successor patch release, direct fast-forward
submission to `main`, immutable publication, and refresh of only the internal
named DevFlow cache.

## Goals / Non-Goals

**Goals:**

- Keep the existing portable `python3` Hook manifest while allowing the Hook
  runtime to import and execute on Python 3.9.
- Preserve exact Codex response schemas and current Python 3.11+ behavior.
- Preserve cleanup safety when TOML ownership cannot be parsed.
- Lock the failure down at the public Hook process boundary and the
  legacy-uninstall inspection boundary.

**Non-Goals:**

- General Python 3.9 support for maintenance, release, or migration apply CLIs.
- A bundled Python interpreter, new dependency, vendored TOML parser, or global
  PATH change.
- Rewriting or replacing immutable DevFlow `0.4.0` artifacts.
- Archive, PR creation, merge commits, force push, alternate publication,
  other-plugin refresh, or consumer-project migration.

## Decisions

### Make `tomllib` an optional import at the inspection boundary

`workflow_legacy_uninstall.py` will treat `tomllib` as an optional capability.
TOML decode failures will be caught through `ValueError`, which covers
`TOMLDecodeError` without dereferencing an unavailable module.

This keeps the complete Hook import graph loadable on Python 3.9. Changing the
manifest to `python3.12` was rejected because it would replace one implicit
runtime assumption with another and would fail on hosts that do not install
that exact executable name.

### Preserve ownership proof instead of using the minimal TOML parser

The existing minimal parser is suitable for read-only context-tool inventory,
but it intentionally ignores unsupported TOML constructs. Legacy uninstall can
authorize cleanup candidates, so partial parsing is not strong enough evidence.

The inspector will read the raw configuration first. If it has no GSD
reference, no TOML parse is needed. If it references GSD and `tomllib` is
unavailable, the exact path becomes a manual action with a stable
parser-unavailable reason. No candidate is emitted.

Vendoring `tomli` was rejected because it adds production dependency and
release surface for behavior that can remain safe through conservative
classification.

### Test the public process boundary with deterministic parser absence

A focused test will invoke the source Hook entrypoints in subprocesses while a
temporary shadow module makes `import tomllib` raise `ModuleNotFoundError`.
This is deterministic on every supported test interpreter and exercises the
same import chain that failed in the packaged runtime.

The legacy-uninstall test will additionally set the module capability to
unavailable and assert candidate/manual classification. On this workstation,
fresh direct runs under `/usr/bin/python3` 3.9.6 and Python 3.12 provide runtime
qualification beyond the portable regression.

### Verify an isolated generated release candidate

Canonical `plugins/dev-flow/` remains unchanged because release sync is not
authorized. Verification will build a temporary release candidate from the
changed development plugin, run both Hook entrypoints under Python 3.9 and
3.12, inspect runtime parity, and run Plugin Eval against that candidate. The
temporary root is invocation-owned and outside the repository.

### Advance refresh evidence without a project migration

`workflow_legacy_uninstall.py` is a declared project-refresh tracked input.
Changing it invalidates the revision-11 evidence digest even though the repair
does not alter `.dev-flow.json`, project-local skills, config targets, or
migration behavior.

The source project-refresh contract will advance to revision 12, bind this
change ID and the fresh tracked-input digest, and remain a `managed-refresh`
decision at project schema 8. No configuration target or migration step is
added.

### Publish an immutable `0.4.1` successor

The Python 3.9 compatibility change advances runtime bytes after immutable
`dev-flow-v0.4.0`, so the release identity becomes `0.4.1` rather than
overwriting or retagging `0.4.0`. Source plugin metadata, version-bearing
templates, release policy, expected manifest, release notes, exact asset
expectation, bundle tests, and the tag-bound GitHub Actions workflow will agree
on `dev-flow-v0.4.1`.

The publication workflow remains exact-tag-only, commit-pinned, and
least-privilege. It rebuilds the deterministic runtime and seven declared
assets from the immutable tag, verifies their frozen names, sizes, and hashes,
then creates a non-draft, non-prerelease GitHub Release without overwrite
flags.

### Execute only the authorized external effects

The authorized effect chain is:

1. promote source to `plugins/dev-flow/**` through the release promotion gate;
2. run complete source/release/runtime/OpenSpec/Plugin Eval verification;
3. create one reviewed commit on the isolated branch;
4. fast-forward local `main` to that commit and push `refs/heads/main`;
5. create and push immutable tag `dev-flow-v0.4.1`;
6. require GitHub Actions/Release publication and exact asset readback;
7. refresh only
   `CODEX_HOME=/Users/cY/.codex-switch/homes/internal`
   `dev-flow@cy-codex-skills`;
8. prove the installed cache runs migration and Stop Hooks under Python 3.9.

No consumer-project migration is part of this chain. Technical failure stops
the next effect while preserving the reviewed commit and immutable tag.

## Target State

Both public Hook entrypoints start successfully through source, generated
release, and the refreshed internal installed cache when `tomllib` is absent.
GSD-bearing TOML remains non-actionable without parser-backed proof, modern
Python behavior is unchanged, and source/main/tag/Release/cache identities all
resolve to immutable DevFlow `0.4.1`.

## Completion Contract

- A regression demonstrates the pre-fix import failure.
- The focused compatibility and legacy-uninstall tests pass.
- Direct Python 3.9 and 3.12 Hook runs exit without traceback.
- Revision-12 project-refresh impact evidence is current, config-insensitive,
  and requires no project-schema advance.
- Source suites, strict OpenSpec validation, workflow validation, diff checks,
  isolated runtime parity, and release-target Plugin Eval pass or have
  explicitly dispositioned non-blocking warnings.
- The generated release is current and byte-consistent with source.
- The reviewed commit is the exact local/remote `main` and tag target.
- GitHub Release `dev-flow-v0.4.1` is published with the frozen asset set.
- Only the internal named DevFlow cache is refreshed and its Python 3.9 Hook
  entrypoints pass without traceback.
- No archive, PR, force push, release overwrite, other-plugin refresh, or
  consumer-project migration occurs.

## Critical Path

1. Add the public-entrypoint and fail-closed RED regressions.
2. Make the parser capability optional with conservative classification.
3. Advance the tracked project-refresh evidence without a configuration
   migration.
4. Run focused source tests and both local Python runtimes.
5. Build and inspect an isolated release candidate.
6. Version and promote the exact `0.4.1` generated release.
7. Run broad source/release/runtime/OpenSpec/Plugin Eval verification.
8. Commit, fast-forward/push `main`, publish the immutable tag, and read back
   Release assets.
9. Refresh only the internal named cache and rerun the Python 3.9 Hook loop.
10. Record final identities and completion evidence.

## Incidental Finding Budget

One bounded RED/GREEN guard is allowed if another Python 3.9 import failure is
revealed by the same two Hook entrypoints. Any unrelated CLI compatibility,
cache drift, release workflow, or project migration issue is
`DEFER_AND_CONTINUE`.

## Capability Slices

1. **Hook startup compatibility:** subprocess regressions plus optional parser
   import.
2. **Cleanup safety:** parser-unavailable classification and focused ownership
   tests.
3. **Refresh evidence:** revision-12 managed refresh at unchanged project
   schema 8.
4. **Packaged qualification:** isolated runtime generation, dual-runtime Hook
   execution, parity, and Plugin Eval.
5. **Patch release identity:** `0.4.1` metadata, deterministic expected
   manifest, release notes, exact asset expectation, and tag workflow.
6. **Generated release:** canonical promotion plus complete release/runtime
   verification and Plugin Eval.
7. **Publication:** reviewed commit, fast-forward `main`, immutable tag,
   GitHub Release, and public asset readback.
8. **Internal activation:** named cache refresh and live Python 3.9 Hook proof.

## Execution Ledger

| Slice | Owner | Write Set | Evidence | Human Gate |
| --- | --- | --- | --- | --- |
| 1-2 | main agent | source module, focused tests | RED/GREEN command logs | none |
| 3 | main agent | source refresh manifest and impact regression | current digest and unchanged schema proof | migration/release apply excluded |
| 4 | main agent | invocation-owned temporary candidate only | runtime hashes and Hook outputs | release/cache apply excluded |
| 5 | main agent | version metadata, release docs/workflow/tests, exact publication evidence | focused RED/GREEN and asset identity | user-authorized patch release |
| 6 | main agent | generated `plugins/dev-flow/**`, release verification evidence | complete suites, runtime parity, Plugin Eval | release promotion authorized |
| 7 | main agent | reviewed Git commit, `main`, tag, GitHub Release | Git/readback and asset hashes | commit/push/publication authorized |
| 8 | main agent | internal named DevFlow cache only | cache identity and Python 3.9 Hooks | named cache refresh authorized |

## Continuation Policy

Execution is `auto-until-terminal` through the authorized release and internal
cache refresh. Stop only for a production dependency, public Hook schema
change, cleanup-authority weakening, non-fast-forward/diverged `main`,
tag/release identity collision, publication asset mismatch, an unnamed cache
or project target, or another material write-set expansion.

## Generated Artifact Strategy

The isolated packaged candidate is created under a fresh OS temporary
directory, owned by one verification invocation, retained only through command
completion, and removed by that invocation. No repository path is registered
for automatic cleanup and no canonical generated release asset is written.

## Validation Commands

```bash
PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest \
  dev/plugins/dev-flow/tests/test_hook_python_compatibility.py \
  dev/plugins/dev-flow/tests/test_legacy_workflow_uninstall.py -v
PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest \
  dev/plugins/dev-flow/tests/test_implementation_readiness.py -v
/usr/bin/python3 dev/plugins/dev-flow/scripts/devflow_stop_hook.py --repo .
/usr/bin/python3 dev/plugins/dev-flow/scripts/plugin_project_migration_check.py \
  --event user_prompt_submit
PYTHONDONTWRITEBYTECODE=1 python3.12 dev/scripts/run_devflow_prepromotion_tests.py
openspec validate repair-devflow-hook-python39-runtime --strict
openspec validate --all --strict
python3.12 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo . --json
python3.12 dev/plugins/dev-flow/scripts/release_promotion_gate.py \
  --repo . --target dev-flow --apply --json
PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest discover \
  -s dev/plugins/dev-flow/tests -p 'test_*.py'
PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest discover \
  -s plugins/dev-flow/tests -p 'test_*.py'
python3.12 plugins/dev-flow/scripts/verify_release_runtime.py \
  --plugin-root plugins/dev-flow --repo-root . --json
plugin-eval analyze plugins/dev-flow --format markdown
git diff --check
```

Isolated candidate generation, dual-runtime Hook execution, runtime parity, and
Plugin Eval commands will be recorded in the verification evidence because
their temporary path is invocation-specific.

## Project Refresh Impact

Disposition: `changed`.

- Hook manifest, skills, project schema, and refresh action set are unchanged.
- The source refresh contract advances from revision 11 to revision 12 because
  `workflow_legacy_uninstall.py`, plugin version metadata, version-bearing
  templates, and release policy are tracked inputs; evidence binds this change
  and the final fresh digest.
- Project schema remains 8, all v1-v8 config targets remain immutable, and no
  migration step is added.
- Packaged runtime bytes, source identity, release identity, and installed-cache
  identity change to `0.4.1`.
- No consumer-project file requires migration; existing managed links remain
  structurally valid.
- A future authorized release/cache refresh must regenerate the runtime,
  promote the release counterpart, refresh only the named DevFlow caches, and
  require source/release/cache identity readback.

## Project-Directed Implementation Readiness

No external implementation provider is selected.
`implementation_readiness.required` remains `false`.

## Risks / Trade-offs

- **[Risk] Python 3.9 reaches another unsupported import after `tomllib`.**
  -> Keep the RED loop at the public process boundary and allow one bounded
  compatibility guard in the same import graph.
- **[Risk] Parser absence hides a safe cleanup candidate.**
  -> Prefer manual review over weakened ownership proof; cleanup remains
  available under Python 3.11+.
- **[Risk] Source verification passes while packaged runtime remains stale.**
  -> Build and exercise an isolated release candidate before completion.
- **[Risk] The repair contaminates the frozen 0.4.0 milestone.**
  -> Publish only successor `0.4.1`; never move or overwrite the `0.4.0` tag or
  Release.
- **[Risk] `main` or the remote changes before push.**
  -> Fetch and rerun exact-base/fast-forward preflight immediately before
  mutation; stop on divergence without merge, rebase, or force push.
- **[Risk] Tag transport succeeds but publication fails.**
  -> Preserve the immutable tag, diagnose once, and resume only the same
  reviewed identity; do not refresh the cache before Release readback.
- **[Risk] Plugin registration succeeds but the cache remains stale.**
  -> Compare source/release/cache version, refresh revision, runtime archive,
  and repaired module hashes, then rerun the real Python 3.9 Hook entrypoints.

## Rollback

Before commit, rollback is deletion of this isolated worktree's change and code
diff only. Before tag push, the reviewed commit remains recoverable and no
Release/cache state exists. After publication, rollback requires a separately
reviewed successor release rather than rewriting an immutable tag. Cache
refresh failure preserves the published release and restores no unrelated
plugin or project state.

## Review Checklist

- Hook subprocess tests exercise real entrypoints and inspect exit/output.
- No fallback parser can authorize automatic cleanup.
- Modern Python behavior and response schemas remain unchanged.
- Generated runtime contains the corrected source bytes.
- Version, workflow, expected manifest, asset expectation, generated release,
  tag, Release, and installed cache identities agree on `0.4.1`.
- Remote `main` and tag target the reviewed commit without merge/rebase/force.
- No archive, PR, release overwrite, other-plugin refresh, or consumer-project
  migration claim is made.
