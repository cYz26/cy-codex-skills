## Why

DevFlow currently carries a multi-provider abstraction whose Superpowers and GSD branches add substantial routing, activation, validation, fixture, and release surface even though the repository's active workflow does not use them. Replace that abstraction with one explicit DevFlow/OpenSpec workflow and a small, pinned MattPocock engineering capability pack so the common path is shorter, easier to diagnose, and cheaper to maintain.

## What Changes

- Make DevFlow and OpenSpec the sole active control plane for intake, planning, canonical artifacts, execution ledgers, evidence, verification, and archive readiness.
- Make the approved MattPocock primitives the sole active external methodology capabilities: `grilling`, `tdd`, `diagnosing-bugs`, `code-review`, `codebase-design`, and `domain-modeling`.
- Replace methodology-profile and roadmap-provider selection with one static capability map and on-demand project-local activation of only the Matt skills required by the current task.
- Define a bounded subagent strategy: use subagents only for independently verifiable work, require a validated task contract and disjoint write ownership, and keep shared-artifact integration with the primary agent.
- **BREAKING** Remove Superpowers and GSD from active configuration, routing, activation, diagnosis, hooks, readiness, archive policy, benchmarks, fixtures, documentation, and release assets. Existing `strict-superpowers`, `roadmap_provider: gsd`, provider selectors, bindings, and provider locks no longer select runtime behavior.
- Preserve an isolated, read-only legacy-config inspector that recognizes obsolete Superpowers/GSD/provider fields, reports a deterministic redacted target configuration and manual cleanup guidance, and never echoes configuration values, installs, imports, executes, or silently falls back to a legacy provider.
- Remove obsolete active-provider code and tests while preserving historical evidence in Git/OpenSpec history and keeping source/release packages byte-aligned.

## Capabilities

### New Capabilities

- `devflow-matt-native-methodology`: Defines the single active DevFlow/OpenSpec control plane, static Matt capability routing, project-local skill readiness, and bounded subagent execution contract.
- `devflow-legacy-provider-migration`: Defines isolated read-only recognition and reporting for obsolete Superpowers, GSD, and multi-provider configuration without runtime dependency or automatic mutation.

### Modified Capabilities

- `devflow-plugin-quality`: Extends release-quality requirements to exclude active Superpowers/GSD surfaces, prove source/release parity, validate the simplified runtime, and assess the release target with Plugin Eval.

## Impact

- Affects DevFlow workflow configuration, dependency checks, project activation, scaffolding, hooks, verification/archive policy, migration diagnostics, provenance, documentation, tests, fixtures, and generated release assets under `dev/plugins/dev-flow` and `plugins/dev-flow`.
- Deletes the active methodology/roadmap provider registry, Superpowers artifact gates, GSD lifecycle bindings, provider comparison benchmarks, and their active fixtures.
- Retains the existing OpenSpec CLI and six project-local OpenSpec skills as canonical behavior-change management; no production dependency is added.
- Existing projects with legacy provider fields receive read-only migration findings and explicit target guidance; applying project changes remains separately authorization-gated.
