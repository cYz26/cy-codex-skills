---
name: project-orchestrator
description: Use when routing Codex project setup, planning, execution, verification, or repair.
---

# Project Orchestrator

Router for Codex-first project work.

## Procedure

Read `AGENTS.md`, `.planning/STATE.md`, and `openspec/config.yaml`. Run dependency check; activate missing project-local dependencies.

## Routing

- No workflow files: use `project-setup`.
- New feature, bug, behavior/API change, migration, or integration: use `feature-intake`.
- Active change without proposal/design/specs/tasks: use `change-plan`.
- Approved task with plan and tests ready: use `execute-task`.
- Implementation complete or user asks to finish: use `verify-and-archive`.
- State files conflict or artifacts are missing: use `workflow-doctor`.
- Major workflow boundary or context cleanup request: use `checkpoint-compact`.

## Dependency Skills

Routes: `superpowers:brainstorming`, `superpowers:writing-plans`, `superpowers:test-driven-development`, `superpowers:verification-before-completion`; `openspec-explore`, `openspec-propose`, `openspec-apply-change`, `openspec-archive-change`; `gsd-discuss-phase`, `gsd-plan-phase`, `gsd-execute-phase`, `gsd-verify-work`.

## Safety

Do not edit production code during setup/intake/planning. Do not archive without verification evidence. Ask before dependencies, migrations, API breaks, or broad rewrites.
