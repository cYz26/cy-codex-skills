## Why

DevFlow's recorded Matt skill installer still invokes `skills@1.5.9`, while
the published npm `latest` is `1.5.20`. Keeping the older executable pin makes
the dependency provenance stale and omits the newer package's Node
`>=22.20.0` runtime requirement.

## What Changes

- Pin the Matt skill installation command to `skills@1.5.20`.
- Record Node `>=22.20.0` as the installer runtime requirement without
  changing the pinned `mattpocock/skills` `v1.1.0` source or content hashes.
- Add source and packaged regression assertions for the exact installer
  version, runtime requirement, and unchanged installation arguments.
- Synchronize the verified DevFlow release counterpart and run release-target
  Plugin Eval before claiming completion.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `devflow-plugin-quality`: DevFlow dependency provenance must expose the
  current verified `skills` installer pin and its supported Node runtime in
  both development and release packages.

## Impact

- Affected development policy:
  `dev/plugins/dev-flow/docs/dependency-provenance.json`.
- Affected release policy:
  `plugins/dev-flow/docs/dependency-provenance.json`, after separately
  authorized release promotion.
- Affected tests: development dependency provenance and packaged runtime
  contract tests.
- No Matt skill source, hash, project-local skill, installed plugin cache,
  migration, commit, push, or archive is changed by this request.
