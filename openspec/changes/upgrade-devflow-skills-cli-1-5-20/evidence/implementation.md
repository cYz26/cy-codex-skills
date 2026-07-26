# Implementation Evidence

## Capability Evidence

- Date: 2026-07-23
- `npm view skills version engines dist-tags --json`: `latest` and version are
  `1.5.20`; Node requirement is `>=22.20.0`.
- `npm view skills repository homepage --json`: package source is
  `vercel-labs/skills`.
- `node --version`: `v24.13.0`, satisfying the installer requirement.
- `npx -y skills@1.5.20 --help`: existing `add`, repeated `--skill`,
  `--agent codex`, and `--yes` arguments remain available.
- Local scan: only development and generated release dependency provenance
  contained `skills@1.5.9`.

## TDD Evidence

RED was observed before changing provenance:

```text
test_dependencies.py: 26 run, 1 expected failure
test_packaged_runtime.py: 5 run, 1 expected failure
```

Both failures showed the exact installer mismatch
`skills@1.5.9` versus `skills@1.5.20`; no unrelated test failed.

GREEN after the development provenance update:

```text
test_dependencies.py: 26 tests passed
```

The passing provenance test reverified the unchanged Matt repository, release
ref, selected skills, vendored file hashes, license hash, and project
adaptations.

## Source Verification

- `PYTHONDONTWRITEBYTECODE=1 python3.12
  dev/scripts/run_devflow_prepromotion_tests.py`: 338 tests across 21 source
  modules passed with no skips.
- `openspec validate upgrade-devflow-skills-cli-1-5-20 --strict`: passed.
- `openspec validate --all --strict`: 56/56 repository items passed.
- `python3.12 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo .
  --json`: passed with no issues or warnings before the active-state update.
- `git diff --check`: passed.
- Source-bound release receipt:
  `.planning/devflow/release-verification/dev-flow.json`, SHA-256
  `241036fa1b01eb64a8a4a7cd80e636ad9755c91d59e24259967283916f3962db`.

## Release Verification

- The user explicitly authorized the combined `dev-flow` release promotion,
  direct-main commit, SSH push, and local DevFlow cache refresh.
- `release_promotion_gate.py --target dev-flow --apply --json` synchronized the
  verified source and generated runtime transactionally.
- The immediate release sync dry-run returned `status: current` with no
  changed, missing, deleted, or stale files or outputs.
- Complete development discovery passed 372/372 tests.
- Packaged release discovery passed 5/5 tests.
- Runtime archive verification returned `ok: true`; archive SHA-256 is
  `4f7d695c922eb97f94d037b06b01fd74a93ca7f45ac2a951bda01f1f5a45b600`.
- Release-target Plugin Eval scored 86/100, grade B, with 0 failures and three
  static token-budget warnings. The warnings remain bounded plugin-wide debt;
  both changed skills remain within the evaluator's good line-count range.
- The internal updater dry-run identified only
  `dev-flow@cy-codex-skills` as differing from its marketplace source among the
  named local core plugin caches. No updater apply or project migration ran
  during release verification.

## Authorization Boundaries

The user authorized the installer dependency contract, combined DevFlow release
promotion, direct-main commit, SSH push, and targeted local DevFlow refresh.
Project migration, archive, pull request creation, credential mutation,
unrelated plugin refresh, and cleanup remain unauthorized.
