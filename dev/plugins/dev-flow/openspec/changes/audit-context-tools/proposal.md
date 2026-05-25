# Audit context tools

## Why

Codex sessions can accumulate globally enabled plugins and skills that are unrelated to the current project. Those global tools occupy long-lived context, make sessions noisier, and make it harder to keep project-specific workflows isolated. The orchestrator already checks that its core dependencies stay project-local; it should also provide a broader audit that explains which tools are active globally, which local or cached tools could be moved into the current project, and which additional tools are worth considering for the repo.

## What Changes

- Add a read-only context tool audit report for global plugins, global skills, project-local skills, installed plugin-cache skills, and optional marketplace/source catalogs.
- Add cleanup and installation recommendations with stable action ids.
- Add an apply script that can execute selected actions only after explicit user authorization.
- Prefer disabling global configuration and installing project-local skills over deleting files or broad global activation.

## Scope

- Project mode: brownfield
- Change type: new-feature

## Non-Goals

- Do not delete plugin cache entries or global skill files in the first version.
- Do not perform open-ended internet search without an explicit source URL or catalog path.
- Do not auto-install marketplace plugins without a supported local install source.
- Do not change existing dependency checks from required to advisory.

## Risks

- Editing `~/.codex/config.toml` incorrectly could break user configuration, so all apply operations must create backups and use targeted updates.
- Relevance scoring can be imperfect, so cleanup actions must remain recommendations until selected by the user.
- Remote catalogs can be unavailable or malformed, so source scanning must degrade into report findings instead of failing the whole audit.
