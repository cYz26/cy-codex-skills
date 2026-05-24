# Integrate AI-native planning

<!-- ai-native-plan-lint: allow-human-planning-terms -->

## Why

The codex-project-orchestrator plugin currently contains workflow scaffolding and planning language that can encourage human project-management boundaries such as MVP, phase completion, and later work buckets. That conflicts with the desired plugin role: guiding Codex toward full target-state delivery through executable, verifiable AI-native work slices.

This change makes AI-native planning the plugin default while preserving existing Superpowers, GSD, and OpenSpec responsibilities. GSD still owns roadmap and workflow sequencing, OpenSpec still owns behavior-level artifacts, and Superpowers still owns engineering discipline. The plugin will add the missing execution contract layer so plans are durable, resumable, and difficult to stop after the first partial slice.

## What Changes

- Add an `ai-native-tech-plan` skill for technical plans, implementation plans, architecture plans, and Codex execution plans.
- Add reusable templates and references for Target State, Completion Contract, Capability Slices, Execution Ledger, `/goal` prompts, continue prompts, AGENTS.md rules, and review checklists.
- Add a lint script that detects human-style planning anti-patterns in generated plans unless an explicit allow marker is present.
- Update project scaffold templates so generated workflow files use AI-native planning language by default.
- Update orchestrator routing skills so Superpowers, GSD, and OpenSpec are applied through AI-native completion contracts and execution ledgers.
- Update development and release plugin copies together.

## Scope

- Project mode: brownfield
- Change type: behavior-change
- Applies to `dev/plugins/codex-project-orchestrator` and the release copy under `plugins/codex-project-orchestrator`.
- Applies to generated workflow scaffolds, skill instructions, bundled references, and validation tooling.

## Non-Goals

- Do not remove GSD, OpenSpec, or Superpowers workflow ownership.
- Do not rewrite the plugin architecture or replace existing setup, checkpoint, verification, dependency, or audit scripts.
- Do not add production dependencies.
- Do not change public command names or existing script invocation contracts except to add new optional tooling.

## Risks

- Existing tests assert legacy scaffold names such as `initial-mvp`; they must be updated to the new AI-native baseline without weakening behavior coverage.
- The lint script must allow documents that discuss anti-patterns as policy while still catching those terms in generated execution plans.
- GSD uses phase terminology for workflow governance; updated instructions must distinguish governance checkpoints from technical completion boundaries.
