# Current System Baseline

## Why

Initialize a safe baseline for Codex-managed project work.

## What Changes

- Record the current Context Fixer behavior as a concrete baseline.
- Preserve local-first CLI analysis for Codex sessions, optional request traces,
  project instruction files, Codex configuration, project-local skills, and
  workflow files.
- Preserve sanitized text, JSON, and self-contained HTML reporting.
- Record workflow state, planning files, OpenSpec artifacts, checkpoint policy,
  and verification gates.

## Capabilities

- `current-system`: Context Fixer current behavior and workflow baseline.

## Scope

- Project mode: brownfield
- Change type: setup

## Non-Goals

- Do not expand beyond the requested change without updating this proposal.

## Risks

- Compatibility and verification risks must be resolved before archive.
