# Release Isolation for Skills and Plugins

Development happens under `dev/`. Installable release sources live outside `dev/`.

```text
dev/skills/<skill-name>/              # Draft or actively changing standalone skill
<skill-name>/                         # Release-ready standalone skill source

dev/plugins/<plugin-name>/            # Draft or actively changing plugin bundle
plugins/<plugin-name>/                # Release-ready plugin source

.agents/plugins/marketplace.json      # Release marketplace; only points at plugins/<plugin-name>
.agents/plugins/marketplace.dev.json  # Optional local dev marketplace; may point at dev/plugins/<plugin-name>
.release/                             # Generated release staging, never committed
```

Top-level skill directories remain the release source because the restore flow already copies or symlinks them into `~/.codex/skills/`.

## Asset States

- `dev`: work in progress; may include tests, fixtures, logs, local reports, and experiments.
- `staging`: copied to `.release/` for review; generated and disposable.
- `release`: clean source used by installs, marketplaces, and cross-machine restore.
- `archived`: no longer maintained; kept only for history or compatibility.

## Standalone Skill Workflow

1. Create or iterate on a skill in `dev/skills/<skill-name>/`.
2. Keep tests, scratch files, eval output, and drafts inside the dev skill directory.
3. Promote by running `sync_release_assets.py --apply` after dev validation
   has passed, or let the DevFlow release promotion gate run at the verified
   stop boundary.
4. Verify the promoted skill from the top-level directory.
5. Update `README.md` when adding, renaming, or retiring a release skill.

Release standalone skills should include only runtime files:

- `SKILL.md`
- `references/`
- `assets/`
- `scripts/`
- `agents/`
- Small examples that are referenced directly by the skill

Do not promote local logs, generated output, test caches, or one-off evaluation reports.

## Plugin Workflow

1. Create or iterate on a plugin in `dev/plugins/<plugin-name>/`.
2. Keep plugin tests, fixtures, evals, logs, and local reports in the dev plugin directory.
3. Promote by running `sync_release_assets.py --apply` after dev validation
   has passed, or let the DevFlow release promotion gate run at the verified
   stop boundary.
4. Point `.agents/plugins/marketplace.json` at `./plugins/<plugin-name>`.
5. If local development needs marketplace testing, create `.agents/plugins/marketplace.dev.json` and point it at `./dev/plugins/<plugin-name>`.

Release plugins should include only manifest-declared or runtime files:

- `.codex-plugin/plugin.json`
- `skills/`
- `hooks.json`
- `scripts/`
- `assets/`
- `agents/`
- `.mcp.json` or `.app.json` when shipped
- `README.md`, `CHANGELOG.md`, and license files when present

Do not promote `tests/`, `fixtures/`, `log/`, `__pycache__/`, generated eval artifacts, or local-only reports unless a runtime skill directly references them.

## Release Promotion Gate

The `dev -> release` sync point is the verified workflow boundary:

```text
dev changes -> dev validation passes -> release promotion gate -> release validation
```

The gate does not run on ordinary edits or saves. It runs from the DevFlow
`Stop` hook after `.planning/STATE.md` records `gates.verification_passed:
true`. The sync is allowlist-based, with optional per-asset metadata in
`.codex-plugin/release-sync.json` or `release-sync.json` for custom excludes,
build commands, and managed release outputs.

Use the explicit CLI when preparing a commit or evaluating a target manually:

```bash
python3 dev/plugins/dev-flow/scripts/sync_release_assets.py --apply --json
python3 dev/plugins/dev-flow/scripts/sync_release_assets.py --eval-target dev/plugins/dev-flow --json
```

Plugin Eval should use the release asset as the primary target when one exists:

- `dev/plugins/<plugin-name>` resolves to `plugins/<plugin-name>`.
- `dev/skills/<skill-name>` resolves to `<skill-name>`.
- Dev-path eval is diagnostic only, useful for source-tree size or authoring
  checks that are intentionally outside the release package.

## Marketplace Rules

- `.agents/plugins/marketplace.json` is the release marketplace.
- Release marketplace entries should reference `./plugins/<plugin-name>`, not `./dev/plugins/<plugin-name>`.
- Each plugin entry should keep `policy.installation`, `policy.authentication`, and `category`.
- Dev marketplace files may exist for local testing but are not release truth.

## Promotion Checklist

1. Confirm the dev source has no unrelated dirty changes.
2. Run `sync_release_assets.py --apply`.
3. Check that release sources contain no `log/`, `__pycache__/`, generated reports, or scratch files.
4. Run the asset-specific release validation command and Plugin Eval against the release path.
5. Review the diff for accidental deletes, path changes, or marketplace drift.

## Current Repository Migration

For `dev-flow`, keep iterating in `dev/plugins/dev-flow`. Its release copy lives at `plugins/dev-flow`.

On this machine, the active development install is `dev-flow@agents-dev-local`.
The `agents-dev-local` marketplace is still rooted at `/Users/cy/Dev/agents-dev` so it can also serve
other local plugins, but its `dev-flow` entry should resolve to:

```text
/Users/cy/Dev/agents-dev/cy-codex-skills/dev/plugins/dev-flow
```

After changing the dev plugin, refresh the local install with:

```bash
codex plugin add dev-flow@agents-dev-local
```

Then verify the source marketplace mapping with:

```bash
python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py \
  --plugin-root /Users/cy/Dev/agents-dev/cy-codex-skills/dev/plugins/dev-flow \
  --marketplace /Users/cy/Dev/agents-dev/.agents/plugins/marketplace.json \
  --repo /Users/cy/Dev/agents-dev/cy-codex-skills \
  --codex-home /Users/cy/.codex \
  --config /Users/cy/.codex/config.toml \
  --json
```

When promoting it:

1. Run `python3 dev/plugins/dev-flow/scripts/sync_release_assets.py --apply`.
2. Keep `.agents/plugins/marketplace.json` pointed at `./plugins/dev-flow`.
3. Keep `.agents/plugins/marketplace.dev.json` pointed at `./dev/plugins/dev-flow` for local development testing.
4. Keep tests and fixtures in the dev copy.
5. Run unit tests from the dev copy and Plugin Eval against `plugins/dev-flow`.

The existing `plugins/godot-core` already matches the release-side plugin location. If it needs heavier iteration, create `dev/plugins/godot-core` and promote back to `plugins/godot-core` after validation.
