# Add capability evidence gate to research skills

## Why

The compact-hook discussion exposed a workflow failure mode: Codex can treat "not found locally" as "not supported by the platform" when the right answer requires current official capability evidence plus local implementation evidence. That problem is broader than Codex CLI hook work, so the guardrail should live in DevFlow research and planning skills, with only a light trigger in generated AGENTS guidance.

## What Changes

- Add a dedicated DevFlow `capability-research` skill that defines a reusable Capability Evidence Gate.
- Route uncertain/current platform, tool, plugin, API, and workflow capability questions through that skill from DevFlow intake and planning skills.
- Add OpenSpec template sections so capability evidence is recorded before implementation for relevant changes.
- Keep generated `AGENTS.md` guidance brief: it should point agents to the skill instead of embedding the full procedure.

## Target State

- DevFlow has a first-class research skill for evidence-backed capability decisions.
- When a request depends on current, external, platform, plugin, hook, API, or local tool capability, DevFlow routes agents through a four-step gate: authoritative/current capability confirmation, local implementation scan, solution comparison, and OpenSpec/test contract before implementation.
- Generated planning artifacts include a place to record capability evidence and assumptions.
- Release packaging and project-local dependency activation include the new skill.

## Scope

- Project mode: brownfield
- Change type: behavior-change

## Non-Goals

- Do not implement runtime web browsing or automatic documentation fetching.
- Do not add production dependencies.
- Do not replace AGENTS, OpenSpec, GSD, or Superpowers ownership boundaries.
- Do not force this gate for trivial code-only tasks with no unstable/current capability assumptions.

## Completion Contract

- [ ] `capability-research` exists in development and release plugin roots with valid Codex skill frontmatter.
- [ ] DevFlow routing skills reference the gate where capability assumptions affect requirements, design, or implementation.
- [ ] OpenSpec templates include a Capability Evidence section and tasks include a first slice for the evidence gate.
- [ ] Tests cover the new skill packaging, routing text, templates, and dependency activation.
- [ ] Dev and release verification pass and evidence is recorded.

## Risks

- Over-routing simple work through research can slow execution; the skill must define concrete triggers.
- Duplicating detailed process in AGENTS would create drift; AGENTS must remain a lightweight pointer.
