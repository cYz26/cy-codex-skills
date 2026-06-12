---
name: skill-candidate-harvester
description: Aggregate repeated durable workflows across Codex repositories, maintain candidate records in global durable-knowledge memory, and promote mature candidates into skill drafts when the evidence threshold is met.
---

# Skill Candidate Harvester

Use this skill when repeated workflows need to move beyond task-local notes and become structured skill candidates or drafts.

## Preconditions
- The target environment should have:
  - tracked repos listed in `$CODEX_HOME/memories/durable-knowledge/repos.yaml`
  - candidate storage under `$CODEX_HOME/memories/durable-knowledge/skill-candidates/`
  - draft storage under `$CODEX_HOME/memories/durable-knowledge/skill-drafts/`
- If those paths are missing, seed them first from this skill's `assets/` templates.

## Read first
1. `$CODEX_HOME/memories/durable-knowledge/repos.yaml`
2. the candidate schema in `assets/skill-candidate.template.yaml`
3. each tracked repo's:
   - `AGENTS.md`
   - `docs/work/.current`
   - recent task `meta.yaml` files
   - recent task `learning-log.md` files
   - recent task `status.md` files, especially `Potential Skills`
   - `knowledge/changelog.md`
   - relevant pitfalls, checklist, or verification docs when evidence needs confirmation

## Workflow
1. Load the tracked repo list.
   - use `assets/repos.template.yaml` only as a seed, not as the live registry
2. Collect candidate evidence.
   - triaged or promoted entries from `learning-log.md`
   - explicit `skill_candidates` from task metadata
   - `Potential Skills` sections in task status files
   - repeated durable findings in changelogs, pitfalls, or checklists
3. Merge by workflow identity.
   - prefer a stable `pattern_key` first when present
   - otherwise merge by stable skill-style name plus normalized summary similarity
   - merge evidence instead of creating near-duplicates
4. Update or create candidate records under `$CODEX_HOME/memories/durable-knowledge/skill-candidates/`.
   - use `assets/skill-candidate.template.yaml`
   - keep `pattern_keys`, `trigger_types`, `source_entries`, `recurrence_count`, `source_repos`, `source_tasks`, validation, and failure modes current
5. Decide whether a draft should be created.
   - require at least two independent tasks or two repositories of evidence
   - require at least one validation path
   - require at least one pitfalls or edge-case record
   - require stable steps that no longer depend on large amounts of one-off context
6. When the threshold is met:
   - create or refresh a draft under `$CODEX_HOME/memories/durable-knowledge/skill-drafts/<skill-name>/`
   - link back to source repos, source tasks, and verification state
   - hand off to `skill-creator` for the final installed skill
7. If the workflow is already an installed skill:
   - mark the candidate `installed`
   - update the global skills changelog instead of generating a duplicate draft

## Hard rules
1. Do not create multiple candidates for the same workflow just because wording differs.
2. Do not promote a candidate to a draft without evidence, validation, and at least one failure-mode record.
3. Do not treat manual enthusiasm alone as enough for draft promotion.
4. Do not overwrite source-repo nuance; keep blocked or partial validation states intact.
5. Do not install a skill directly from this skill; draft first, then use `skill-creator`.

## Bundled assets
- `assets/skill-candidate.template.yaml`
- `assets/repos.template.yaml`
- `assets/global-memory/`

## Deliverables
1. Tracked repos are aggregated into candidate evidence.
2. Candidate files stay normalized and deduplicated.
3. Mature candidates become drafts with clear provenance.
4. Installed skills remain linked back to their source evidence.
