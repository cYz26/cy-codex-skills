# Verification: simplify-codex-profile-switch

Date: 2026-05-31

## Commands

```bash
bash -n dev/tools/codex-profile-switch/switch-profile.sh
```

Result: pass.

```bash
python3 -m unittest discover -s dev/tools/codex-profile-switch/tests
```

Result: pass. Output: 7 tests ran, OK.

```bash
python3 -m json.tool dev/tools/codex-profile-switch/profiles/deepseek/models_catalog.json >/dev/null
python3 -m json.tool dev/tools/codex-profile-switch/ccx/config.example.json >/dev/null
```

Result: pass.

```bash
python3 - <<'PY'
import tomllib
from pathlib import Path
for path in [Path('dev/tools/codex-profile-switch/profiles/deepseek/config.openai.toml')]:
    tomllib.loads(path.read_text())
print('toml parse ok')
PY
```

Result: pass. Output: `toml parse ok`.

```bash
codex -c 'model_catalog_json="dev/tools/codex-profile-switch/profiles/deepseek/models_catalog.json"' debug models
```

Result: pass. Parsed output includes model slug `ccx`.

```bash
openspec validate harden-codex-profile-switch --strict
```

Result: pass. Output: `Change 'harden-codex-profile-switch' is valid`.

```bash
codex-profile help
codex-profile deepseek --help
```

Result: pass. Help shows simplified daily commands and `--cli-only`; `deepseek --help` does not print status after help.

```bash
ls -l /Users/cy/.local/bin/codex-profile
command -v codex-profile
```

Result: pass. `codex-profile` resolves to `/Users/cy/.local/bin/codex-profile`, symlinked to the project script.

## Notes

- Daily usage is now `codex-profile deepseek` and `codex-profile official`.
- `codex-profile deepseek --cli-only` preserves the previous overlay-only behavior for CLI runtime commands.
- Tests use temporary `CODEX_HOME` directories and do not mutate the real `~/.codex/config.toml`.
