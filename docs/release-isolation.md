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
3. Promote by copying only runtime files to `<skill-name>/`.
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
3. Promote by copying only runtime files to `plugins/<plugin-name>/`.
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

## Marketplace Rules

- `.agents/plugins/marketplace.json` is the release marketplace.
- Release marketplace entries should reference `./plugins/<plugin-name>`, not `./dev/plugins/<plugin-name>`.
- Each plugin entry should keep `policy.installation`, `policy.authentication`, and `category`.
- Dev marketplace files may exist for local testing but are not release truth.

## Promotion Checklist

1. Confirm the dev source has no unrelated dirty changes.
2. Copy only allowlisted runtime files into the release source.
3. Check that release sources contain no `log/`, `__pycache__/`, generated reports, or scratch files.
4. Run the asset-specific validation command.
5. Review the diff for accidental deletes, path changes, or marketplace drift.

## Current Repository Migration

For `codex-project-orchestrator`, keep iterating in `dev/plugins/codex-project-orchestrator`. Its release copy lives at `plugins/codex-project-orchestrator`.

On this machine, the active development install is `codex-project-orchestrator@agents-dev-local`.
The `agents-dev-local` marketplace is still rooted at `/Users/cy/Dev/agents-dev` so it can also serve
other local plugins, but its `codex-project-orchestrator` entry should resolve to:

```text
/Users/cy/Dev/agents-dev/cy-codex-skills/dev/plugins/codex-project-orchestrator
```

After changing the dev plugin, refresh the local install with:

```bash
codex plugin add codex-project-orchestrator@agents-dev-local
```

Then verify the source marketplace mapping with:

```bash
python3 dev/plugins/codex-project-orchestrator/scripts/codex_plugin_preflight.py \
  --plugin-root /Users/cy/Dev/agents-dev/cy-codex-skills/dev/plugins/codex-project-orchestrator \
  --marketplace /Users/cy/Dev/agents-dev/.agents/plugins/marketplace.json \
  --repo /Users/cy/Dev/agents-dev/cy-codex-skills \
  --codex-home /Users/cy/.codex \
  --config /Users/cy/.codex/config.toml \
  --json
```

When promoting it:

1. Copy the allowlisted plugin runtime files from `dev/plugins/codex-project-orchestrator` to `plugins/codex-project-orchestrator`.
2. Keep `.agents/plugins/marketplace.json` pointed at `./plugins/codex-project-orchestrator`.
3. Keep `.agents/plugins/marketplace.dev.json` pointed at `./dev/plugins/codex-project-orchestrator` for local development testing.
4. Keep tests and fixtures in the dev copy.
5. Run unit tests from the dev copy and plugin preflight against both the release and dev marketplace paths.

The existing `plugins/godot-core` already matches the release-side plugin location. If it needs heavier iteration, create `dev/plugins/godot-core` and promote back to `plugins/godot-core` after validation.
