---
name: project-orchestrator
description: Use when routing Codex setup, planning, execution, verify, or repair.
---

# Project Orchestrator

Router for Codex-first project work.

## Procedure

Read `AGENTS.md`, `.planning/STATE.md`, and `openspec/config.yaml`. Run dependency check; activate missing project-local dependencies.

## Routing

- No workflow files: use `project-setup`.
- Technical plan, implementation plan, architecture plan, Codex execution plan, workflow plan, or anti-partial-delivery request: use `ai-native-tech-plan`.
- New feature, bug, behavior/API change, migration, or integration: use `feature-intake`.
- Active change without proposal/design/specs/tasks: use `change-plan`.
- Approved task with plan and tests ready: use `execute-task`.
- Implementation complete or user asks to finish: use `verify-and-archive`.
- State files conflict or artifacts are missing: use `workflow-doctor`.
- Major workflow boundary or context cleanup request: use `checkpoint-compact`.
- Global plugin/skill context audit, cleanup recommendation, or authorized cleanup/install request: use `context-tool-audit`.

## Dependency Skills

Routes: `ai-native-tech-plan`; `superpowers:brainstorming`, `superpowers:writing-plans`, `superpowers:test-driven-development`, `superpowers:verification-before-completion`; `openspec-explore`, `openspec-propose`, `openspec-apply-change`, `openspec-archive-change`; `gsd-discuss-phase`, `gsd-plan-phase`, `gsd-execute-phase`, `gsd-verify-work`.

## Superpowers Artifact Mapping

Superpowers provides process discipline; OpenSpec, GSD, and DevFlow planning files are the canonical artifacts. Map `docs/superpowers/specs/...` into `openspec/changes/<change-id>/proposal.md`, `design.md`, or `specs/` for behavior work. Map `docs/superpowers/plans/...` into `openspec/changes/<change-id>/tasks.md`, `.planning/phases/.../PLAN.md`, or a DevFlow-approved Execution Ledger before implementation.

## Safety

Do not edit production code during setup/intake/planning. Do not archive without verification evidence. Ask before dependencies, migrations, API breaks, or broad rewrites. Treat GSD phases as workflow governance; technical completion is governed by Target State, Completion Contract, Capability Slices, Execution Ledger, and Validation Commands.
