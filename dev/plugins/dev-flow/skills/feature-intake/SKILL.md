---
name: feature-intake
description: Use when triaging features, bugs, refactors, migrations, tooling, or workflow requests.
---

# Feature Intake

Classify the request and produce a routing decision before planning or code.

## Intake

1. Name the kind: feature, bug, behavior/API/data change, migration,
   integration, refactor, test-only, docs-only, tooling, or workflow repair.
2. State Target State, scope/non-goals, acceptance evidence, risks, and missing
   decisions. For repair, describe the systemic solution first, then justify a
   systemic, minimal, staged, or deferred execution shape.
3. Choose `Full OpenSpec`, configured `Lightweight Ledger`, or explicit
   `Prototype Mode` from `docs/routing.matrix.json`.
4. Use `capability-research` when current or external capability, platform,
   plugin/runtime, hook/API, CLI, cache, or local-versus-platform evidence can
   change the solution.
5. If goals, constraints, tradeoffs, or Open Questions remain, resolve them
   before the artifact is final. Decision grilling inspects local evidence,
   asks one question at a time, recommends an answer, and records it in the
   canonical artifact.

## Capability Routing

Record required stable IDs, not provider skill names. Intake normally needs
`decision-resolution`; architecture work adds `architecture-guidance`; a
non-trivial plan adds `implementation-planning`. Resolve implementations from
`docs/provider_profiles.json`. Provider details are deferred to
`docs/provider-profile-migration.md`.

## Skill Routing Ledger

For research, design, architecture, product shape, or technical planning,
record kind, workflow mode, capability-research, decision resolution,
implementation planning, OpenSpec routing, roadmap routing, and a reason for
every skip. Open Questions make decision resolution required and the artifact
draft until resolved.

Route technical-plan structure to `ai-native-tech-plan`, unclear OpenSpec
behavior to `openspec-explore`, ready behavior intent to `openspec-propose`,
and an approved task to `openspec-apply-change` through `execute-task`.

Before delegated agent, subagent, worker, or parallel execution, require an
Agent Task Contract with Goal, Scope, Constraints, Verification, Evidence, and
Human Gate. Apply the Goal Suitability Gate through `define-goal` when the user
requests a goal or the work is likely to lose its definition of done.

## Output

Return the classification, workflow mode, capability IDs, canonical artifact,
approval boundary, validation surface, and exact next action. Intake is
complete only when unresolved questions are absent or the artifact is marked
draft.
