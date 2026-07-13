# Slices 3-4 Adapter, Dependency, and Activation Evidence

## RED

Focused tests first demonstrated that:

- multiple roots ignored matching/stale locks;
- Matt hash drift was accepted;
- no persistence authorization seam existed;
- dependency report required absent Superpowers and GSD for `core + none`;
- activation always planned GSD and Superpowers links;
- updater always planned Superpowers and detected-installed GSD;
- activation CLI wrote by default;
- provider source IDs and explicit persistence flags were unsupported.

Each failure was observed before the corresponding production edit.

## GREEN

Command:

```bash
python3.12 -m unittest \
  dev/plugins/dev-flow/tests/test_provider_profiles.py \
  dev/plugins/dev-flow/tests/test_dependencies.py \
  dev/plugins/dev-flow/tests/test_superpowers_artifact_mapping.py -v
```

Result: `Ran 72 tests in 18.166s` and `OK`.

Verified behavior:

- selector -> matching lock -> unique discovery precedence;
- ambiguous and stale source blocking without cross-root skill mixing;
- manifest-declared-only hook checks;
- Matt allowed/excluded mappings and selected skill hashes;
- `--provider-source PROVIDER=SOURCE_ID` uses recorded portable source IDs;
- config and lock persistence require both `--apply` and
  `--persist-provider-selection`;
- full 3 methodology x 2 roadmap readiness matrix;
- GSD drift and Superpowers availability are non-blocking when unselected;
- activation and updater plan only selected providers;
- activation CLI is dry-run by default and `--apply` is the unified mutation
  authority;
- existing `--strict` developer-helper behavior remains independent from
  methodology selection;
- provider drafts remain non-canonical until promoted.

Apply-path tests used isolated temporary repositories only. No real provider,
project, cache, release, or external dependency was modified.
