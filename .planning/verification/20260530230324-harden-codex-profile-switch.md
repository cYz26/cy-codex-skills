# Verification: harden-codex-profile-switch

Date: 2026-05-30

## Commands

```bash
bash -n dev/tools/codex-profile-switch/switch-profile.sh
```

Result: pass.

```bash
python3 -m unittest discover -s dev/tools/codex-profile-switch/tests
```

Result: pass. Output: 5 tests ran in 0.395s, OK.

```bash
python3 -m json.tool dev/tools/codex-profile-switch/profiles/deepseek/models_catalog.json >/dev/null
python3 -m json.tool dev/tools/codex-profile-switch/ccx/config.example.json >/dev/null
```

Result: pass.

```bash
python3 - <<'PY'
import pathlib, tomllib
for path in [pathlib.Path('dev/tools/codex-profile-switch/profiles/deepseek/config.openai.toml')]:
    tomllib.loads(path.read_text())
print('toml ok')
PY
```

Result: pass. Output: `toml ok`.

```bash
codex -c 'model_catalog_json="dev/tools/codex-profile-switch/profiles/deepseek/models_catalog.json"' debug models
```

Result: pass. Parsed output includes model slug `ccx`.

```bash
openspec validate harden-codex-profile-switch --strict
```

Result: pass. Output: `Change 'harden-codex-profile-switch' is valid`.

```bash
dev/tools/codex-profile-switch/switch-profile.sh deepseek
dev/tools/codex-profile-switch/switch-profile.sh validate
```

Result: pass in temporary `CODEX_HOME`. Profile TOML parsed and Codex model catalog parsed.

## Notes

- `codex app --help` exposes `-c/--config` but not `--profile`; docs therefore use `activate-deepseek` for Desktop App instead of `codex --profile deepseek app`.
- All switcher tests use temporary `CODEX_HOME` directories and do not mutate the real `~/.codex/config.toml`.
