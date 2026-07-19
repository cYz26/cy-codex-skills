## Why

DevFlow currently models Git push and GitHub platform actions through the combined `git.push_pr` side effect. In practice, `gh auth status` can fail while the repository's configured SSH remote remains fully usable, so treating those failures as one capability causes unnecessary authentication loops and can block an otherwise authorized `git push`.

## What Changes

- Classify native Git transport and GitHub control-plane writes as independent capabilities and authorization effects.
- Add a read-only native Git transport preflight that inspects the configured remote and probes it with `git ls-remote` without invoking `gh` or performing a push.
- Route authorized push work through the configured Git remote first; a failed `gh` authentication check must not imply that Git transport is unavailable.
- Bound GitHub control-plane recovery to one diagnosis and one remediation attempt, then stop that platform path without retry loops or blocking independent Git work.
- Preserve the existing `git.push_pr` policy entry as a compatibility alias while new routing uses the separated effects.
- Add focused contract tests and generated-project guidance for the new behavior.

## Capabilities

### New Capabilities

- `git-transport-routing`: Independent routing, preflight, authorization, and bounded fallback behavior for native Git transport versus GitHub control-plane actions.

### Modified Capabilities

None.

## Impact

Affected surfaces include the DevFlow side-effect policy, Git workflow helpers and CLI entrypoints, project-orchestrator and verification guidance, generated `AGENTS.md` rules, development tests, and the resolved release package. No production dependency, Git credential configuration, automatic push, or continuation-outcome expansion is introduced.
