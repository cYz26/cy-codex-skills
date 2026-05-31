# Tasks: Harden Codex Profile Switcher

## Target State

The Codex profile switcher provides a safe, reversible DeepSeek/CCX mode through two daily commands: `codex-profile deepseek` and `codex-profile official`. The default DeepSeek command prepares the CLI overlay and activates the Desktop App base config; `--cli-only` keeps the overlay-only workflow available.

## Completion Contract

- [x] Add failing regression tests for default one-command DeepSeek switching.
- [x] Add failing regression tests for CLI-only overlay generation without base config mutation.
- [x] Add failing regression tests for fixed `ccx` provider id with alternate model aliases.
- [x] Add failing regression tests for official mode preserving unrelated providers and reasoning effort.
- [x] Add failing regression tests for Desktop App activation and exact official restore.
- [x] Add failing regression tests for current Codex model catalog compatibility.
- [x] Implement profile overlay generation and non-destructive official behavior.
- [x] Implement one-command DeepSeek switching plus targeted Desktop App activation for base config and snapshot restore.
- [x] Update CCX template and documentation.
- [x] Run focused tests, syntax checks, Codex catalog validation, and OpenSpec validation.
- [x] Update workflow state and record verification evidence.

## Capability Slices

### Slice 1: Regression tests

**Status:** done

**Implementation**
- [x] Add Python unittest coverage under `dev/tools/codex-profile-switch/tests`.
- [x] Use temporary `CODEX_HOME` directories only.
- [x] Assert current failure modes before implementation.
- [x] Cover default DeepSeek switching and `--cli-only`.
- [x] Cover Desktop App activation and official restore.

**Validation Commands**
```bash
python3 -m unittest discover -s dev/tools/codex-profile-switch/tests
```

### Slice 2: Switcher implementation

**Status:** done

**Implementation**
- [x] Generate `$CODEX_HOME/deepseek.config.toml` from templates.
- [x] Make `deepseek` switch both CLI overlay and base config by default.
- [x] Keep `deepseek --cli-only` for overlay-only use.
- [x] Keep `model_provider = "ccx"` independent from requested model alias.
- [x] Make `official` non-destructive and remove only generated DeepSeek overlay when requested.
- [x] Restore official snapshot when the base config is currently activated for CCX.
- [x] Keep backup/restore commands for manual recovery.
- [x] Add validation helpers for profile and CCX health.

**Validation Commands**
```bash
bash -n dev/tools/codex-profile-switch/switch-profile.sh
python3 -m unittest discover -s dev/tools/codex-profile-switch/tests
```

### Slice 3: Templates, docs, and final verification

**Status:** done

**Implementation**
- [x] Update DeepSeek model catalog to current Codex schema.
- [x] Update CCX example to supported option values.
- [x] Update README to document simplified daily switching, CLI-only usage, and migration from older destructive switching.
- [x] Record verification evidence and update `.planning/STATE.md`.

**Validation Commands**
```bash
python3 -m json.tool dev/tools/codex-profile-switch/profiles/deepseek/models_catalog.json >/dev/null
python3 -m json.tool dev/tools/codex-profile-switch/ccx/config.example.json >/dev/null
openspec validate harden-codex-profile-switch --strict
```

## Execution Ledger

| Slice | Status | Evidence |
|---|---|---|
| Regression tests | done | `python3 -m unittest discover -s dev/tools/codex-profile-switch/tests` |
| Switcher implementation | done | `bash -n dev/tools/codex-profile-switch/switch-profile.sh`; focused unittest suite |
| Templates, docs, and final verification | done | JSON/TOML validation, Codex catalog parse, OpenSpec strict validation |

## Final Verification

- [x] Focused switcher tests pass.
- [x] Script syntax and JSON/TOML templates validate.
- [x] Codex model catalog compatibility is checked.
- [x] OpenSpec validates in strict mode.
