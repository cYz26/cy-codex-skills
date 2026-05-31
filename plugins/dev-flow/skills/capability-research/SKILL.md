---
name: capability-research
description: Use when researching current, external, platform, plugin, API, hook, or local tool capabilities before planning or implementation.
---

# Capability Research

Use this skill when a request depends on a capability that might be supplied by an external platform, current documentation, a plugin runtime, a CLI, a hook/event system, installed cache contents, or repo-local tooling.

## Capability Evidence Gate

Run this gate before choosing a solution or claiming a capability is unsupported.

1. Confirm authoritative/current capability.
   - Prefer official documentation, primary source release notes, schemas, or the tool's own current help output.
   - Record source, date or version when available, and any direct constraint that affects the design.
   - If the capability can drift and current docs are unavailable, mark the assumption as unverified instead of treating memory as evidence.

2. Run a local implementation scan.
   - Inspect repo files, plugin manifests, hooks, config, installed cache, scripts, tests, lockfiles, and generated artifacts.
   - Use `rg` or structured tooling first.
   - For local Codex plugins, separate source repo state from installed cache state; registration or enablement is not proof that packaged files are refreshed.

3. Produce a solution comparison.
   - Compare authoritative capability, local availability, fallback options, compatibility risks, and the smallest safe implementation path.
   - Explicitly state when local absence is not platform absence.
   - Do not infer "unsupported" solely from not finding local code.

4. Persist the OpenSpec/test contract.
   - For behavior, workflow, integration, API, compatibility, or tooling changes, record the chosen capability contract in OpenSpec before implementation.
   - Include evidence links or command evidence, local scan findings, assumptions, validation commands, and rollback or fallback behavior.
   - Do not implement until the evidence supports the chosen approach or a blocker is recorded.

## Triggers

Use this gate when any of these are true:

- The user asks whether something is supported, recommended, latest, current, official, or possible.
- The design depends on platform behavior, hooks, plugins, CLI commands, SDK APIs, external services, standards, browser behavior, OS behavior, or package manager behavior.
- A previous answer would change if a newer version or installed cache differs from memory.
- Local files do not show a capability that might be provided by the runtime, installed plugin, or external tool.
- The implementation would add a fallback, workaround, custom parser, or manual convention because a native capability was not found locally.

## Evidence Ledger

When the gate applies, record these fields in the active proposal, design, tasks, verification note, or checkpoint:

- `authoritative_current`: source or command used, observed capability, version or date when available.
- `local_scan`: files, cache paths, config, tests, or commands inspected.
- `comparison`: native option, local state, fallback option, recommendation, and tradeoffs.
- `assumptions`: what remains unverified and why it is acceptable or blocking.
- `contract`: OpenSpec scenarios and validation commands that prove the selected behavior.

## Anti-Patterns

- Treating "I did not see it in this repo" as "the platform does not support it".
- Parsing user terminal input when the platform exposes a lifecycle event, schema, or API for the same fact.
- Using transcript or chat history as the only evidence for unstable behavior.
- Putting the full gate procedure into AGENTS; AGENTS should only route to this skill.
- Implementing a workaround before checking official/current and local installed capability.

## Output

End research with a concise recommendation:

- Confirmed capability.
- Local state.
- Recommended approach.
- OpenSpec/test contract.
- Remaining blocker, if any.
