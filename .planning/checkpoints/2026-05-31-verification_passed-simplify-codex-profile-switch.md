# Checkpoint: simplify-codex-profile-switch verification passed

Date: 2026-05-31

## Scope

Simplified the Codex profile switcher UX so daily switching uses:

```bash
codex-profile deepseek
codex-profile official
```

The old overlay-only workflow remains available through:

```bash
codex-profile deepseek --cli-only
codex --profile deepseek
```

## Changed Files

- `dev/tools/codex-profile-switch/switch-profile.sh`
- `dev/tools/codex-profile-switch/tests/test_switch_profile.py`
- `dev/tools/codex-profile-switch/README.md`
- `openspec/changes/harden-codex-profile-switch/proposal.md`
- `openspec/changes/harden-codex-profile-switch/design.md`
- `openspec/changes/harden-codex-profile-switch/specs/codex-profile-switch/spec.md`
- `openspec/changes/harden-codex-profile-switch/tasks.md`
- `.planning/verification/20260531112729-simplify-codex-profile-switch.md`

## Verification

- `bash -n dev/tools/codex-profile-switch/switch-profile.sh`: pass.
- `python3 -m unittest discover -s dev/tools/codex-profile-switch/tests`: pass, 7 tests ran.
- JSON template parse checks: pass.
- DeepSeek provider TOML parse: pass.
- Codex model catalog parse includes `ccx`: pass.
- `openspec validate harden-codex-profile-switch --strict`: pass.
- `codex-profile help` and `codex-profile deepseek --help`: pass.

## Remaining Risks

- `codex app` still does not support `--profile`, so base config activation remains necessary for Desktop App DeepSeek mode.
- CCX must be running or startable from `CCX_DIR` for DeepSeek calls to succeed.

## Next Action

Review the local diff, then archive `harden-codex-profile-switch` when ready.
